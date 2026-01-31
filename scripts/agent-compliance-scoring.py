#!/usr/bin/env python3
"""
Agent Compliance Scoring
Analyzes agent memory usage and assigns compliance scores
Helps identify which agents are following memory protocol
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List
import sys
from collections import defaultdict

MEMORY_API = "http://localhost:8100"
AUDIT_LOG = f"/Users/{sys.argv[0].split('/')[2]}/.claude/audit.log" if len(sys.argv[0].split('/')) > 2 else None

def parse_audit_log(hours: int = 24) -> Dict:
    """Parse audit log to extract memory tool usage by context."""
    if not AUDIT_LOG:
        return {}

    try:
        with open(AUDIT_LOG, "r") as f:
            lines = f.readlines()

        # Look for recent entries (last N hours)
        cutoff = datetime.now() - timedelta(hours=hours)

        usage_data = defaultdict(lambda: {
            "search_memory": 0,
            "get_context": 0,
            "store_memory": 0,
            "total_operations": 0,
            "sessions": set()
        })

        for line in lines:
            try:
                # Parse timestamp
                if "[" in line:
                    timestamp_str = line.split("[")[1].split("]")[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp < cutoff:
                        continue

                    # Extract tool usage
                    if "search_memory" in line:
                        usage_data["_all"]["search_memory"] += 1
                        usage_data["_all"]["total_operations"] += 1

                    elif "get_context" in line:
                        usage_data["_all"]["get_context"] += 1
                        usage_data["_all"]["total_operations"] += 1

                    elif "store_memory" in line:
                        usage_data["_all"]["store_memory"] += 1
                        usage_data["_all"]["total_operations"] += 1
            except:
                continue

        # Convert sets to counts
        for key in usage_data:
            usage_data[key]["sessions"] = len(usage_data[key]["sessions"])

        return dict(usage_data)
    except Exception as e:
        print(f"⚠️  Could not parse audit log: {e}")
        return {}

def get_memory_activity(hours: int = 24) -> Dict:
    """Get memory activity from API."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 200
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [m for m in memories if datetime.fromisoformat(m.get("created_at", "")) >= cutoff]

        # Group by project (proxy for agent context)
        by_project = defaultdict(int)
        by_type = defaultdict(int)

        for mem in recent:
            project = mem.get("project", "_none")
            mem_type = mem.get("type", "unknown")

            by_project[project] += 1
            by_type[mem_type] += 1

        return {
            "total_stored": len(recent),
            "by_project": dict(by_project),
            "by_type": dict(by_type)
        }
    except Exception as e:
        return {"error": str(e)}

def calculate_compliance_score(usage_stats: Dict) -> Dict:
    """
    Calculate compliance score (0-100) based on memory usage patterns.

    Scoring criteria:
    - Session start: search_memory or get_context called (40 points)
    - Solution storage: store_memory called after work (40 points)
    - Frequency: Regular usage throughout session (20 points)
    """
    score = 0.0
    breakdown = {}

    # Check if search/get_context was called (40 points)
    searches = usage_stats.get("search_memory", 0) + usage_stats.get("get_context", 0)
    if searches > 0:
        search_score = min(40, searches * 20)  # Max 40 points, 20 per search
        score += search_score
        breakdown["search_score"] = search_score
    else:
        breakdown["search_score"] = 0

    # Check if store_memory was called (40 points)
    stores = usage_stats.get("store_memory", 0)
    if stores > 0:
        store_score = min(40, stores * 20)  # Max 40 points, 20 per store
        score += store_score
        breakdown["store_score"] = store_score
    else:
        breakdown["store_score"] = 0

    # Check usage frequency (20 points)
    total_ops = usage_stats.get("total_operations", 0)
    if total_ops >= 5:
        frequency_score = 20  # High frequency
    elif total_ops >= 3:
        frequency_score = 15  # Medium frequency
    elif total_ops >= 1:
        frequency_score = 10  # Low frequency
    else:
        frequency_score = 0   # No usage

    score += frequency_score
    breakdown["frequency_score"] = frequency_score

    # Cap at 100
    score = min(100, score)

    return {
        "total_score": score,
        "breakdown": breakdown,
        "searches": searches,
        "stores": stores,
        "total_operations": total_ops,
        "grade": get_grade(score)
    }

def get_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+ (Excellent)"
    elif score >= 80:
        return "A (Very Good)"
    elif score >= 70:
        return "B (Good)"
    elif score >= 60:
        return "C (Fair)"
    elif score >= 50:
        return "D (Poor)"
    else:
        return "F (Failing)"

def generate_compliance_report(hours: int = 24) -> Dict:
    """Generate full compliance report."""
    print(f"📊 Analyzing memory usage over last {hours} hours...\n")

    # Get usage data
    audit_data = parse_audit_log(hours)
    activity_data = get_memory_activity(hours)

    # Calculate overall compliance
    overall_usage = audit_data.get("_all", {})
    overall_compliance = calculate_compliance_score(overall_usage)

    return {
        "period_hours": hours,
        "overall_compliance": overall_compliance,
        "memory_activity": activity_data,
        "recommendations": generate_recommendations(overall_compliance)
    }

def generate_recommendations(compliance: Dict) -> List[str]:
    """Generate recommendations based on compliance score."""
    recommendations = []

    if compliance["searches"] == 0:
        recommendations.append("❌ CRITICAL: No search_memory or get_context calls detected")
        recommendations.append("   → START every session with search_memory() + get_context()")

    if compliance["stores"] == 0:
        recommendations.append("❌ CRITICAL: No store_memory calls detected")
        recommendations.append("   → STORE memories after solving problems, making decisions, or fetching docs")

    if compliance["total_operations"] < 3:
        recommendations.append("⚠️  WARNING: Low memory system usage")
        recommendations.append("   → Increase usage frequency throughout session")

    if compliance["total_score"] < 70:
        recommendations.append("⚠️  WARNING: Compliance score below recommended threshold")
        recommendations.append("   → Review CLAUDE.md memory protocol requirements")

    if compliance["total_score"] >= 90:
        recommendations.append("✅ EXCELLENT: Memory protocol being followed correctly")
        recommendations.append("   → Keep up the good work!")

    return recommendations

def display_report(report: Dict):
    """Display the compliance report."""
    print("\n" + "═" * 60)
    print("📊 AGENT COMPLIANCE REPORT")
    print("═" * 60)

    print(f"\nPeriod: Last {report['period_hours']} hours")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Overall Compliance Score
    compliance = report["overall_compliance"]
    print("\n" + "─" * 60)
    print("🎯 OVERALL COMPLIANCE SCORE")
    print("─" * 60)

    score = compliance["total_score"]
    grade = compliance["grade"]

    # Visual score bar
    filled = int(score / 5)  # 20 chars for 100 points
    bar = "█" * filled + "░" * (20 - filled)

    print(f"\nScore: {score:.1f}/100 {bar}")
    print(f"Grade: {grade}\n")

    # Score Breakdown
    breakdown = compliance["breakdown"]
    print("Breakdown:")
    print(f"  Search & Context:  {breakdown['search_score']:5.1f}/40 pts")
    print(f"  Memory Storage:    {breakdown['store_score']:5.1f}/40 pts")
    print(f"  Usage Frequency:   {breakdown['frequency_score']:5.1f}/20 pts")

    # Usage Stats
    print("\n" + "─" * 60)
    print("📈 MEMORY OPERATIONS")
    print("─" * 60)
    print(f"\nSearch Operations: {compliance['searches']}")
    print(f"Store Operations: {compliance['stores']}")
    print(f"Total Operations: {compliance['total_operations']}")

    # Memory Activity
    activity = report.get("memory_activity", {})
    if "error" not in activity:
        print("\n" + "─" * 60)
        print("💾 STORED MEMORIES")
        print("─" * 60)
        print(f"\nTotal Stored: {activity.get('total_stored', 0)}")

        by_type = activity.get("by_type", {})
        if by_type:
            print(f"\nBy Type:")
            for mem_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"  {mem_type:12} {count:4}")

        by_project = activity.get("by_project", {})
        if by_project:
            print(f"\nBy Project (Top 5):")
            for project, count in sorted(by_project.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {project:20} {count:4}")

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        print("\n" + "─" * 60)
        print("💡 RECOMMENDATIONS")
        print("─" * 60)
        print("")
        for rec in recommendations:
            print(rec)

    print("\n" + "═" * 60)

def main():
    """Main compliance scoring workflow."""
    print("🎯 Agent Compliance Scoring")
    print("═" * 60)

    # Check service
    try:
        response = requests.get(f"{MEMORY_API}/health")
        response.raise_for_status()
        print("✅ Memory service is running")
    except Exception as e:
        print(f"❌ Memory service not available: {e}")
        sys.exit(1)

    # Get time period from arguments
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24

    # Generate report
    report = generate_compliance_report(hours)

    # Display report
    display_report(report)

    # Return exit code based on compliance
    score = report["overall_compliance"]["total_score"]
    if score >= 70:
        print("\n✅ Compliance: PASSING")
        sys.exit(0)
    else:
        print(f"\n⚠️  Compliance: NEEDS IMPROVEMENT (score < 70)")
        sys.exit(1)

if __name__ == "__main__":
    main()
