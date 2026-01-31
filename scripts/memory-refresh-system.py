#!/usr/bin/env python3
"""
Memory Refresh System
Identifies stale or potentially outdated memories and suggests refreshes
Helps keep knowledge base current and relevant
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys

MEMORY_API = "http://localhost:8100"

def get_old_memories(days: int = 30) -> List[Dict]:
    """Get memories older than N days."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        data = response.json()

        cutoff = datetime.now() - timedelta(days=days)
        old_memories = []

        for mem in data.get("memories", []):
            created_at = datetime.fromisoformat(mem.get("created_at", ""))
            if created_at < cutoff:
                old_memories.append(mem)

        return old_memories
    except Exception as e:
        print(f"❌ Error fetching memories: {e}")
        return []

def calculate_staleness_score(memory: Dict) -> float:
    """
    Calculate staleness score (0-100).
    Higher score = more stale = needs refresh.

    Factors:
    - Age (older = more stale)
    - Access count (fewer accesses = more stale)
    - Type (docs = more likely to become outdated)
    - Usefulness score (lower = more likely outdated)
    """
    score = 0.0

    # Age factor (0-40 points)
    try:
        created_at = datetime.fromisoformat(memory.get("created_at", ""))
        age_days = (datetime.now() - created_at).days
        age_score = min(40, age_days / 10)  # Max 40 points after ~400 days
        score += age_score
    except:
        score += 20  # Default if date parsing fails

    # Access count factor (0-30 points)
    access_count = memory.get("access_count", 0)
    if access_count == 0:
        score += 30  # Never accessed = very stale
    elif access_count < 3:
        score += 20  # Rarely accessed
    elif access_count < 10:
        score += 10  # Moderately accessed
    # Frequently accessed = 0 points

    # Type factor (0-20 points)
    mem_type = memory.get("type", "")
    if mem_type == "docs":
        score += 20  # Documentation often becomes outdated
    elif mem_type == "error":
        score += 10  # Error solutions may become outdated
    elif mem_type == "decision":
        score += 5   # Decisions may be revisited
    # Patterns and learnings are more timeless

    # Usefulness factor (0-10 points)
    usefulness = memory.get("usefulness_score", 0.5)
    if usefulness < 0.3:
        score += 10  # Low usefulness suggests outdated
    elif usefulness < 0.5:
        score += 5

    return min(100, score)

def generate_refresh_suggestion(memory: Dict) -> str:
    """Generate a suggestion for refreshing this memory."""
    mem_type = memory.get("type", "unknown")
    content = memory.get("content", "")[:100]

    suggestions = {
        "docs": f"Check if documentation has been updated. Original: {content}...",
        "error": f"Verify if this error still occurs with current versions. Original: {content}...",
        "decision": f"Review if this decision still applies. Original: {content}...",
        "pattern": f"Check if this pattern is still recommended. Original: {content}...",
        "learning": f"Validate this learning with current codebase. Original: {content}..."
    }

    return suggestions.get(mem_type, f"Review and update if needed: {content}...")

def check_for_duplicates(memory: Dict) -> List[Dict]:
    """Check if this memory has been superseded by newer similar memories."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": memory.get("content", ""),
            "limit": 5
        })
        response.raise_for_status()
        results = response.json().get("results", [])

        # Filter to newer memories with high similarity
        memory_created = datetime.fromisoformat(memory.get("created_at", ""))
        duplicates = []

        for result in results:
            if result.get("id") == memory.get("id"):
                continue

            result_created = datetime.fromisoformat(result.get("created_at", ""))
            if result_created > memory_created and result.get("score", 0) > 0.85:
                duplicates.append(result)

        return duplicates
    except Exception as e:
        return []

def generate_refresh_report(memories: List[Dict], staleness_threshold: float = 60.0) -> Dict:
    """Generate a report of memories that need refresh."""
    report = {
        "total_analyzed": len(memories),
        "needs_refresh": [],
        "possibly_duplicate": [],
        "high_priority": [],
        "timestamp": datetime.now().isoformat()
    }

    for mem in memories:
        staleness = calculate_staleness_score(mem)

        if staleness >= staleness_threshold:
            entry = {
                "id": mem.get("id"),
                "type": mem.get("type"),
                "content": mem.get("content", "")[:100],
                "staleness_score": staleness,
                "age_days": (datetime.now() - datetime.fromisoformat(mem.get("created_at", ""))).days,
                "access_count": mem.get("access_count", 0),
                "usefulness": mem.get("usefulness_score", 0),
                "suggestion": generate_refresh_suggestion(mem)
            }

            report["needs_refresh"].append(entry)

            # Check for high priority (very stale or never accessed docs)
            if staleness > 80 or (mem.get("type") == "docs" and mem.get("access_count", 0) == 0):
                report["high_priority"].append(entry)

            # Check for possible duplicates
            duplicates = check_for_duplicates(mem)
            if duplicates:
                report["possibly_duplicate"].append({
                    **entry,
                    "newer_memories": [d.get("id") for d in duplicates]
                })

    return report

def main():
    """Main refresh check workflow."""
    print("🔄 Memory Refresh System")
    print("═" * 60)

    # Check if memory service is running
    try:
        response = requests.get(f"{MEMORY_API}/health")
        response.raise_for_status()
        print("✅ Memory service is running")
    except Exception as e:
        print(f"❌ Memory service not available: {e}")
        sys.exit(1)

    # Get configuration from arguments
    days_old = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    staleness_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0

    print(f"\n📊 Analyzing memories older than {days_old} days...")
    print(f"   Staleness threshold: {staleness_threshold}")

    # Fetch old memories
    old_memories = get_old_memories(days_old)
    print(f"   Found {len(old_memories)} old memories")

    if not old_memories:
        print("   No old memories found")
        return

    # Generate refresh report
    print(f"\n🔍 Calculating staleness scores...")
    report = generate_refresh_report(old_memories, staleness_threshold)

    # Display results
    print("\n" + "═" * 60)
    print(f"📊 Refresh Report:")
    print(f"   Total analyzed: {report['total_analyzed']}")
    print(f"   Needs refresh: {len(report['needs_refresh'])}")
    print(f"   High priority: {len(report['high_priority'])}")
    print(f"   Possibly duplicate: {len(report['possibly_duplicate'])}")
    print("═" * 60)

    # Show high priority items
    if report['high_priority']:
        print(f"\n🚨 High Priority Refresh Needed ({len(report['high_priority'])} items):")
        for i, item in enumerate(report['high_priority'][:10], 1):  # Show top 10
            print(f"\n   {i}. [{item['type']}] ID: {item['id'][:8]}")
            print(f"      Staleness: {item['staleness_score']:.1f}/100")
            print(f"      Age: {item['age_days']} days")
            print(f"      Accesses: {item['access_count']}")
            print(f"      Content: {item['content']}...")
            print(f"      → {item['suggestion']}")

    # Show possible duplicates
    if report['possibly_duplicate']:
        print(f"\n🔄 Possibly Superseded ({len(report['possibly_duplicate'])} items):")
        for i, item in enumerate(report['possibly_duplicate'][:5], 1):  # Show top 5
            print(f"\n   {i}. [{item['type']}] ID: {item['id'][:8]}")
            print(f"      Content: {item['content']}...")
            print(f"      Newer similar: {', '.join(m[:8] for m in item['newer_memories'])}")
            print(f"      → Consider archiving or consolidating")

    # Save report to file
    report_file = f"/tmp/claude/memory-refresh-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Full report saved to: {report_file}")
    print("═" * 60)

if __name__ == "__main__":
    main()
