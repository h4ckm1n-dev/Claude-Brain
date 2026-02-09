"""Memory lifecycle state machine (Phase 4.1).

Implements proper memory state transitions:
- EPISODIC → STAGING → SEMANTIC → PROCEDURAL
- ANY → ARCHIVED → PURGED

State transitions based on:
- Quality scores (Phase 3.2)
- Age thresholds
- Access patterns
- Manual interventions
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import MemoryState

logger = logging.getLogger(__name__)


def _load_retention_default() -> int:
    """Load audit retention days from settings.json, defaulting to 90."""
    settings_path = os.path.join(os.path.expanduser("~"), ".claude", "memory", "data", "settings.json")
    try:
        with open(settings_path, "r") as f:
            data = json.load(f)
        return max(30, min(365, int(data.get("auditRetentionDays", 90))))
    except Exception:
        return 90


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class StateTransition:
    """Represents a state transition with validation."""

    # Valid state transitions
    VALID_TRANSITIONS = {
        MemoryState.EPISODIC: [MemoryState.STAGING, MemoryState.SEMANTIC, MemoryState.ARCHIVED],
        MemoryState.STAGING: [MemoryState.SEMANTIC, MemoryState.EPISODIC, MemoryState.ARCHIVED],
        MemoryState.SEMANTIC: [MemoryState.PROCEDURAL, MemoryState.ARCHIVED],
        MemoryState.PROCEDURAL: [MemoryState.ARCHIVED],  # Procedural can be archived but carefully
        MemoryState.ARCHIVED: [MemoryState.PURGED, MemoryState.EPISODIC],  # Can restore to EPISODIC
        MemoryState.PURGED: []  # Terminal state
    }

    @staticmethod
    def is_valid_transition(from_state: MemoryState, to_state: MemoryState) -> bool:
        """Check if a state transition is valid."""
        valid_next_states = StateTransition.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_next_states

    @staticmethod
    def get_valid_next_states(current_state: MemoryState) -> List[MemoryState]:
        """Get list of valid next states from current state."""
        return StateTransition.VALID_TRANSITIONS.get(current_state, [])


class MemoryLifecycleManager:
    """Manages memory state transitions and lifecycle."""

    # Configuration constants
    STAGING_AGE_HOURS = 48  # Move to STAGING after 48 hours if low access
    STAGING_MIN_ACCESS = 3  # Minimum accesses to skip STAGING

    SEMANTIC_MIN_QUALITY = 0.75  # Min quality for SEMANTIC promotion
    SEMANTIC_MIN_AGE_DAYS = 7  # Min age for SEMANTIC promotion

    PROCEDURAL_MIN_QUALITY = 0.9  # Min quality for PROCEDURAL promotion
    PROCEDURAL_MIN_AGE_DAYS = 30  # Min age for PROCEDURAL promotion

    ARCHIVED_LOW_QUALITY = 0.2  # Archive if quality < 0.2
    ARCHIVED_LOW_QUALITY_AGE_DAYS = 30  # ... and older than 30 days

    PURGE_RETENTION_DAYS = _load_retention_default()  # Loaded from settings.json

    @staticmethod
    def evaluate_episodic_transition(
        memory_id: str,
        memory: Dict,
        current_time: datetime
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if EPISODIC memory should transition.

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        created_at = memory.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        age_hours = (current_time - created_at).total_seconds() / 3600
        access_count = memory.get("access_count", 0)
        quality_score = memory.get("quality_score", 0.5)

        # Check for promotion to SEMANTIC (high quality, sufficient age)
        age_days = age_hours / 24
        if age_days >= MemoryLifecycleManager.SEMANTIC_MIN_AGE_DAYS:
            if quality_score >= MemoryLifecycleManager.SEMANTIC_MIN_QUALITY:
                return (
                    MemoryState.SEMANTIC,
                    f"High quality ({quality_score:.2f}) sustained for {age_days:.0f} days"
                )

        # Check for archival (low quality, old)
        if age_days >= MemoryLifecycleManager.ARCHIVED_LOW_QUALITY_AGE_DAYS:
            if quality_score < MemoryLifecycleManager.ARCHIVED_LOW_QUALITY:
                return (
                    MemoryState.ARCHIVED,
                    f"Low quality ({quality_score:.2f}) after {age_days:.0f} days"
                )

        # Move to STAGING if old enough and not frequently accessed
        if age_hours >= MemoryLifecycleManager.STAGING_AGE_HOURS:
            if access_count < MemoryLifecycleManager.STAGING_MIN_ACCESS:
                return (
                    MemoryState.STAGING,
                    f"Low access ({access_count}) after {age_hours:.0f} hours"
                )

        return None

    @staticmethod
    def evaluate_staging_transition(
        memory_id: str,
        memory: Dict,
        current_time: datetime
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if STAGING memory should transition.

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        state_changed_at = memory.get("state_changed_at")
        if isinstance(state_changed_at, str):
            state_changed_at = datetime.fromisoformat(state_changed_at.replace('Z', '+00:00'))

        time_in_staging_days = (current_time - state_changed_at).days
        access_count = memory.get("access_count", 0)
        quality_score = memory.get("quality_score", 0.5)

        # If accessed after entering STAGING, move back to EPISODIC
        # (Check if access_count increased since staging)
        last_accessed = memory.get("last_accessed")
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))

        if last_accessed > state_changed_at:
            return (
                MemoryState.EPISODIC,
                f"Accessed {access_count} times after staging"
            )

        # Check for consolidation to SEMANTIC
        if time_in_staging_days >= MemoryLifecycleManager.SEMANTIC_MIN_AGE_DAYS:
            # If quality improved, promote to SEMANTIC
            if quality_score >= 0.5:  # Lower threshold for staging
                return (
                    MemoryState.SEMANTIC,
                    f"Quality improved to {quality_score:.2f} during staging"
                )

        # Check for archival (no improvement after long staging)
        if time_in_staging_days >= MemoryLifecycleManager.ARCHIVED_LOW_QUALITY_AGE_DAYS:
            if quality_score < 0.3:
                return (
                    MemoryState.ARCHIVED,
                    f"Low quality ({quality_score:.2f}) after {time_in_staging_days} days in staging"
                )

        return None

    @staticmethod
    def evaluate_semantic_transition(
        memory_id: str,
        memory: Dict,
        current_time: datetime
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if SEMANTIC memory should transition.

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        state_changed_at = memory.get("state_changed_at")
        if isinstance(state_changed_at, str):
            state_changed_at = datetime.fromisoformat(state_changed_at.replace('Z', '+00:00'))

        time_in_semantic_days = (current_time - state_changed_at).days
        quality_score = memory.get("quality_score", 0.5)
        current_version = memory.get("current_version", 1)

        # Check for promotion to PROCEDURAL (excellent quality, stable, old)
        if time_in_semantic_days >= MemoryLifecycleManager.PROCEDURAL_MIN_AGE_DAYS:
            if quality_score >= MemoryLifecycleManager.PROCEDURAL_MIN_QUALITY:
                # Also check stability (few edits)
                if current_version <= 3:  # Stable (≤2 edits)
                    return (
                        MemoryState.PROCEDURAL,
                        f"Excellent quality ({quality_score:.2f}), stable (v{current_version}), {time_in_semantic_days} days old"
                    )

        # Check for archival (quality degraded)
        if quality_score < MemoryLifecycleManager.ARCHIVED_LOW_QUALITY:
            if time_in_semantic_days >= 60:  # Give semantic memories more time
                return (
                    MemoryState.ARCHIVED,
                    f"Quality degraded to {quality_score:.2f} after {time_in_semantic_days} days"
                )

        return None

    @staticmethod
    def evaluate_procedural_transition(
        memory_id: str,
        memory: Dict,
        current_time: datetime
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if PROCEDURAL memory should transition.

        Procedural memories are permanent best practices and should rarely be archived.

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        quality_score = memory.get("quality_score", 0.5)
        state_changed_at = memory.get("state_changed_at")
        if isinstance(state_changed_at, str):
            state_changed_at = datetime.fromisoformat(state_changed_at.replace('Z', '+00:00'))

        time_in_procedural_days = (current_time - state_changed_at).days

        # Only archive procedural if quality is extremely low and old
        if quality_score < 0.1:  # Very low threshold
            if time_in_procedural_days >= 180:  # Give procedural memories lots of time
                return (
                    MemoryState.ARCHIVED,
                    f"Extremely low quality ({quality_score:.2f}) after {time_in_procedural_days} days"
                )

        return None

    @staticmethod
    def evaluate_archived_transition(
        memory_id: str,
        memory: Dict,
        current_time: datetime
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if ARCHIVED memory should be purged.

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        state_changed_at = memory.get("state_changed_at")
        if isinstance(state_changed_at, str):
            state_changed_at = datetime.fromisoformat(state_changed_at.replace('Z', '+00:00'))

        time_in_archived_days = (current_time - state_changed_at).days

        # Check for purge (retention period expired)
        if time_in_archived_days >= MemoryLifecycleManager.PURGE_RETENTION_DAYS:
            return (
                MemoryState.PURGED,
                f"Retention period ({MemoryLifecycleManager.PURGE_RETENTION_DAYS} days) expired"
            )

        return None

    @staticmethod
    def evaluate_transition(
        memory_id: str,
        memory: Dict,
        current_time: Optional[datetime] = None
    ) -> Optional[Tuple[MemoryState, str]]:
        """
        Evaluate if a memory should transition to a new state.

        Args:
            memory_id: Memory ID
            memory: Memory payload
            current_time: Current time (defaults to now)

        Returns:
            (next_state, reason) if transition recommended, None otherwise
        """
        if current_time is None:
            current_time = utc_now()

        current_state_str = memory.get("state", "episodic")
        try:
            current_state = MemoryState(current_state_str)
        except ValueError:
            logger.warning(f"Invalid state '{current_state_str}' for memory {memory_id}")
            return None

        # Evaluate based on current state
        if current_state == MemoryState.EPISODIC:
            return MemoryLifecycleManager.evaluate_episodic_transition(
                memory_id, memory, current_time
            )
        elif current_state == MemoryState.STAGING:
            return MemoryLifecycleManager.evaluate_staging_transition(
                memory_id, memory, current_time
            )
        elif current_state == MemoryState.SEMANTIC:
            return MemoryLifecycleManager.evaluate_semantic_transition(
                memory_id, memory, current_time
            )
        elif current_state == MemoryState.PROCEDURAL:
            return MemoryLifecycleManager.evaluate_procedural_transition(
                memory_id, memory, current_time
            )
        elif current_state == MemoryState.ARCHIVED:
            return MemoryLifecycleManager.evaluate_archived_transition(
                memory_id, memory, current_time
            )
        elif current_state == MemoryState.PURGED:
            # Purged is terminal state
            return None

        return None

    @staticmethod
    def apply_state_transition(
        client: QdrantClient,
        collection_name: str,
        memory_id: str,
        new_state: MemoryState,
        reason: str
    ) -> bool:
        """
        Apply a state transition to a memory.

        Args:
            client: Qdrant client
            collection_name: Collection name
            memory_id: Memory ID
            new_state: New state
            reason: Reason for transition

        Returns:
            True if transition applied successfully
        """
        try:
            now = utc_now()

            # Get current memory to validate transition
            response = client.retrieve(
                collection_name=collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False
            )

            if not response:
                logger.error(f"Memory {memory_id} not found")
                return False

            payload = response[0].payload
            current_state_str = payload.get("state", "episodic")

            try:
                current_state = MemoryState(current_state_str)
            except ValueError:
                logger.warning(f"Invalid current state '{current_state_str}' for memory {memory_id}")
                return False

            # Validate transition
            if not StateTransition.is_valid_transition(current_state, new_state):
                logger.error(
                    f"Invalid transition for memory {memory_id}: "
                    f"{current_state.value} → {new_state.value}"
                )
                return False

            # Get existing state history
            state_history = payload.get("state_history", [])

            # Add transition to history
            state_history.append({
                "from_state": current_state.value,
                "to_state": new_state.value,
                "timestamp": now.isoformat(),
                "reason": reason
            })

            # Update state fields
            updates = {
                "state": new_state.value,
                "state_changed_at": now.isoformat(),
                "state_history": state_history
            }

            # Special handling for ARCHIVED and PURGED
            if new_state == MemoryState.ARCHIVED:
                updates["archived"] = True
                updates["archived_at"] = now.isoformat()
            elif new_state == MemoryState.PURGED:
                # For purged, we might want to actually delete from Qdrant
                # But for now, just mark it
                updates["archived"] = True

            # Apply update with quality recalc (applies tier bonus immediately)
            from .collections import safe_set_payload
            safe_set_payload(memory_id, updates, collection_name=collection_name)

            logger.info(
                f"State transition applied: {memory_id} "
                f"{current_state.value} → {new_state.value} ({reason})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to apply state transition for {memory_id}: {e}")
            return False


def update_memory_states(
    client: QdrantClient,
    collection_name: str,
    batch_size: int = 100,
    max_updates: Optional[int] = None
) -> Dict:
    """
    Batch update memory states based on lifecycle rules.

    Args:
        client: Qdrant client
        collection_name: Collection name
        batch_size: Batch size for processing
        max_updates: Maximum number of updates (None = unlimited)

    Returns:
        Statistics about state transitions
    """
    try:
        stats = {
            "total_processed": 0,
            "transitions": 0,
            "by_state": {},
            "by_transition": {},
            "failed": 0
        }

        current_time = utc_now()

        # Process memories in batches
        offset = None
        while True:
            # Scroll through memories
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must_not=[
                        models.FieldCondition(
                            key="state",
                            match=models.MatchValue(value=MemoryState.PURGED.value)
                        )
                    ]
                ),
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points, next_offset = response

            if not points:
                break

            # Evaluate each memory
            for point in points:
                memory_id = point.id
                payload = point.payload

                stats["total_processed"] += 1

                # Evaluate transition
                transition = MemoryLifecycleManager.evaluate_transition(
                    memory_id,
                    payload,
                    current_time
                )

                if transition:
                    new_state, reason = transition
                    current_state = MemoryState(payload.get("state", "episodic"))

                    # Apply transition
                    success = MemoryLifecycleManager.apply_state_transition(
                        client,
                        collection_name,
                        memory_id,
                        new_state,
                        reason
                    )

                    if success:
                        stats["transitions"] += 1

                        # Track by state
                        from_state = current_state.value
                        to_state = new_state.value
                        stats["by_state"][to_state] = stats["by_state"].get(to_state, 0) + 1

                        # Track by transition
                        transition_key = f"{from_state}→{to_state}"
                        stats["by_transition"][transition_key] = stats["by_transition"].get(transition_key, 0) + 1
                    else:
                        stats["failed"] += 1

                # Check if we've hit max_updates
                if max_updates and stats["transitions"] >= max_updates:
                    break

            # Check if we've hit max_updates
            if max_updates and stats["transitions"] >= max_updates:
                break

            # Continue with next batch
            offset = next_offset
            if offset is None:
                break

        return stats

    except Exception as e:
        logger.error(f"Failed to update memory states: {e}")
        return {"error": str(e)}


def get_state_distribution(
    client: QdrantClient,
    collection_name: str
) -> Dict:
    """
    Get distribution of memories across states.

    Returns:
        Distribution statistics
    """
    try:
        distribution = {}

        for state in MemoryState:
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="state",
                            match=models.MatchValue(value=state.value)
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False
            )

            # Count total (Qdrant doesn't have count API directly)
            # We'll do a full scroll just to count
            count = 0
            offset = None
            while True:
                resp = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="state",
                                match=models.MatchValue(value=state.value)
                            )
                        ]
                    ),
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )

                points, next_offset = resp
                count += len(points)

                offset = next_offset
                if offset is None:
                    break

            distribution[state.value] = count

        return {
            "distribution": distribution,
            "total": sum(distribution.values())
        }

    except Exception as e:
        logger.error(f"Failed to get state distribution: {e}")
        return {"error": str(e)}


def manual_state_transition(
    client: QdrantClient,
    collection_name: str,
    memory_id: str,
    new_state: MemoryState,
    reason: str = "Manual transition"
) -> Dict:
    """
    Manually transition a memory to a new state.

    Args:
        client: Qdrant client
        collection_name: Collection name
        memory_id: Memory ID
        new_state: Desired new state
        reason: Reason for manual transition

    Returns:
        Result of transition
    """
    try:
        success = MemoryLifecycleManager.apply_state_transition(
            client,
            collection_name,
            memory_id,
            new_state,
            reason
        )

        if success:
            return {
                "success": True,
                "memory_id": memory_id,
                "new_state": new_state.value,
                "reason": reason
            }
        else:
            return {
                "success": False,
                "memory_id": memory_id,
                "error": "Transition failed (see logs)"
            }

    except Exception as e:
        logger.error(f"Manual state transition failed: {e}")
        return {
            "success": False,
            "memory_id": memory_id,
            "error": str(e)
        }
