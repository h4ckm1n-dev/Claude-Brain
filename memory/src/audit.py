"""Change audit trail system (Phase 4.2).

Tracks all CRUD operations on memories with:
- Full change history (old/new values)
- User/system attribution
- Undo/restore capability
- Audit log querying
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from qdrant_client import QdrantClient
from qdrant_client.http import models
import json

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class AuditAction(str, Enum):
    """Types of audit actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    RESTORE = "restore"
    STATE_TRANSITION = "state_transition"
    TIER_PROMOTION = "tier_promotion"
    QUALITY_UPDATE = "quality_update"


class AuditEntry:
    """Represents a single audit log entry."""

    def __init__(
        self,
        memory_id: str,
        action: AuditAction,
        actor: str = "system",
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Initialize audit entry.

        Args:
            memory_id: ID of memory being changed
            action: Type of action
            actor: Who performed the action ("system" or user ID)
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            reason: Reason for change
            metadata: Additional context
        """
        self.memory_id = memory_id
        self.action = action
        self.actor = actor
        self.timestamp = utc_now()
        self.old_values = old_values or {}
        self.new_values = new_values or {}
        self.reason = reason
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "memory_id": self.memory_id,
            "action": self.action.value,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "old_values": self.old_values,
            "new_values": self.new_values,
            "reason": self.reason,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data: Dict) -> 'AuditEntry':
        """Create from dictionary."""
        entry = AuditEntry(
            memory_id=data["memory_id"],
            action=AuditAction(data["action"]),
            actor=data.get("actor", "system"),
            old_values=data.get("old_values"),
            new_values=data.get("new_values"),
            reason=data.get("reason"),
            metadata=data.get("metadata")
        )
        # Restore timestamp
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            entry.timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return entry


class AuditLogger:
    """Manages audit trail logging and querying."""

    # We'll use a separate Qdrant collection for audit logs
    AUDIT_COLLECTION = "memory_audit_trail"

    @staticmethod
    def ensure_audit_collection(client: QdrantClient):
        """Ensure audit trail collection exists."""
        try:
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if AuditLogger.AUDIT_COLLECTION not in collection_names:
                # Create collection for audit logs
                # We don't need vectors for audit logs, just use a small dimension
                client.create_collection(
                    collection_name=AuditLogger.AUDIT_COLLECTION,
                    vectors_config=models.VectorParams(
                        size=1,  # Minimal vector (we won't use it)
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created audit trail collection: {AuditLogger.AUDIT_COLLECTION}")

        except Exception as e:
            logger.error(f"Failed to ensure audit collection: {e}")

    @staticmethod
    def log_action(
        client: QdrantClient,
        memory_id: str,
        action: AuditAction,
        actor: str = "system",
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Log an audit action.

        Args:
            client: Qdrant client
            memory_id: ID of memory being changed
            action: Type of action
            actor: Who performed the action
            old_values: Previous values
            new_values: New values
            reason: Reason for change
            metadata: Additional context

        Returns:
            Audit entry ID if successful
        """
        try:
            # Ensure collection exists
            AuditLogger.ensure_audit_collection(client)

            # Create audit entry
            entry = AuditEntry(
                memory_id=memory_id,
                action=action,
                actor=actor,
                old_values=old_values,
                new_values=new_values,
                reason=reason,
                metadata=metadata
            )

            # Generate audit entry ID
            from uuid6 import uuid7
            audit_id = str(uuid7())

            # Store in Qdrant
            client.upsert(
                collection_name=AuditLogger.AUDIT_COLLECTION,
                points=[
                    models.PointStruct(
                        id=audit_id,
                        vector=[0.0],  # Dummy vector (not used)
                        payload=entry.to_dict()
                    )
                ]
            )

            logger.debug(
                f"Audit log created: {action.value} on {memory_id} by {actor}"
            )

            return audit_id

        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            return None

    @staticmethod
    def get_audit_trail(
        client: QdrantClient,
        memory_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEntry]:
        """
        Get audit trail entries.

        Args:
            client: Qdrant client
            memory_id: Filter by memory ID
            action: Filter by action type
            actor: Filter by actor
            limit: Maximum entries to return
            offset: Offset for pagination

        Returns:
            List of audit entries
        """
        try:
            # Ensure collection exists
            AuditLogger.ensure_audit_collection(client)

            # Build filter
            filter_conditions = []

            if memory_id:
                filter_conditions.append(
                    models.FieldCondition(
                        key="memory_id",
                        match=models.MatchValue(value=memory_id)
                    )
                )

            if action:
                filter_conditions.append(
                    models.FieldCondition(
                        key="action",
                        match=models.MatchValue(value=action.value)
                    )
                )

            if actor:
                filter_conditions.append(
                    models.FieldCondition(
                        key="actor",
                        match=models.MatchValue(value=actor)
                    )
                )

            # Query audit logs
            filter_obj = models.Filter(must=filter_conditions) if filter_conditions else None

            response = client.scroll(
                collection_name=AuditLogger.AUDIT_COLLECTION,
                scroll_filter=filter_obj,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points, _ = response

            # Convert to AuditEntry objects
            entries = []
            for point in points:
                try:
                    entry = AuditEntry.from_dict(point.payload)
                    entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to parse audit entry: {e}")
                    continue

            # Sort by timestamp (most recent first)
            entries.sort(key=lambda e: e.timestamp, reverse=True)

            return entries

        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []

    @staticmethod
    def get_audit_statistics(
        client: QdrantClient,
        memory_id: Optional[str] = None
    ) -> Dict:
        """
        Get audit trail statistics.

        Args:
            client: Qdrant client
            memory_id: Filter by memory ID (optional)

        Returns:
            Statistics dictionary
        """
        try:
            # Get all audit entries
            entries = AuditLogger.get_audit_trail(
                client,
                memory_id=memory_id,
                limit=10000  # Get many for statistics
            )

            # Count by action
            action_counts = {}
            for entry in entries:
                action_counts[entry.action.value] = action_counts.get(entry.action.value, 0) + 1

            # Count by actor
            actor_counts = {}
            for entry in entries:
                actor_counts[entry.actor] = actor_counts.get(entry.actor, 0) + 1

            # Recent activity (last 24 hours)
            now = utc_now()
            recent_entries = [
                e for e in entries
                if (now - e.timestamp).total_seconds() < 86400
            ]

            return {
                "total_entries": len(entries),
                "by_action": action_counts,
                "by_actor": actor_counts,
                "recent_24h": len(recent_entries),
                "oldest_entry": entries[-1].timestamp.isoformat() if entries else None,
                "newest_entry": entries[0].timestamp.isoformat() if entries else None
            }

        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {"error": str(e)}


class RestoreManager:
    """Manages undo/restore operations using audit trail."""

    @staticmethod
    def get_restorable_versions(
        client: QdrantClient,
        memory_id: str
    ) -> List[Dict]:
        """
        Get list of restorable versions for a memory.

        Args:
            client: Qdrant client
            memory_id: Memory ID

        Returns:
            List of restorable versions with metadata
        """
        try:
            # Get audit trail for this memory
            entries = AuditLogger.get_audit_trail(
                client,
                memory_id=memory_id,
                limit=100
            )

            # Filter to entries with old_values (restorable changes)
            restorable = []
            for entry in entries:
                if entry.old_values and entry.action in [
                    AuditAction.UPDATE,
                    AuditAction.STATE_TRANSITION,
                    AuditAction.TIER_PROMOTION
                ]:
                    restorable.append({
                        "timestamp": entry.timestamp.isoformat(),
                        "action": entry.action.value,
                        "actor": entry.actor,
                        "reason": entry.reason,
                        "old_values": entry.old_values,
                        "new_values": entry.new_values
                    })

            return restorable

        except Exception as e:
            logger.error(f"Failed to get restorable versions: {e}")
            return []

    @staticmethod
    def restore_to_version(
        client: QdrantClient,
        collection_name: str,
        memory_id: str,
        target_timestamp: str,
        actor: str = "system"
    ) -> Dict:
        """
        Restore a memory to a previous version.

        Args:
            client: Qdrant client
            collection_name: Memory collection name
            memory_id: Memory ID
            target_timestamp: Timestamp to restore to
            actor: Who is performing the restore

        Returns:
            Result dictionary
        """
        try:
            # Get audit trail
            entries = AuditLogger.get_audit_trail(
                client,
                memory_id=memory_id,
                limit=100
            )

            # Find entry matching target timestamp
            target_entry = None
            for entry in entries:
                if entry.timestamp.isoformat() == target_timestamp:
                    target_entry = entry
                    break

            if not target_entry:
                return {
                    "success": False,
                    "error": f"No audit entry found for timestamp {target_timestamp}"
                }

            if not target_entry.old_values:
                return {
                    "success": False,
                    "error": "Cannot restore: no old values available"
                }

            # Get current memory state
            current_response = client.retrieve(
                collection_name=collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False
            )

            if not current_response:
                return {
                    "success": False,
                    "error": "Memory not found"
                }

            current_payload = current_response[0].payload

            # Apply old values as current values
            restored_values = target_entry.old_values.copy()

            # Update in Qdrant
            client.set_payload(
                collection_name=collection_name,
                payload=restored_values,
                points=[memory_id]
            )

            # Sanitize restored content and tags (snapshots may predate enrichment pipeline)
            try:
                from .enhancements import clean_content, normalize_tags
                sanitized = {}
                if "content" in restored_values and restored_values["content"]:
                    sanitized["content"] = clean_content(restored_values["content"])
                if "tags" in restored_values and restored_values["tags"]:
                    sanitized["tags"] = normalize_tags(restored_values["tags"])
                if sanitized:
                    client.set_payload(
                        collection_name=collection_name,
                        payload=sanitized,
                        points=[memory_id]
                    )
            except Exception as e:
                logger.warning(f"Sanitization failed for restored {memory_id}: {e}")

            # Recalculate quality score after restoration
            try:
                from .quality_tracking import QualityScoreCalculator
                QualityScoreCalculator.recalculate_single_memory_quality(
                    client, collection_name, memory_id
                )
            except Exception as e:
                logger.warning(f"Quality recalc failed for restored {memory_id}: {e}")

            # Log the restore action
            AuditLogger.log_action(
                client,
                memory_id=memory_id,
                action=AuditAction.RESTORE,
                actor=actor,
                old_values={k: current_payload.get(k) for k in restored_values.keys()},
                new_values=restored_values,
                reason=f"Restored to version from {target_timestamp}",
                metadata={
                    "restored_from_timestamp": target_timestamp,
                    "restored_from_action": target_entry.action.value
                }
            )

            return {
                "success": True,
                "memory_id": memory_id,
                "restored_to": target_timestamp,
                "restored_fields": list(restored_values.keys())
            }

        except Exception as e:
            logger.error(f"Failed to restore memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def undo_last_change(
        client: QdrantClient,
        collection_name: str,
        memory_id: str,
        actor: str = "system"
    ) -> Dict:
        """
        Undo the last change to a memory.

        Args:
            client: Qdrant client
            collection_name: Memory collection name
            memory_id: Memory ID
            actor: Who is performing the undo

        Returns:
            Result dictionary
        """
        try:
            # Get audit trail
            entries = AuditLogger.get_audit_trail(
                client,
                memory_id=memory_id,
                limit=10
            )

            if not entries:
                return {
                    "success": False,
                    "error": "No audit history found for memory"
                }

            # Find most recent change with old_values
            last_change = None
            for entry in entries:
                if entry.old_values and entry.action not in [AuditAction.CREATE, AuditAction.RESTORE]:
                    last_change = entry
                    break

            if not last_change:
                return {
                    "success": False,
                    "error": "No undoable changes found"
                }

            # Restore to that version
            return RestoreManager.restore_to_version(
                client,
                collection_name,
                memory_id,
                last_change.timestamp.isoformat(),
                actor
            )

        except Exception as e:
            logger.error(f"Failed to undo last change: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Helper functions for easy integration

def log_create(
    client: QdrantClient,
    memory_id: str,
    memory_data: Dict,
    actor: str = "system"
):
    """Log memory creation."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.CREATE,
        actor=actor,
        new_values=memory_data,
        reason="Memory created"
    )


def log_update(
    client: QdrantClient,
    memory_id: str,
    old_values: Dict,
    new_values: Dict,
    actor: str = "system",
    reason: Optional[str] = None
):
    """Log memory update."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.UPDATE,
        actor=actor,
        old_values=old_values,
        new_values=new_values,
        reason=reason or "Memory updated"
    )


def log_delete(
    client: QdrantClient,
    memory_id: str,
    memory_data: Dict,
    actor: str = "system",
    reason: Optional[str] = None
):
    """Log memory deletion."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.DELETE,
        actor=actor,
        old_values=memory_data,
        reason=reason or "Memory deleted"
    )


def log_archive(
    client: QdrantClient,
    memory_id: str,
    actor: str = "system",
    reason: Optional[str] = None
):
    """Log memory archival."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.ARCHIVE,
        actor=actor,
        reason=reason or "Memory archived"
    )


def log_state_transition(
    client: QdrantClient,
    memory_id: str,
    old_state: str,
    new_state: str,
    actor: str = "system",
    reason: Optional[str] = None
):
    """Log state transition."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.STATE_TRANSITION,
        actor=actor,
        old_values={"state": old_state},
        new_values={"state": new_state},
        reason=reason or f"State changed: {old_state} → {new_state}"
    )


def log_tier_promotion(
    client: QdrantClient,
    memory_id: str,
    old_tier: str,
    new_tier: str,
    actor: str = "system",
    reason: Optional[str] = None
):
    """Log tier promotion."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.TIER_PROMOTION,
        actor=actor,
        old_values={"memory_tier": old_tier},
        new_values={"memory_tier": new_tier},
        reason=reason or f"Tier promoted: {old_tier} → {new_tier}"
    )


def log_quality_update(
    client: QdrantClient,
    memory_id: str,
    old_quality: float,
    new_quality: float,
    actor: str = "system"
):
    """Log quality score update."""
    AuditLogger.log_action(
        client,
        memory_id=memory_id,
        action=AuditAction.QUALITY_UPDATE,
        actor=actor,
        old_values={"quality_score": old_quality},
        new_values={"quality_score": new_quality},
        reason=f"Quality updated: {old_quality:.3f} → {new_quality:.3f}"
    )
