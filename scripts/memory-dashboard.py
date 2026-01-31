#!/usr/bin/env python3
"""
Memory Usage Dashboard
Real-time dashboard showing memory system health and usage metrics
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List
import sys

MEMORY_API = "http://localhost:8100"

def get_memory_stats() -> Dict:
    """Fetch overall memory statistics."""
    try:
        response = requests.get(f"{MEMORY_API}/stats")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_graph_stats() -> Dict:
    """Fetch knowledge graph statistics."""
    try:
        response = requests.get(f"{MEMORY_API}/graph/stats")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_recent_activity(hours: int = 24) -> Dict:
    """Get recent memory activity."""
    try:
        # Get timeline
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 100
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [m for m in memories if datetime.fromisoformat(m.get("created_at", "")) >= cutoff]

        # Group by type
        by_type = {}
        for mem in recent:
            mem_type = mem.get("type", "unknown")
            by_type[mem_type] = by_type.get(mem_type, 0) + 1

        return {
            "total": len(recent),
            "by_type": by_type,
            "hourly_rate": len(recent) / hours
        }
    except Exception as e:
        return {"error": str(e)}

def get_quality_metrics() -> Dict:
    """Calculate quality metrics for memories."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        if not memories:
            return {"error": "No memories found"}

        # Calculate metrics
        total = len(memories)
        with_projects = sum(1 for m in memories if m.get("project"))
        avg_tags = sum(len(m.get("tags", [])) for m in memories) / total
        avg_content_length = sum(len(m.get("content", "")) for m in memories) / total

        # Quality tiers
        high_quality = sum(1 for m in memories if len(m.get("content", "")) > 100 and len(m.get("tags", [])) >= 3)
        medium_quality = sum(1 for m in memories if 30 <= len(m.get("content", "")) <= 100)
        low_quality = sum(1 for m in memories if len(m.get("content", "")) < 30)

        return {
            "total_memories": total,
            "with_project": with_projects,
            "project_rate": (with_projects / total) * 100,
            "avg_tags": avg_tags,
            "avg_content_length": avg_content_length,
            "high_quality": high_quality,
            "high_quality_rate": (high_quality / total) * 100,
            "medium_quality": medium_quality,
            "medium_quality_rate": (medium_quality / total) * 100,
            "low_quality": low_quality,
            "low_quality_rate": (low_quality / total) * 100
        }
    except Exception as e:
        return {"error": str(e)}

def get_top_tags(limit: int = 10) -> List[Dict]:
    """Get most used tags."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        # Count tags
        tag_counts = {}
        for mem in memories:
            for tag in mem.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort and return top N
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": tag, "count": count} for tag, count in sorted_tags[:limit]]
    except Exception as e:
        return []

def get_project_breakdown() -> List[Dict]:
    """Get memory count by project."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        # Count by project
        project_counts = {}
        for mem in memories:
            project = mem.get("project", "_none")
            project_counts[project] = project_counts.get(project, 0) + 1

        # Sort and format
        sorted_projects = sorted(project_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"project": proj, "count": count} for proj, count in sorted_projects]
    except Exception as e:
        return []

def format_bar_chart(value: float, max_value: float, width: int = 30) -> str:
    """Create a simple ASCII bar chart."""
    filled = int((value / max_value) * width) if max_value > 0 else 0
    return "█" * filled + "░" * (width - filled)

def print_dashboard():
    """Print the complete dashboard."""
    print("\n" * 2)  # Add spacing instead of clearing screen
    print("╔════════════════════════════════════════════════════════════╗")
    print("║          🧠 MEMORY SYSTEM DASHBOARD 🧠                     ║")
    print("║          " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                                ║")
    print("╚════════════════════════════════════════════════════════════╝")

    # Check service health
    try:
        response = requests.get(f"{MEMORY_API}/health", timeout=2)
        response.raise_for_status()
        print("\n✅ Service Status: RUNNING")
    except Exception as e:
        print(f"\n❌ Service Status: DOWN ({e})")
        print("\n💡 Start service: cd ~/.claude/memory && docker compose up -d")
        return

    # Overall Stats
    print("\n" + "─" * 60)
    print("📊 OVERALL STATISTICS")
    print("─" * 60)

    stats = get_memory_stats()
    if "error" not in stats:
        total = stats.get("total_memories", 0)
        by_type = stats.get("by_type", {})

        print(f"Total Memories: {total}")
        print(f"Memory Types:")
        for mem_type, count in by_type.items():
            percentage = (count / total * 100) if total > 0 else 0
            bar = format_bar_chart(count, total, 20)
            print(f"  {mem_type:12} {count:4} {bar} {percentage:5.1f}%")

    # Knowledge Graph Stats
    print("\n" + "─" * 60)
    print("🕸️  KNOWLEDGE GRAPH")
    print("─" * 60)

    graph_stats = get_graph_stats()
    if "error" not in graph_stats:
        nodes = graph_stats.get("total_nodes", 0)
        rels = graph_stats.get("total_relationships", 0)
        projects = graph_stats.get("project_count", 0)

        print(f"Nodes: {nodes}")
        print(f"Relationships: {rels}")
        print(f"Projects: {projects}")
        print(f"Avg Connections/Node: {(rels / nodes):.2f}" if nodes > 0 else "Avg Connections/Node: 0")

    # Recent Activity (24h)
    print("\n" + "─" * 60)
    print("📈 RECENT ACTIVITY (24 hours)")
    print("─" * 60)

    activity = get_recent_activity(24)
    if "error" not in activity:
        total_recent = activity.get("total", 0)
        hourly_rate = activity.get("hourly_rate", 0)
        by_type = activity.get("by_type", {})

        print(f"New Memories: {total_recent}")
        print(f"Hourly Rate: {hourly_rate:.2f} memories/hour")
        if by_type:
            print(f"Breakdown:")
            for mem_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"  {mem_type:12} {count:4}")

    # Quality Metrics
    print("\n" + "─" * 60)
    print("⭐ QUALITY METRICS")
    print("─" * 60)

    quality = get_quality_metrics()
    if "error" not in quality:
        print(f"Avg Tags/Memory: {quality.get('avg_tags', 0):.2f}")
        print(f"Avg Content Length: {quality.get('avg_content_length', 0):.0f} chars")
        print(f"With Project: {quality.get('project_rate', 0):.1f}%")
        print(f"\nQuality Distribution:")
        print(f"  High (>100 chars, 3+ tags): {quality.get('high_quality', 0)} ({quality.get('high_quality_rate', 0):.1f}%)")
        print(f"  Medium (30-100 chars):       {quality.get('medium_quality', 0)} ({quality.get('medium_quality_rate', 0):.1f}%)")
        print(f"  Low (<30 chars):             {quality.get('low_quality', 0)} ({quality.get('low_quality_rate', 0):.1f}%)")

    # Top Tags
    print("\n" + "─" * 60)
    print("🏷️  TOP TAGS")
    print("─" * 60)

    top_tags = get_top_tags(10)
    if top_tags:
        max_count = max(t["count"] for t in top_tags)
        for tag_info in top_tags:
            tag = tag_info["tag"]
            count = tag_info["count"]
            bar = format_bar_chart(count, max_count, 20)
            print(f"  {tag:20} {count:4} {bar}")

    # Project Breakdown
    print("\n" + "─" * 60)
    print("📁 PROJECTS")
    print("─" * 60)

    projects = get_project_breakdown()
    if projects:
        max_count = max(p["count"] for p in projects)
        for proj_info in projects[:10]:  # Top 10 projects
            project = proj_info["project"]
            count = proj_info["count"]
            bar = format_bar_chart(count, max_count, 20)
            print(f"  {project:20} {count:4} {bar}")

    # Footer
    print("\n" + "═" * 60)
    print("💡 Refresh: Run this script again")
    print("📖 Full stats: curl http://localhost:8100/stats")
    print("═" * 60)

def main():
    """Main dashboard display."""
    try:
        print_dashboard()
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard closed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
