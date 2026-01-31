#!/usr/bin/env python3
"""
Automatic Memory Linking System
Analyzes new memories and creates relationships with existing memories
Runs periodically or on-demand to build the knowledge graph
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys

MEMORY_API = "http://localhost:8100"

def get_recent_memories(hours: int = 1) -> List[Dict]:
    """Get memories created in the last N hours."""
    try:
        # Get all memories sorted by timestamp
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 100
        })
        response.raise_for_status()
        data = response.json()

        # Filter to recent memories
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []

        for mem in data.get("memories", []):
            created_at = datetime.fromisoformat(mem.get("created_at", ""))
            if created_at >= cutoff:
                recent.append(mem)

        return recent
    except Exception as e:
        print(f"❌ Error fetching recent memories: {e}")
        return []

def search_similar_memories(content: str, memory_id: str, limit: int = 5) -> List[Dict]:
    """Search for memories similar to the given content."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": content,
            "limit": limit + 1  # +1 to account for self-match
        })
        response.raise_for_status()
        results = response.json().get("results", [])

        # Filter out the memory itself
        return [r for r in results if r.get("id") != memory_id][:limit]
    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        return []

def determine_relationship_type(mem1: Dict, mem2: Dict) -> Optional[str]:
    """
    Determine the relationship type between two memories.

    Returns one of: causes, fixes, contradicts, supports, follows, related, supersedes
    """
    type1 = mem1.get("type")
    type2 = mem2.get("type")

    # Error -> Learning: The learning fixes the error
    if type1 == "error" and type2 == "learning":
        if mem1.get("error_message", "").lower() in mem2.get("content", "").lower():
            return "fixes"

    # Learning -> Error: The error was fixed by this learning
    if type1 == "learning" and type2 == "error":
        if mem2.get("error_message", "").lower() in mem1.get("content", "").lower():
            return "fixes"

    # Decision -> Pattern: Decision enables or supports pattern
    if type1 == "decision" and type2 == "pattern":
        return "supports"

    # Pattern -> Decision: Pattern influenced decision
    if type1 == "pattern" and type2 == "decision":
        return "supports"

    # Same project and same tags: Related
    if mem1.get("project") == mem2.get("project") and mem1.get("project"):
        tags1 = set(mem1.get("tags", []))
        tags2 = set(mem2.get("tags", []))
        if len(tags1 & tags2) >= 2:  # At least 2 common tags
            return "related"

    # Sequential learnings in same session: Follows
    if type1 == "learning" and type2 == "learning":
        # Check if created close together (within 5 minutes)
        try:
            time1 = datetime.fromisoformat(mem1.get("created_at", ""))
            time2 = datetime.fromisoformat(mem2.get("created_at", ""))
            if abs((time1 - time2).total_seconds()) < 300:  # 5 minutes
                return "follows"
        except:
            pass

    # Newer memory with similar content: Supersedes
    if type1 == type2:
        try:
            time1 = datetime.fromisoformat(mem1.get("created_at", ""))
            time2 = datetime.fromisoformat(mem2.get("created_at", ""))
            if time1 > time2 and abs((time1 - time2).total_seconds()) > 86400:  # >1 day apart
                return "supersedes"
        except:
            pass

    # Default: General relationship
    return "related"

def create_memory_link(source_id: str, target_id: str, relation: str) -> bool:
    """Create a relationship between two memories."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/link", json={
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation
        })
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error creating link: {e}")
        return False

def auto_link_memory(memory: Dict, similarity_threshold: float = 0.7) -> List[Dict]:
    """
    Automatically find and create links for a single memory.

    Returns list of created links.
    """
    memory_id = memory.get("id")
    content = memory.get("content", "")

    if not memory_id or not content:
        return []

    # Search for similar memories
    similar = search_similar_memories(content, memory_id)

    links_created = []

    for sim_mem in similar:
        # Check similarity score (if available)
        score = sim_mem.get("score", 0)
        if score < similarity_threshold:
            continue

        # Determine relationship type
        relation = determine_relationship_type(memory, sim_mem)

        if not relation:
            continue

        # Create the link
        target_id = sim_mem.get("id")
        if create_memory_link(memory_id, target_id, relation):
            links_created.append({
                "source": memory_id,
                "target": target_id,
                "relation": relation,
                "score": score
            })
            print(f"✅ Linked {memory_id[:8]} → {target_id[:8]} ({relation})")

    return links_created

def main():
    """Main auto-linking workflow."""
    print("🔗 Automatic Memory Linking System")
    print("═" * 60)

    # Check if memory service is running
    try:
        response = requests.get(f"{MEMORY_API}/health")
        response.raise_for_status()
        print("✅ Memory service is running")
    except Exception as e:
        print(f"❌ Memory service not available: {e}")
        sys.exit(1)

    # Get recent memories (last 24 hours by default)
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    print(f"\n📊 Fetching memories from last {hours} hours...")

    recent_memories = get_recent_memories(hours)
    print(f"   Found {len(recent_memories)} recent memories")

    if not recent_memories:
        print("   No recent memories to link")
        return

    # Auto-link each recent memory
    print(f"\n🔗 Auto-linking memories...")
    total_links = 0

    for memory in recent_memories:
        mem_id = memory.get("id", "unknown")[:8]
        mem_type = memory.get("type", "unknown")
        mem_content = memory.get("content", "")[:50]

        print(f"\n   Processing: {mem_id} ({mem_type})")
        print(f"   Content: {mem_content}...")

        links = auto_link_memory(memory)
        total_links += len(links)

        if links:
            print(f"   ✅ Created {len(links)} links")
        else:
            print(f"   ⏭️  No links created")

    # Summary
    print("\n" + "═" * 60)
    print(f"📊 Summary:")
    print(f"   Processed: {len(recent_memories)} memories")
    print(f"   Links created: {total_links}")
    print(f"   Avg links per memory: {total_links / len(recent_memories):.2f}")
    print("═" * 60)

    # Get updated graph stats
    try:
        response = requests.get(f"{MEMORY_API}/graph/stats")
        response.raise_for_status()
        stats = response.json()
        print(f"\n📈 Knowledge Graph Stats:")
        print(f"   Total nodes: {stats.get('total_nodes', 0)}")
        print(f"   Total relationships: {stats.get('total_relationships', 0)}")
        print(f"   Projects: {stats.get('project_count', 0)}")
    except:
        pass

if __name__ == "__main__":
    main()
