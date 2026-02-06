"""Session-based memory extraction for conversational context.

Implements Phase 1.3: Session-based Memory Extraction
- Track conversation sessions and turn sequences
- Extract implicit relationships from conversation flow
- Identify causal chains across multiple memories
- Consolidate session memories into summaries
- Link memories within sessions with FOLLOWS relationships
"""

import logging
import os
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import Memory, MemoryType, utc_now
from .graph import create_relationship, is_graph_enabled

logger = logging.getLogger(__name__)

# Configuration
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "2"))
SESSION_CONSOLIDATION_DELAY_HOURS = int(os.getenv("SESSION_CONSOLIDATION_DELAY_HOURS", "24"))
MAX_CONVERSATION_CONTEXT_CHARS = 500  # Limit context to prevent bloat


class SessionManager:
    """Manages conversation sessions and memory extraction."""

    @staticmethod
    def generate_session_id() -> str:
        """Generate a new session ID."""
        from uuid6 import uuid7
        return f"session_{str(uuid7())}"

    @staticmethod
    def get_or_create_session(
        project: Optional[str] = None,
        existing_session_id: Optional[str] = None
    ) -> str:
        """
        Get existing active session or create new one.

        A session is considered active if it has memories created within
        SESSION_TIMEOUT_HOURS. If no active session exists, creates a new one.

        Args:
            project: Optional project name to scope session
            existing_session_id: Optional session ID to resume

        Returns:
            Session ID (existing or new)
        """
        # If session ID provided and still active, use it
        if existing_session_id:
            return existing_session_id

        # For now, always create new session
        # Future: Could look up last active session for project
        return SessionManager.generate_session_id()

    @staticmethod
    def get_session_memories(
        client: QdrantClient,
        collection_name: str,
        session_id: str
    ) -> List[Memory]:
        """
        Get all memories in a session, ordered by sequence.

        Args:
            client: Qdrant client
            collection_name: Collection name
            session_id: Session ID

        Returns:
            List of memories in session order
        """
        try:
            results, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="session_id",
                            match=models.MatchValue(value=session_id)
                        )
                    ]
                ),
                limit=100,
                with_payload=True
            )

            # Convert to Memory objects
            from .collections import _point_to_memory
            memories = [_point_to_memory(r) for r in results]

            # Sort by session_sequence
            memories.sort(key=lambda m: m.session_sequence or 0)

            return memories

        except Exception as e:
            logger.error(f"Failed to get session memories: {e}")
            return []

    @staticmethod
    def extract_conversation_context(previous_memories: List[Memory], max_chars: int = MAX_CONVERSATION_CONTEXT_CHARS) -> str:
        """
        Extract conversation context from previous memories in session.

        Takes the last 3 memories and creates a summary context string.

        Args:
            previous_memories: List of previous memories in session
            max_chars: Maximum characters for context

        Returns:
            Context string summarizing previous conversation
        """
        if not previous_memories:
            return ""

        # Take last 3 memories
        recent = previous_memories[-3:]

        context_parts = []
        for i, mem in enumerate(recent, 1):
            # Format: "[1] ERROR: content"
            type_label = mem.type.value.upper()
            content_preview = mem.content[:100] if mem.content else ""
            context_parts.append(f"[{i}] {type_label}: {content_preview}")

        context = " → ".join(context_parts)

        # Truncate if too long
        if len(context) > max_chars:
            context = context[:max_chars-3] + "..."

        return context

    @staticmethod
    def infer_session_relationships(
        client: QdrantClient,
        collection_name: str,
        session_id: str
    ) -> int:
        """
        Infer relationships between memories in a session.

        Creates FOLLOWS relationships between sequential memories
        and identifies causal chains.

        Args:
            client: Qdrant client
            collection_name: Collection name
            session_id: Session ID

        Returns:
            Number of relationships created
        """
        if not is_graph_enabled():
            return 0

        try:
            memories = SessionManager.get_session_memories(client, collection_name, session_id)

            if len(memories) < 2:
                return 0

            links_created = 0

            # Create FOLLOWS relationships between sequential memories
            for i in range(len(memories) - 1):
                curr = memories[i]
                next_mem = memories[i + 1]

                # Link curr → next as FOLLOWS
                if create_relationship(curr.id, next_mem.id, "FOLLOWS"):
                    links_created += 1
                    logger.debug(f"Session FOLLOWS: {curr.id} → {next_mem.id}")

            # Identify causal chains (ERROR → LEARNING → DECISION)
            for i in range(len(memories) - 1):
                curr = memories[i]
                next_mem = memories[i + 1]

                # Error followed by learning/decision → FIXES
                if curr.type == MemoryType.ERROR and next_mem.type in [MemoryType.LEARNING, MemoryType.DECISION]:
                    if create_relationship(next_mem.id, curr.id, "FIXES"):
                        links_created += 1
                        logger.info(f"Session causal chain: {next_mem.id} FIXES {curr.id}")

                # Pattern followed by implementation → SUPPORTS
                if curr.type == MemoryType.PATTERN and next_mem.type in [MemoryType.LEARNING, MemoryType.DECISION]:
                    if create_relationship(curr.id, next_mem.id, "SUPPORTS"):
                        links_created += 1
                        logger.info(f"Session support chain: {curr.id} SUPPORTS {next_mem.id}")

            logger.info(f"Created {links_created} session relationships for {session_id}")
            return links_created

        except Exception as e:
            logger.error(f"Failed to infer session relationships: {e}")
            return 0

    @staticmethod
    def consolidate_session(
        client: QdrantClient,
        collection_name: str,
        session_id: str
    ) -> Optional[str]:
        """
        Consolidate a completed session into a summary memory.

        Creates a CONTEXT-type memory that summarizes the session,
        then links all session memories to it.

        Args:
            client: Qdrant client
            collection_name: Collection name
            session_id: Session ID

        Returns:
            Summary memory ID or None if consolidation failed
        """
        try:
            memories = SessionManager.get_session_memories(client, collection_name, session_id)

            if len(memories) < 2:
                logger.debug(f"Session {session_id} has <2 memories, skipping consolidation")
                return None

            # Build summary
            summary_parts = []
            projects = set()
            all_tags = set()
            error_count = 0
            solution_count = 0

            for mem in memories:
                # Track project
                if mem.project:
                    projects.add(mem.project)

                # Track tags
                all_tags.update(mem.tags or [])

                # Count types
                if mem.type == MemoryType.ERROR:
                    error_count += 1
                elif mem.type in [MemoryType.LEARNING, MemoryType.DECISION]:
                    solution_count += 1

                # Add memory summary
                type_label = mem.type.value
                content_preview = mem.content[:80] if mem.content else ""
                summary_parts.append(f"- {type_label.upper()}: {content_preview}")

            # Create summary content
            session_summary = f"Session summary ({len(memories)} memories):\n"

            if error_count > 0 and solution_count > 0:
                session_summary += f"Problem-solving session: {error_count} errors, {solution_count} solutions\n\n"
            elif error_count > 0:
                session_summary += f"Error investigation: {error_count} errors encountered\n\n"
            elif solution_count > 0:
                session_summary += f"Implementation session: {solution_count} decisions/learnings\n\n"
            else:
                session_summary += "General development session\n\n"

            session_summary += "Sequence:\n" + "\n".join(summary_parts)

            # Create summary memory
            from .collections import store_memory
            from .models import MemoryCreate

            summary_data = MemoryCreate(
                type=MemoryType.CONTEXT,
                content=session_summary[:1000],  # Limit length
                tags=list(all_tags)[:10] + ["session-summary"],  # Limit tags
                project=list(projects)[0] if projects else None,
                session_id=session_id
            )

            summary_memory = store_memory(summary_data, deduplicate=False)

            # Link all session memories to summary
            if is_graph_enabled():
                for mem in memories:
                    create_relationship(mem.id, summary_memory.id, "PART_OF")

            logger.info(f"Consolidated session {session_id} into summary {summary_memory.id}")
            return summary_memory.id

        except Exception as e:
            logger.error(f"Failed to consolidate session {session_id}: {e}")
            return None

    @staticmethod
    def get_sessions_for_consolidation(
        client: QdrantClient,
        collection_name: str,
        older_than_hours: int = SESSION_CONSOLIDATION_DELAY_HOURS
    ) -> List[str]:
        """
        Find sessions ready for consolidation.

        Sessions are ready if:
        1. They have ≥2 memories
        2. Last memory was created >older_than_hours ago
        3. No summary memory exists yet

        Args:
            client: Qdrant client
            collection_name: Collection name
            older_than_hours: Hours to wait before consolidating

        Returns:
            List of session IDs ready for consolidation
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)

            # Get all memories with session_id that are old enough
            results, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="created_at",
                            range=models.DatetimeRange(lte=cutoff_time)
                        )
                    ],
                    must_not=[
                        models.IsNullCondition(is_null=models.PayloadField(key="session_id"))
                    ]
                ),
                limit=1000,
                with_payload=True
            )

            # Group by session
            sessions: Dict[str, List] = defaultdict(list)
            for r in results:
                session_id = r.payload.get("session_id")
                if session_id:
                    sessions[session_id].append(r)

            # Filter sessions ready for consolidation
            ready_sessions = []
            for session_id, mems in sessions.items():
                # Need at least 2 memories
                if len(mems) < 2:
                    continue

                # Check if already has summary (type=context, session_id match)
                has_summary = any(
                    m.payload.get("type") == "context" and
                    "session-summary" in m.payload.get("tags", [])
                    for m in mems
                )

                if not has_summary:
                    ready_sessions.append(session_id)

            logger.info(f"Found {len(ready_sessions)} sessions ready for consolidation")
            return ready_sessions

        except Exception as e:
            logger.error(f"Failed to get sessions for consolidation: {e}")
            return []

    @staticmethod
    def get_session_stats(
        client: QdrantClient,
        collection_name: str
    ) -> Dict:
        """
        Get statistics about sessions.

        Returns:
            Dictionary with session statistics
        """
        try:
            # Get all memories with session_id
            results, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must_not=[
                        models.IsNullCondition(is_null=models.PayloadField(key="session_id"))
                    ]
                ),
                limit=10000,
                with_payload=True
            )

            # Group by session
            sessions: Dict[str, List] = defaultdict(list)
            for r in results:
                session_id = r.payload.get("session_id")
                if session_id:
                    sessions[session_id].append(r)

            # Calculate stats
            total_sessions = len(sessions)
            total_memories_in_sessions = len(results)
            sessions_with_summary = 0
            avg_memories_per_session = 0

            if total_sessions > 0:
                avg_memories_per_session = total_memories_in_sessions / total_sessions

                # Count sessions with summaries
                for session_mems in sessions.values():
                    has_summary = any(
                        m.payload.get("type") == "context" and
                        "session-summary" in m.payload.get("tags", [])
                        for m in session_mems
                    )
                    if has_summary:
                        sessions_with_summary += 1

            return {
                "total_sessions": total_sessions,
                "total_memories_in_sessions": total_memories_in_sessions,
                "avg_memories_per_session": round(avg_memories_per_session, 2),
                "sessions_with_summary": sessions_with_summary,
                "sessions_without_summary": total_sessions - sessions_with_summary,
                "config": {
                    "session_timeout_hours": SESSION_TIMEOUT_HOURS,
                    "consolidation_delay_hours": SESSION_CONSOLIDATION_DELAY_HOURS,
                    "max_context_chars": MAX_CONVERSATION_CONTEXT_CHARS
                }
            }

        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}
