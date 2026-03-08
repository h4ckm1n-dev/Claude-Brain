"""Memory flow detection and tracing.

Discovers meaningful chains of related memories (knowledge flows):
- Resolution flows: ERROR -> FIXES -> LEARNING/PATTERN
- Evolution flows: DECISION -> SUPERSEDES -> DECISION
- Causal flows: ERROR -> CAUSES -> ERROR -> FIXES -> PATTERN
- Knowledge building: LEARNING -> SUPPORTS -> DECISION

Two modes:
- Auto-detection: scheduled job finds all flows
- On-demand trace: BFS from a given memory
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from .graph import is_graph_enabled, get_session
from .models import utc_now

logger = logging.getLogger(__name__)

# Relationship types that form meaningful flows (directed)
FLOW_EDGE_TYPES = ["FIXES", "FOLLOWS", "CAUSES", "SUPPORTS", "SUPERSEDES"]

# Minimum chain length to qualify as a flow
MIN_FLOW_STEPS = 3

# Flow type classification based on memory types in chain
FLOW_TYPE_RULES = {
    "resolution": {"entry_types": {"error"}, "terminal_types": {"pattern", "learning", "decision"}},
    "evolution": {"entry_types": {"decision"}, "terminal_types": {"decision"}},
    "causal": {"entry_types": {"error"}, "terminal_types": {"error", "pattern"}},
    "knowledge_building": {"entry_types": {"learning"}, "terminal_types": {"decision", "pattern"}},
}


def trace_from_memory(
    memory_id: str,
    direction: str = "both",
    max_depth: int = 10,
) -> dict:
    """Trace a flow from a given memory via BFS.

    Args:
        memory_id: Starting memory ID
        direction: "forward" (outgoing), "backward" (incoming), or "both"
        max_depth: Maximum traversal depth

    Returns:
        Dict with chain (ordered steps), total_steps, and flow_type.
    """
    if not is_graph_enabled():
        return {"chain": [], "total_steps": 0, "flow_type": "unknown", "error": "graph_disabled"}

    edge_types = "|".join(FLOW_EDGE_TYPES)

    with get_session() as session:
        if session is None:
            return {"chain": [], "total_steps": 0, "flow_type": "unknown", "error": "no_session"}

        try:
            chain = []

            if direction in ("backward", "both"):
                # Trace backward (incoming edges)
                backward = _trace_direction(
                    session, memory_id, edge_types, max_depth, "backward"
                )
                chain = list(reversed(backward))

            # Add the starting node
            start_node = _get_memory_node(session, memory_id)
            if start_node:
                start_node["is_origin"] = True
                chain.append(start_node)

            if direction in ("forward", "both"):
                # Trace forward (outgoing edges)
                forward = _trace_direction(
                    session, memory_id, edge_types, max_depth, "forward"
                )
                chain.extend(forward)

            # Assign step numbers
            for i, step in enumerate(chain):
                step["step"] = i

            # Classify flow type
            flow_type = _classify_flow(chain)

            return {
                "chain": chain,
                "total_steps": len(chain),
                "flow_type": flow_type,
                "origin_id": memory_id,
            }

        except Exception as e:
            logger.error(f"Flow trace from {memory_id} failed: {e}")
            return {"chain": [], "total_steps": 0, "flow_type": "unknown", "error": str(e)}


def detect_all_flows(
    project: Optional[str] = None,
    max_flows: int = 100,
) -> dict:
    """Auto-detect all meaningful flows in the knowledge graph.

    Algorithm:
    1. Find entry points (memories with 0 incoming flow edges or high out-degree)
    2. BFS forward from each entry point
    3. Chains of 3+ steps become named Flow nodes

    Returns:
        Stats dict with flows_created, flows_updated, entry_points_found.
    """
    if not is_graph_enabled():
        return {"flows_created": 0, "error": "graph_disabled"}

    stats = {"entry_points_found": 0, "flows_created": 0, "flows_updated": 0}
    edge_types = "|".join(FLOW_EDGE_TYPES)

    with get_session() as session:
        if session is None:
            return {"flows_created": 0, "error": "no_session"}

        try:
            # Find entry points: memories with outgoing flow edges but few/no incoming
            project_filter = ""
            params: dict = {}
            if project:
                project_filter = "AND m.project = $project"
                params["project"] = project

            entry_query = f"""
                MATCH (m:Memory)
                WHERE NOT m.type IS NULL {project_filter}
                OPTIONAL MATCH (m)<-[rin:{edge_types}]-(:Memory)
                OPTIONAL MATCH (m)-[rout:{edge_types}]->(:Memory)
                WITH m,
                     count(DISTINCT rin) as in_count,
                     count(DISTINCT rout) as out_count
                WHERE in_count = 0 AND out_count > 0
                RETURN m.id as id, m.type as type, out_count
                ORDER BY out_count DESC
                LIMIT 200
            """
            entry_results = session.run(entry_query, params)
            entry_points = [dict(r) for r in entry_results]
            stats["entry_points_found"] = len(entry_points)

            # BFS from each entry point
            seen_flows = set()
            for entry in entry_points:
                if stats["flows_created"] >= max_flows:
                    break

                entry_id = entry["id"]
                chain = _trace_direction(
                    session, entry_id, edge_types, max_depth=15, direction="forward"
                )

                # Add entry node
                entry_node = _get_memory_node(session, entry_id)
                if entry_node:
                    full_chain = [entry_node] + chain
                else:
                    full_chain = chain

                if len(full_chain) < MIN_FLOW_STEPS:
                    continue

                # Dedup: hash the chain by sorted IDs
                chain_key = tuple(sorted(s["memory_id"] for s in full_chain))
                if chain_key in seen_flows:
                    continue
                seen_flows.add(chain_key)

                # Classify and create flow
                flow_type = _classify_flow(full_chain)
                flow_id = f"flow_{uuid4().hex[:12]}"
                label = _generate_flow_label(full_chain, flow_type)
                terminal_id = full_chain[-1]["memory_id"] if full_chain else None

                _create_flow_in_graph(
                    session, flow_id, label, flow_type,
                    len(full_chain), entry_id, terminal_id,
                    project, full_chain,
                )
                stats["flows_created"] += 1

        except Exception as e:
            logger.error(f"Flow detection failed: {e}")

    return stats


def get_flows(
    project: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Get all detected flows, optionally filtered by project."""
    if not is_graph_enabled():
        return []

    with get_session() as session:
        if session is None:
            return []

        try:
            project_filter = ""
            params: dict = {"limit": limit}
            if project:
                project_filter = "WHERE f.project = $project"
                params["project"] = project

            query = f"""
                MATCH (f:Flow)
                {project_filter}
                OPTIONAL MATCH (m:Memory)-[s:STEP_IN_FLOW]->(f)
                WITH f, count(m) as actual_steps
                RETURN f.id as id,
                       f.label as label,
                       f.flow_type as flow_type,
                       f.step_count as step_count,
                       actual_steps,
                       f.entry_id as entry_id,
                       f.terminal_id as terminal_id,
                       f.project as project,
                       f.created_at as created_at
                ORDER BY f.created_at DESC
                LIMIT $limit
            """
            results = session.run(query, params)
            return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Failed to get flows: {e}")
            return []


# ── Internal helpers ──────────────────────────────────────────────────────


def _trace_direction(
    session, memory_id: str, edge_types: str, max_depth: int, direction: str
) -> list[dict]:
    """BFS trace in one direction from a memory."""
    if direction == "forward":
        query = f"""
            MATCH path = (start:Memory {{id: $id}})-[r:{edge_types}*1..{max_depth}]->(target:Memory)
            WITH target, length(path) as depth,
                 [rel in relationships(path) | type(rel)] as rel_types,
                 [n in nodes(path) | n.id] as node_ids
            RETURN DISTINCT target.id as memory_id,
                   target.type as type,
                   target.content_preview as preview,
                   depth,
                   rel_types,
                   node_ids
            ORDER BY depth
        """
    else:
        query = f"""
            MATCH path = (start:Memory {{id: $id}})<-[r:{edge_types}*1..{max_depth}]-(source:Memory)
            WITH source, length(path) as depth,
                 [rel in relationships(path) | type(rel)] as rel_types,
                 [n in nodes(path) | n.id] as node_ids
            RETURN DISTINCT source.id as memory_id,
                   source.type as type,
                   source.content_preview as preview,
                   depth,
                   rel_types,
                   node_ids
            ORDER BY depth
        """

    try:
        results = session.run(query, {"id": memory_id})
        seen = set()
        chain = []
        for record in results:
            mid = record["memory_id"]
            if mid not in seen and mid != memory_id:
                seen.add(mid)
                chain.append({
                    "memory_id": mid,
                    "type": record["type"],
                    "preview": record["preview"],
                    "depth": record["depth"],
                    "relationship": record["rel_types"][-1] if record["rel_types"] else None,
                })
        return chain
    except Exception as e:
        logger.debug(f"Trace direction failed: {e}")
        return []


def _get_memory_node(session, memory_id: str) -> Optional[dict]:
    """Get a single memory node's info."""
    try:
        result = session.run(
            "MATCH (m:Memory {id: $id}) RETURN m.id as memory_id, m.type as type, m.content_preview as preview",
            {"id": memory_id},
        )
        record = result.single()
        if record:
            return {
                "memory_id": record["memory_id"],
                "type": record["type"],
                "preview": record["preview"],
                "relationship": None,
            }
    except Exception:
        pass
    return None


def _classify_flow(chain: list[dict]) -> str:
    """Classify a flow based on memory types in the chain."""
    if not chain:
        return "unknown"

    entry_type = (chain[0].get("type") or "").lower()
    terminal_type = (chain[-1].get("type") or "").lower()

    for flow_type, rules in FLOW_TYPE_RULES.items():
        if entry_type in rules["entry_types"] and terminal_type in rules["terminal_types"]:
            return flow_type

    return "mixed"


def _generate_flow_label(chain: list[dict], flow_type: str) -> str:
    """Generate a human-readable label for a flow."""
    if not chain:
        return f"Empty {flow_type} flow"

    entry_preview = (chain[0].get("preview") or "")[:40]
    type_label = flow_type.replace("_", " ").title()
    return f"{type_label}: {entry_preview}"


def _create_flow_in_graph(
    session, flow_id: str, label: str, flow_type: str,
    step_count: int, entry_id: str, terminal_id: Optional[str],
    project: Optional[str], chain: list[dict],
) -> None:
    """Create a Flow node and STEP_IN_FLOW edges in Neo4j."""
    try:
        session.run("""
            MERGE (f:Flow {id: $id})
            SET f.label = $label,
                f.flow_type = $flow_type,
                f.step_count = $step_count,
                f.entry_id = $entry_id,
                f.terminal_id = $terminal_id,
                f.project = $project,
                f.created_at = datetime()
        """, {
            "id": flow_id,
            "label": label,
            "flow_type": flow_type,
            "step_count": step_count,
            "entry_id": entry_id,
            "terminal_id": terminal_id,
            "project": project,
        })

        # Create STEP_IN_FLOW edges
        for i, step in enumerate(chain):
            session.run("""
                MATCH (m:Memory {id: $memory_id})
                MATCH (f:Flow {id: $flow_id})
                MERGE (m)-[s:STEP_IN_FLOW]->(f)
                SET s.step = $step
            """, {
                "memory_id": step["memory_id"],
                "flow_id": flow_id,
                "step": i,
            })

    except Exception as e:
        logger.warning(f"Failed to create flow {flow_id}: {e}")
