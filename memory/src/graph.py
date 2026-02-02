"""Neo4j knowledge graph for memory relationships.

Tracks:
- Memory relationships (FIXES, CAUSES, RELATES_TO, etc.)
- Temporal evolution of knowledge
- Project and tag connections
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "memory_graph_2024")

_driver = None


def get_driver():
    """Get or create Neo4j driver."""
    global _driver

    if _driver is None:
        try:
            from neo4j import GraphDatabase
            _driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Verify connection
            _driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {NEO4J_URI}")
        except ImportError:
            logger.warning("neo4j package not installed, graph features disabled")
            _driver = "disabled"
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            _driver = "disabled"

    return _driver


def is_graph_enabled() -> bool:
    """Check if graph database is available."""
    driver = get_driver()
    return driver is not None and driver != "disabled"


@contextmanager
def get_session():
    """Get a Neo4j session context manager."""
    driver = get_driver()
    if driver == "disabled":
        yield None
        return

    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def init_graph_schema():
    """Initialize Neo4j schema with indexes and constraints."""
    if not is_graph_enabled():
        return False

    with get_session() as session:
        if session is None:
            return False

        try:
            # Create constraints for unique memory IDs
            session.run("""
                CREATE CONSTRAINT memory_id IF NOT EXISTS
                FOR (m:Memory) REQUIRE m.id IS UNIQUE
            """)

            # Create constraint for unique projects
            session.run("""
                CREATE CONSTRAINT project_name IF NOT EXISTS
                FOR (p:Project) REQUIRE p.name IS UNIQUE
            """)

            # Create constraint for unique tags
            session.run("""
                CREATE CONSTRAINT tag_name IF NOT EXISTS
                FOR (t:Tag) REQUIRE t.name IS UNIQUE
            """)

            # Create indexes for common queries
            session.run("""
                CREATE INDEX memory_type IF NOT EXISTS
                FOR (m:Memory) ON (m.type)
            """)

            session.run("""
                CREATE INDEX memory_created IF NOT EXISTS
                FOR (m:Memory) ON (m.created_at)
            """)

            logger.info("Neo4j schema initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize graph schema: {e}")
            return False


def create_memory_node(
    memory_id: str,
    memory_type: str,
    content_preview: str,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    created_at: Optional[datetime] = None
) -> bool:
    """Create a Memory node in the graph.

    Args:
        memory_id: Unique memory ID (from Qdrant)
        memory_type: Type of memory (error, decision, etc.)
        content_preview: First 200 chars of content
        project: Optional project name
        tags: Optional list of tags
        created_at: Creation timestamp

    Returns:
        True if created successfully
    """
    if not is_graph_enabled():
        return False

    with get_session() as session:
        if session is None:
            return False

        try:
            timestamp = created_at or datetime.now(timezone.utc)

            # Create memory node
            session.run("""
                MERGE (m:Memory {id: $id})
                SET m.type = $type,
                    m.content_preview = $preview,
                    m.created_at = datetime($created_at)
            """, {
                "id": memory_id,
                "type": memory_type,
                "preview": content_preview[:200] if content_preview else "",
                "created_at": timestamp.isoformat()
            })

            # Link to project if specified
            if project:
                session.run("""
                    MERGE (p:Project {name: $project})
                    WITH p
                    MATCH (m:Memory {id: $id})
                    MERGE (m)-[:BELONGS_TO]->(p)
                """, {"id": memory_id, "project": project})

            # Link to tags
            if tags:
                for tag in tags:
                    session.run("""
                        MERGE (t:Tag {name: $tag})
                        WITH t
                        MATCH (m:Memory {id: $id})
                        MERGE (m)-[:TAGGED_WITH]->(t)
                    """, {"id": memory_id, "tag": tag})

            return True

        except Exception as e:
            logger.error(f"Failed to create memory node: {e}")
            return False


def create_relationship(
    source_id: str,
    target_id: str,
    relation_type: str,
    properties: Optional[dict] = None,
    valid_from: Optional[datetime] = None,
    valid_to: Optional[datetime] = None
) -> bool:
    """Create a relationship between two memories with optional temporal validity.

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        relation_type: Type of relationship (FIXES, CAUSES, RELATES_TO, etc.)
        properties: Optional relationship properties
        valid_from: When this relationship became true (default: now)
        valid_to: When this relationship became obsolete (default: None = indefinite)

    Returns:
        True if created successfully
    """
    if not is_graph_enabled():
        return False

    with get_session() as session:
        if session is None:
            return False

        try:
            props = properties or {}
            props["created_at"] = datetime.now(timezone.utc).isoformat()

            # Phase 2.2: Add temporal validity window
            props["valid_from"] = (valid_from or datetime.now(timezone.utc)).isoformat()
            if valid_to:
                props["valid_to"] = valid_to.isoformat()

            # Create relationship with dynamic type
            query = f"""
                MATCH (source:Memory {{id: $source_id}})
                MATCH (target:Memory {{id: $target_id}})
                MERGE (source)-[r:{relation_type}]->(target)
                SET r += $props
                RETURN r
            """

            result = session.run(query, {
                "source_id": source_id,
                "target_id": target_id,
                "props": props
            })

            return result.single() is not None

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False


def get_related_memories(
    memory_id: str,
    max_hops: int = 2,
    limit: int = 20
) -> list[dict]:
    """Get memories related to a given memory via graph traversal.

    Args:
        memory_id: Starting memory ID
        max_hops: Maximum relationship hops (1-3)
        limit: Maximum results

    Returns:
        List of related memories with relationship info
    """
    if not is_graph_enabled():
        return []

    with get_session() as session:
        if session is None:
            return []

        try:
            # Traverse up to max_hops relationships
            # Note: Cypher doesn't support parameters in variable-length patterns
            hops = min(max_hops, 3)
            query = f"""
                MATCH path = (start:Memory {{id: $id}})-[*1..{hops}]-(related:Memory)
                WHERE start <> related
                WITH related,
                     length(path) as distance,
                     [r in relationships(path) | type(r)] as rel_types
                RETURN DISTINCT related.id as id,
                       related.type as type,
                       related.content_preview as preview,
                       distance,
                       rel_types
                ORDER BY distance
                LIMIT $limit
            """
            result = session.run(query, {
                "id": memory_id,
                "limit": limit
            })

            related = []
            for record in result:
                related.append({
                    "id": record["id"],
                    "type": record["type"],
                    "preview": record["preview"],
                    "distance": record["distance"],
                    "relationship_path": record["rel_types"]
                })

            return related

        except Exception as e:
            logger.error(f"Failed to get related memories: {e}")
            return []


def get_related_memories_at_time(
    memory_id: str,
    target_time: datetime,
    max_hops: int = 2,
    limit: int = 20
) -> list[dict]:
    """Get memories related to a given memory at a specific point in time.

    This implements temporal graph traversal (Phase 2.2): only follows relationships
    that were valid at the target_time.

    A relationship is valid at time T if:
    - valid_from <= T
    - valid_to is NULL OR valid_to > T

    Args:
        memory_id: Starting memory ID
        target_time: Time to query relationships
        max_hops: Maximum relationship hops (1-3)
        limit: Maximum results

    Returns:
        List of related memories with relationship info
    """
    if not is_graph_enabled():
        return []

    with get_session() as session:
        if session is None:
            return []

        try:
            # Traverse up to max_hops relationships, filtering by temporal validity
            hops = min(max_hops, 3)
            target_time_str = target_time.isoformat()

            query = f"""
                MATCH path = (start:Memory {{id: $id}})-[*1..{hops}]-(related:Memory)
                WHERE start <> related
                  AND ALL(r in relationships(path) WHERE
                    datetime(r.valid_from) <= datetime($target_time)
                    AND (r.valid_to IS NULL OR datetime(r.valid_to) > datetime($target_time))
                  )
                WITH related,
                     length(path) as distance,
                     [r in relationships(path) | type(r)] as rel_types
                RETURN DISTINCT related.id as id,
                       related.type as type,
                       related.content_preview as preview,
                       distance,
                       rel_types
                ORDER BY distance
                LIMIT $limit
            """
            result = session.run(query, {
                "id": memory_id,
                "target_time": target_time_str,
                "limit": limit
            })

            related = []
            for record in result:
                related.append({
                    "id": record["id"],
                    "type": record["type"],
                    "preview": record["preview"],
                    "distance": record["distance"],
                    "relationship_path": record["rel_types"]
                })

            return related

        except Exception as e:
            logger.error(f"Failed to get temporally-filtered related memories: {e}")
            return []


def mark_relationship_obsolete(
    source_id: str,
    target_id: str,
    relation_type: str,
    valid_to: Optional[datetime] = None
) -> bool:
    """Mark a relationship as obsolete by setting valid_to.

    Args:
        source_id: Source memory ID
        target_id: Target memory ID
        relation_type: Type of relationship
        valid_to: When relationship became obsolete (default: now)

    Returns:
        True if successful
    """
    if not is_graph_enabled():
        return False

    with get_session() as session:
        if session is None:
            return False

        try:
            end_time = valid_to or datetime.now(timezone.utc)

            query = f"""
                MATCH (source:Memory {{id: $source_id}})-[r:{relation_type}]->(target:Memory {{id: $target_id}})
                SET r.valid_to = datetime($valid_to)
                RETURN r
            """

            result = session.run(query, {
                "source_id": source_id,
                "target_id": target_id,
                "valid_to": end_time.isoformat()
            })

            success = result.single() is not None
            if success:
                logger.info(f"Marked relationship {source_id}-[{relation_type}]->{target_id} as obsolete")
            return success

        except Exception as e:
            logger.error(f"Failed to mark relationship obsolete: {e}")
            return False


def _neo4j_datetime_to_iso(dt) -> Optional[str]:
    """Convert Neo4j DateTime to ISO string."""
    if dt is None:
        return None
    # Neo4j DateTime has .isoformat() method
    try:
        return dt.isoformat()
    except AttributeError:
        # If already a string or other type, return as is
        return str(dt)


def get_memory_timeline(
    project: Optional[str] = None,
    memory_type: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """Get memories ordered by time with their relationships.

    Args:
        project: Filter by project
        memory_type: Filter by type
        limit: Maximum results

    Returns:
        List of memories with temporal context
    """
    if not is_graph_enabled():
        return []

    with get_session() as session:
        if session is None:
            return []

        try:
            # Build dynamic query based on filters
            where_clauses = []
            params = {"limit": limit}

            if project:
                where_clauses.append("(m)-[:BELONGS_TO]->(:Project {name: $project})")
                params["project"] = project

            if memory_type:
                where_clauses.append("m.type = $type")
                params["type"] = memory_type

            where_str = " AND ".join(where_clauses) if where_clauses else "TRUE"

            result = session.run(f"""
                MATCH (m:Memory)
                WHERE {where_str}
                OPTIONAL MATCH (m)-[r]->(related:Memory)
                WITH m, collect({{
                    type: type(r),
                    target_id: related.id,
                    target_type: related.type
                }}) as outgoing
                RETURN m.id as id,
                       m.type as type,
                       m.content_preview as preview,
                       m.created_at as created_at,
                       outgoing
                ORDER BY m.created_at DESC
                LIMIT $limit
            """, params)

            timeline = []
            for record in result:
                timeline.append({
                    "id": record["id"],
                    "type": record["type"],
                    "preview": record["preview"],
                    "created_at": _neo4j_datetime_to_iso(record["created_at"]),
                    "relationships": [r for r in record["outgoing"] if r["target_id"]]
                })

            return timeline

        except Exception as e:
            logger.error(f"Failed to get memory timeline: {e}")
            return []


def find_error_solutions(error_id: str) -> list[dict]:
    """Find solutions that fixed a specific error.

    Args:
        error_id: Error memory ID

    Returns:
        List of solution memories
    """
    if not is_graph_enabled():
        return []

    with get_session() as session:
        if session is None:
            return []

        try:
            result = session.run("""
                MATCH (error:Memory {id: $id, type: 'error'})
                      -[:FIXED_BY]->(solution:Memory)
                RETURN solution.id as id,
                       solution.type as type,
                       solution.content_preview as preview,
                       solution.created_at as created_at
                ORDER BY solution.created_at DESC
            """, {"id": error_id})

            solutions = []
            for record in result:
                solutions.append({
                    "id": record["id"],
                    "type": record["type"],
                    "preview": record["preview"],
                    "created_at": record["created_at"]
                })

            return solutions

        except Exception as e:
            logger.error(f"Failed to find error solutions: {e}")
            return []


def get_project_knowledge_graph(project: str) -> dict:
    """Get the knowledge graph for a project.

    Args:
        project: Project name

    Returns:
        Graph data with nodes and edges
    """
    if not is_graph_enabled():
        return {"nodes": [], "edges": []}

    with get_session() as session:
        if session is None:
            return {"nodes": [], "edges": []}

        try:
            # Get all memories and their relationships for the project
            result = session.run("""
                MATCH (p:Project {name: $project})<-[:BELONGS_TO]-(m:Memory)
                OPTIONAL MATCH (m)-[r]->(target:Memory)
                WHERE (target)-[:BELONGS_TO]->(p)
                RETURN m.id as source_id,
                       m.type as source_type,
                       m.content_preview as source_preview,
                       type(r) as rel_type,
                       target.id as target_id,
                       target.type as target_type
            """, {"project": project})

            nodes = {}
            edges = []

            for record in result:
                # Add source node
                if record["source_id"] not in nodes:
                    nodes[record["source_id"]] = {
                        "id": record["source_id"],
                        "type": record["source_type"],
                        "preview": record["source_preview"]
                    }

                # Add edge if relationship exists
                if record["rel_type"] and record["target_id"]:
                    edges.append({
                        "source": record["source_id"],
                        "target": record["target_id"],
                        "type": record["rel_type"]
                    })

                    # Add target node
                    if record["target_id"] not in nodes:
                        nodes[record["target_id"]] = {
                            "id": record["target_id"],
                            "type": record["target_type"],
                            "preview": None
                        }

            return {
                "nodes": list(nodes.values()),
                "edges": edges
            }

        except Exception as e:
            logger.error(f"Failed to get project knowledge graph: {e}")
            return {"nodes": [], "edges": []}


def delete_memory_node(memory_id: str) -> bool:
    """Delete a memory node and its relationships.

    Args:
        memory_id: Memory ID to delete

    Returns:
        True if deleted
    """
    if not is_graph_enabled():
        return False

    with get_session() as session:
        if session is None:
            return False

        try:
            session.run("""
                MATCH (m:Memory {id: $id})
                DETACH DELETE m
            """, {"id": memory_id})

            return True

        except Exception as e:
            logger.error(f"Failed to delete memory node: {e}")
            return False


def get_graph_stats() -> dict:
    """Get graph database statistics."""
    if not is_graph_enabled():
        return {"enabled": False}

    with get_session() as session:
        if session is None:
            return {"enabled": False}

        try:
            # Count nodes and relationships
            result = session.run("""
                MATCH (m:Memory)
                WITH count(m) as memory_count
                MATCH (p:Project)
                WITH memory_count, count(p) as project_count
                MATCH (t:Tag)
                WITH memory_count, project_count, count(t) as tag_count
                MATCH ()-[r]->()
                RETURN memory_count,
                       project_count,
                       tag_count,
                       count(r) as relationship_count
            """)

            record = result.single()

            return {
                "enabled": True,
                "memory_nodes": record["memory_count"] if record else 0,
                "project_nodes": record["project_count"] if record else 0,
                "tag_nodes": record["tag_count"] if record else 0,
                "relationships": record["relationship_count"] if record else 0
            }

        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {"enabled": True, "error": str(e)}


def reset_graph() -> dict:
    """Delete all nodes and relationships from the graph database.

    Returns:
        dict with counts of deleted nodes and relationships
    """
    if not is_graph_enabled():
        return {"enabled": False, "deleted_nodes": 0, "deleted_relationships": 0}

    with get_session() as session:
        if session is None:
            return {"enabled": False, "deleted_nodes": 0, "deleted_relationships": 0}

        try:
            # Get counts before deletion
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH ()-[r]->()
                RETURN count(DISTINCT n) as node_count, count(DISTINCT r) as rel_count
            """)
            record = result.single()
            node_count = record["node_count"] if record else 0
            rel_count = record["rel_count"] if record else 0

            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")

            logger.info(f"Graph reset: deleted {node_count} nodes and {rel_count} relationships")

            return {
                "enabled": True,
                "deleted_nodes": node_count,
                "deleted_relationships": rel_count
            }

        except Exception as e:
            logger.error(f"Failed to reset graph: {e}")
            return {"enabled": True, "error": str(e)}


def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver and _driver != "disabled":
        _driver.close()
        _driver = None
