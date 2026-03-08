"""Adaptive context builder for enriched get_context() responses.

Dynamically assembles context with graph stats, hotspots, staleness alerts,
knowledge gaps, active flows, and project health — scaled to project size.
"""

import logging
from typing import Optional
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.http import models

from .models import utc_now

logger = logging.getLogger(__name__)

# Adaptive threshold: escalate to full context when project exceeds this
ESCALATION_MEMORY_THRESHOLD = 50


def build_enriched_context(
    client: QdrantClient,
    collection_name: str,
    project: Optional[str] = None,
) -> dict:
    """Build enriched context beyond pinned + unresolved errors.

    Returns additional sections that get_context() merges into its response.
    Adapts based on project size and detected alerts.
    """
    context = {}

    try:
        # Always included: graph summary
        context["graph_summary"] = _get_graph_summary(project)

        # Count project memories to determine escalation
        memory_count = _count_project_memories(client, collection_name, project)

        # Always included: hotspots (most connected memories)
        context["hotspots"] = _get_hotspot_memories(project, limit=5)

        # Get staleness alerts (always check — triggers escalation)
        stale_alerts = _get_staleness_alerts(client, collection_name, project)
        context["alerts"] = {"stale_memories": stale_alerts}

        # Get knowledge gaps
        gaps = _get_knowledge_gaps(client, collection_name, project)
        context["alerts"]["knowledge_gaps"] = gaps

        # Determine if we should escalate to full context
        should_escalate = (
            memory_count > ESCALATION_MEMORY_THRESHOLD
            or len(stale_alerts) > 0
            or len(gaps) > 2
        )

        context["mode"] = "full" if should_escalate else "lightweight"

        if should_escalate:
            # Full context: add flows, activity, health
            context["flows"] = _get_active_flows(project)
            context["recent_activity"] = _get_recent_activity(
                client, collection_name, project
            )
            context["project_health"] = _get_project_health(
                client, collection_name, project
            )

    except Exception as e:
        logger.warning(f"Context enrichment failed: {e}")
        context["error"] = str(e)

    return context


def _get_graph_summary(project: Optional[str]) -> dict:
    """Get graph statistics summary."""
    try:
        from .graph import is_graph_enabled, get_session

        if not is_graph_enabled():
            return {"enabled": False}

        with get_session() as session:
            if session is None:
                return {"enabled": False}

            if project:
                result = session.run("""
                    MATCH (m:Memory)-[:BELONGS_TO]->(p:Project {name: $project})
                    OPTIONAL MATCH (m)-[r]-(:Memory)
                    RETURN count(DISTINCT m) as nodes,
                           count(DISTINCT r) as edges
                """, {"project": project})
            else:
                result = session.run("""
                    MATCH (m:Memory)
                    OPTIONAL MATCH (m)-[r]-(:Memory)
                    RETURN count(DISTINCT m) as nodes,
                           count(DISTINCT r) as edges
                """)

            record = result.single()
            if record:
                return {
                    "enabled": True,
                    "total_memories": record["nodes"],
                    "total_relationships": record["edges"],
                }

    except Exception as e:
        logger.debug(f"Graph summary failed: {e}")

    return {"enabled": True, "total_memories": 0, "total_relationships": 0}


def _count_project_memories(
    client: QdrantClient, collection_name: str, project: Optional[str]
) -> int:
    """Count memories in a project."""
    try:
        filters = [
            models.FieldCondition(
                key="archived", match=models.MatchValue(value=False)
            )
        ]
        if project:
            filters.append(
                models.FieldCondition(
                    key="project", match=models.MatchValue(value=project)
                )
            )

        result = client.count(
            collection_name=collection_name,
            count_filter=models.Filter(must=filters),
        )
        return result.count

    except Exception:
        return 0


def _get_hotspot_memories(project: Optional[str], limit: int = 5) -> list[dict]:
    """Get most-connected memory nodes from the graph."""
    try:
        from .graph import is_graph_enabled, get_session

        if not is_graph_enabled():
            return []

        with get_session() as session:
            if session is None:
                return []

            project_filter = ""
            params: dict = {"limit": limit}
            if project:
                project_filter = "-[:BELONGS_TO]->(:Project {name: $project})"
                params["project"] = project

            result = session.run(f"""
                MATCH (m:Memory){project_filter}
                OPTIONAL MATCH (m)-[r]-(:Memory)
                WITH m, count(r) as connections
                WHERE connections > 0
                RETURN m.id as id,
                       m.type as type,
                       m.content_preview as preview,
                       connections
                ORDER BY connections DESC
                LIMIT $limit
            """, params)

            return [
                {
                    "id": record["id"],
                    "type": record["type"],
                    "preview": record["preview"],
                    "connections": record["connections"],
                }
                for record in result
            ]

    except Exception as e:
        logger.debug(f"Hotspot query failed: {e}")
        return []


def _get_staleness_alerts(
    client: QdrantClient, collection_name: str, project: Optional[str]
) -> list[dict]:
    """Get memories with high staleness scores."""
    try:
        from .staleness import get_stale_memories
        return get_stale_memories(
            client, collection_name,
            threshold=0.5, project=project, limit=5,
        )
    except Exception as e:
        logger.debug(f"Staleness alerts failed: {e}")
        return []


def _get_knowledge_gaps(
    client: QdrantClient, collection_name: str, project: Optional[str]
) -> list[dict]:
    """Find areas with few memories or low average quality."""
    gaps = []

    try:
        # Get all tags and their memory counts + avg quality
        filters = [
            models.FieldCondition(
                key="archived", match=models.MatchValue(value=False)
            )
        ]
        if project:
            filters.append(
                models.FieldCondition(
                    key="project", match=models.MatchValue(value=project)
                )
            )

        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=filters),
            limit=1000,
            with_payload=["tags", "quality_score"],
        )

        # Aggregate by tag
        tag_stats: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total_quality": 0.0}
        )
        for point in results:
            quality = point.payload.get("quality_score", 0.5)
            for tag in point.payload.get("tags", []):
                tag_stats[tag]["count"] += 1
                tag_stats[tag]["total_quality"] += quality

        # Find tags with low coverage or quality
        for tag, stats in tag_stats.items():
            avg_quality = stats["total_quality"] / stats["count"] if stats["count"] > 0 else 0
            if stats["count"] <= 2 or avg_quality < 0.45:
                gaps.append({
                    "area": tag,
                    "memory_count": stats["count"],
                    "avg_quality": round(avg_quality, 2),
                })

        # Sort by quality (worst first), limit to top 5
        gaps.sort(key=lambda g: g["avg_quality"])
        return gaps[:5]

    except Exception as e:
        logger.debug(f"Knowledge gaps query failed: {e}")
        return []


def _get_active_flows(project: Optional[str]) -> list[dict]:
    """Get active knowledge flows."""
    try:
        from .flow_detection import get_flows
        flows = get_flows(project=project, limit=5)
        return [
            {
                "id": f.get("id", ""),
                "label": f.get("label", ""),
                "flow_type": f.get("flow_type", ""),
                "steps": f.get("step_count", 0),
            }
            for f in flows
        ]
    except Exception as e:
        logger.debug(f"Active flows query failed: {e}")
        return []


def _get_recent_activity(
    client: QdrantClient, collection_name: str, project: Optional[str]
) -> dict:
    """Summarize memory activity in the last 24 hours."""
    from datetime import timedelta

    cutoff = (utc_now() - timedelta(hours=24)).isoformat()

    try:
        filters = [
            models.FieldCondition(
                key="created_at", range=models.Range(gte=cutoff)
            ),
        ]
        if project:
            filters.append(
                models.FieldCondition(
                    key="project", match=models.MatchValue(value=project)
                )
            )

        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=filters),
            limit=200,
            with_payload=["type"],
        )

        by_type: dict[str, int] = defaultdict(int)
        for point in results:
            by_type[point.payload.get("type", "unknown")] += 1

        return {
            "total_24h": len(results),
            "by_type": dict(by_type),
        }

    except Exception as e:
        logger.debug(f"Recent activity query failed: {e}")
        return {"total_24h": 0, "by_type": {}}


def _get_project_health(
    client: QdrantClient, collection_name: str, project: Optional[str]
) -> dict:
    """Get project health metrics."""
    try:
        filters = [
            models.FieldCondition(
                key="archived", match=models.MatchValue(value=False)
            )
        ]
        if project:
            filters.append(
                models.FieldCondition(
                    key="project", match=models.MatchValue(value=project)
                )
            )

        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=filters),
            limit=2000,
            with_payload=["type", "quality_score", "memory_strength"],
        )

        if not results:
            return {}

        by_type: dict[str, int] = defaultdict(int)
        total_quality = 0.0
        total_strength = 0.0

        for point in results:
            by_type[point.payload.get("type", "unknown")] += 1
            total_quality += point.payload.get("quality_score", 0.5)
            total_strength += point.payload.get("memory_strength", 1.0)

        n = len(results)
        return {
            "total_memories": n,
            "by_type": dict(by_type),
            "avg_quality": round(total_quality / n, 2),
            "avg_strength": round(total_strength / n, 2),
        }

    except Exception as e:
        logger.debug(f"Project health query failed: {e}")
        return {}
