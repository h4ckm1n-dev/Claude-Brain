"""Memory export and backup functionality.

Supports multiple export formats:
- JSON (with relationships and metadata)
- CSV (for Excel/Google Sheets)
- Obsidian markdown (with wiki links)
- Full system backups
"""

import json
import csv
from io import StringIO, BytesIO
from datetime import datetime, timezone
from typing import Optional, Dict, List
from pathlib import Path
import zipfile
import logging

from . import collections
from .graph import get_graph_stats, is_graph_enabled

logger = logging.getLogger(__name__)


class MemoryExporter:
    """Export memories in various formats."""

    @staticmethod
    def export_json(
        filters: Optional[Dict] = None,
        include_relationships: bool = True,
        include_metadata: bool = True
    ) -> str:
        """
        Export memories as JSON with full fidelity.

        Args:
            filters: Optional filters (type, project, date_from, date_to, tags)
            include_relationships: Include graph relationships
            include_metadata: Include export metadata

        Returns:
            JSON string
        """
        try:
            client = collections.get_client()

            # Apply filters
            memories = MemoryExporter._filter_memories(filters)

            # Prepare export data
            export_data = {
                "memories": []
            }

            if include_metadata:
                export_data["export_metadata"] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_memories": len(memories),
                    "filters_applied": filters or {},
                    "format_version": "1.0",
                    "includes_relationships": include_relationships
                }

            # Build memory data
            for memory in memories:
                memory_data = {
                    "id": memory["id"],
                    "type": memory["type"],
                    "content": memory["content"],
                    "tags": memory.get("tags", []),
                    "project": memory.get("project"),
                    "importance": memory.get("importance", 0.5),
                    "created_at": memory["created_at"],
                    "updated_at": memory.get("updated_at"),
                    "access_count": memory.get("access_count", 0),
                    "resolved": memory.get("resolved", False),
                }

                # Include type-specific fields
                if memory.get("error_message"):
                    memory_data["error_message"] = memory["error_message"]
                    memory_data["solution"] = memory.get("solution")

                if memory.get("decision"):
                    memory_data["decision"] = memory["decision"]
                    memory_data["rationale"] = memory.get("rationale")

                # Include relationships
                if include_relationships:
                    memory_data["relations"] = memory.get("relations", [])

                export_data["memories"].append(memory_data)

            return json.dumps(export_data, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise

    @staticmethod
    def export_csv(filters: Optional[Dict] = None) -> str:
        """
        Export memories as CSV for Excel/Google Sheets.

        Args:
            filters: Optional filters

        Returns:
            CSV string
        """
        try:
            memories = MemoryExporter._filter_memories(filters)

            output = StringIO()
            writer = csv.writer(output)

            # Header row
            writer.writerow([
                "ID",
                "Type",
                "Content",
                "Tags",
                "Project",
                "Importance",
                "Created",
                "Access Count",
                "Resolved"
            ])

            # Data rows
            for memory in memories:
                writer.writerow([
                    memory["id"],
                    memory["type"],
                    memory["content"][:500],  # Truncate for CSV
                    "|".join(memory.get("tags", [])),
                    memory.get("project", ""),
                    memory.get("importance", 0.5),
                    memory["created_at"],
                    memory.get("access_count", 0),
                    "Yes" if memory.get("resolved") else "No"
                ])

            return output.getvalue()

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise

    @staticmethod
    def export_obsidian(filters: Optional[Dict] = None) -> BytesIO:
        """
        Export as Obsidian-compatible markdown files in a ZIP archive.

        Each memory becomes a .md file with:
        - Frontmatter (YAML metadata)
        - Content
        - Wiki links to related memories

        Args:
            filters: Optional filters

        Returns:
            BytesIO containing ZIP file
        """
        try:
            memories = MemoryExporter._filter_memories(filters)

            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

                # Create index file
                index_content = "# Memory Export\n\n"
                index_content += f"Exported: {datetime.now(timezone.utc).isoformat()}\n"
                index_content += f"Total Memories: {len(memories)}\n\n"
                index_content += "## Memories by Type\n\n"

                # Group by type for index
                by_type = {}
                for memory in memories:
                    mem_type = memory["type"]
                    if mem_type not in by_type:
                        by_type[mem_type] = []
                    by_type[mem_type].append(memory)

                for mem_type, mems in by_type.items():
                    index_content += f"### {mem_type.title()} ({len(mems)})\n\n"

                zip_file.writestr("README.md", index_content)

                # Create individual memory files
                for memory in memories:
                    # Create filename
                    timestamp = memory["created_at"][:10]  # YYYY-MM-DD
                    mem_id_short = memory["id"][:8]
                    filename = f"{timestamp}_{memory['type']}_{mem_id_short}.md"

                    # Build markdown content with frontmatter
                    content = "---\n"
                    content += f"id: {memory['id']}\n"
                    content += f"type: {memory['type']}\n"
                    content += f"created: {memory['created_at']}\n"
                    content += f"tags: [{', '.join(memory.get('tags', []))}]\n"
                    if memory.get("project"):
                        content += f"project: {memory['project']}\n"
                    content += f"importance: {memory.get('importance', 0.5)}\n"
                    content += "---\n\n"

                    # Title
                    content += f"# {memory['type'].title()}: {memory['content'][:50]}...\n\n"

                    # Main content
                    content += memory["content"] + "\n\n"

                    # Metadata section
                    content += "## Metadata\n\n"
                    content += f"- **Access Count**: {memory.get('access_count', 0)}\n"
                    content += f"- **Resolved**: {'Yes' if memory.get('resolved') else 'No'}\n"

                    # Error-specific fields
                    if memory.get("error_message"):
                        content += f"\n### Error Details\n\n"
                        content += f"```\n{memory['error_message']}\n```\n"
                        if memory.get("solution"):
                            content += f"\n### Solution\n\n{memory['solution']}\n"

                    # Decision-specific fields
                    if memory.get("decision"):
                        content += f"\n### Decision\n\n{memory['decision']}\n"
                        if memory.get("rationale"):
                            content += f"\n**Rationale**: {memory['rationale']}\n"

                    # Related memories (wiki links)
                    relations = memory.get("relations", [])
                    if relations:
                        content += "\n## Related Memories\n\n"
                        for rel in relations:
                            # Create wiki link using target ID
                            target_id_short = rel.get("target_id", "")[:8]
                            rel_type = rel.get("relation_type", "related")
                            content += f"- [[{target_id_short}]] ({rel_type})\n"

                    # Add to ZIP
                    zip_file.writestr(filename, content)

            zip_buffer.seek(0)
            return zip_buffer

        except Exception as e:
            logger.error(f"Obsidian export failed: {e}")
            raise

    @staticmethod
    def create_backup(backup_name: Optional[str] = None) -> Dict:
        """
        Create full system backup including memories and graph.

        Args:
            backup_name: Optional backup name (default: backup_YYYYMMDD_HHMMSS)

        Returns:
            Backup metadata
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"backup_{timestamp}"

            # Export all memories with relationships
            all_memories_json = MemoryExporter.export_json(
                include_relationships=True,
                include_metadata=True
            )

            # Get graph data if available
            graph_data = {}
            if is_graph_enabled():
                try:
                    graph_data = get_graph_stats()
                except:
                    logger.warning("Failed to get graph stats for backup")

            # Create backup structure
            backup_data = {
                "backup_metadata": {
                    "name": backup_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_memories": MemoryExporter._count_total_memories(),
                    "format_version": "1.0"
                },
                "memories": json.loads(all_memories_json),
                "graph": graph_data
            }

            # Save to file
            backup_dir = Path.home() / ".claude" / "memory" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_path = backup_dir / f"{backup_name}.json"

            with open(backup_path, "w") as f:
                json.dump(backup_data, f, indent=2)

            size_mb = backup_path.stat().st_size / 1024 / 1024

            return {
                "backup_id": backup_name,
                "path": str(backup_path),
                "size_mb": round(size_mb, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_memories": backup_data["backup_metadata"]["total_memories"]
            }

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise

    @staticmethod
    def list_backups() -> List[Dict]:
        """
        List all available backups.

        Returns:
            List of backup metadata
        """
        try:
            backup_dir = Path.home() / ".claude" / "memory" / "backups"

            if not backup_dir.exists():
                return []

            backups = []
            for backup_file in sorted(backup_dir.glob("*.json"), reverse=True):
                try:
                    with open(backup_file) as f:
                        data = json.load(f)
                        metadata = data.get("backup_metadata", {})

                    backups.append({
                        "id": metadata.get("name", backup_file.stem),
                        "timestamp": metadata.get("timestamp"),
                        "size_mb": round(backup_file.stat().st_size / 1024 / 1024, 2),
                        "memory_count": metadata.get("total_memories", 0),
                        "path": str(backup_file)
                    })
                except Exception as e:
                    logger.warning(f"Failed to read backup {backup_file}: {e}")
                    continue

            return backups

        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    @staticmethod
    def _filter_memories(filters: Optional[Dict]) -> List[Dict]:
        """
        Apply filters to memory query.

        Filters:
        - type: Memory type
        - project: Project name
        - date_from: ISO format date
        - date_to: ISO format date
        - tags: List of tags (OR)

        Returns:
            List of memory payloads
        """
        try:
            client = collections.get_client()

            # Get all memories (we'll filter in Python for simplicity)
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                limit=10000,  # Get all
                with_payload=True,
                with_vectors=False
            )

            memories = []

            for record in records:
                payload = dict(record.payload)
                payload["id"] = str(record.id)

                # Apply filters
                if filters:
                    # Type filter
                    if filters.get("type") and payload.get("type") != filters["type"]:
                        continue

                    # Project filter
                    if filters.get("project") and payload.get("project") != filters["project"]:
                        continue

                    # Date filters
                    created_at = datetime.fromisoformat(payload["created_at"].replace('Z', '+00:00'))

                    if filters.get("date_from"):
                        date_from = datetime.fromisoformat(filters["date_from"])
                        if created_at < date_from:
                            continue

                    if filters.get("date_to"):
                        date_to = datetime.fromisoformat(filters["date_to"])
                        if created_at > date_to:
                            continue

                    # Tags filter (OR - any tag matches)
                    if filters.get("tags"):
                        filter_tags = set(filters["tags"])
                        memory_tags = set(payload.get("tags", []))
                        if not filter_tags.intersection(memory_tags):
                            continue

                memories.append(payload)

            return memories

        except Exception as e:
            logger.error(f"Memory filtering failed: {e}")
            raise

    @staticmethod
    def _count_total_memories() -> int:
        """Count total memories in collection."""
        try:
            client = collections.get_client()
            collection_info = client.get_collection(collections.COLLECTION_NAME)
            return collection_info.points_count
        except:
            return 0
