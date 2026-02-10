"""Generate intelligent insights from memory patterns.

This module analyzes stored memories to extract actionable intelligence:
- Recurring error→solution patterns
- User expertise profiling
- Memory anomaly detection
- Error trend analysis
- Intelligence summaries
"""

from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime, timedelta, timezone
import logging

from . import collections
from .models import MemoryType

logger = logging.getLogger(__name__)

# Tech stack keywords for expertise analysis
TECH_STACK_KEYWORDS = {
    # Languages
    "python", "javascript", "typescript", "java", "go", "rust", "ruby", "php",
    "c++", "c#", "swift", "kotlin", "scala", "r", "matlab",

    # Frontend
    "react", "vue", "angular", "svelte", "nextjs", "vite", "webpack", "tailwind",
    "bootstrap", "sass", "less", "redux", "mobx", "zustand",

    # Backend
    "express", "django", "flask", "fastapi", "spring", "rails", "laravel",
    "nodejs", "deno", "gin", "actix",

    # Databases
    "postgresql", "mongodb", "redis", "mysql", "sqlite", "qdrant", "neo4j",
    "elasticsearch", "dynamodb", "cassandra", "mariadb",

    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github-actions", "gitlab-ci", "circleci",

    # AI/ML
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy",
    "langchain", "openai", "anthropic", "huggingface",
}


class InsightGenerator:
    """Analyze memories and extract actionable insights."""

    @staticmethod
    def discover_recurring_patterns(limit: int = 10) -> List[Dict]:
        """
        Find recurring error→solution patterns.

        Returns patterns like: 'Docker errors usually fixed by permission changes'

        Algorithm:
        1. Get all resolved error memories
        2. Extract keywords from error messages
        3. Extract keywords from solutions
        4. Count frequency of (error_keyword → solution_keyword) pairs
        5. Return patterns occurring 3+ times with confidence scores
        """
        try:
            client = collections.get_client()

            # Get resolved error memories
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                scroll_filter=None,  # Get all, filter in Python
                limit=1000,
                with_payload=True,
                with_vectors=False
            )

            # Filter for resolved errors
            resolved_errors = []
            for record in records:
                payload = record.payload
                if payload.get("type") == "error" and payload.get("resolved"):
                    resolved_errors.append({
                        "id": str(record.id),
                        "content": payload.get("content", ""),
                        "error_message": payload.get("error_message", ""),
                        "solution": payload.get("solution", ""),
                        "tags": payload.get("tags", [])
                    })

            if len(resolved_errors) < 3:
                return []

            # Extract patterns
            pattern_counter = Counter()
            pattern_examples = {}

            for error in resolved_errors:
                # Extract error keywords from tags or content
                error_keywords = set(tag.lower() for tag in error["tags"])

                # Add keywords from error message
                if error["error_message"]:
                    words = error["error_message"].lower().split()
                    error_keywords.update(w for w in words if w in TECH_STACK_KEYWORDS)

                # Extract solution keywords
                solution_keywords = set()
                if error["solution"]:
                    words = error["solution"].lower().split()
                    solution_keywords.update(w for w in words if w in TECH_STACK_KEYWORDS or len(w) > 8)

                # Create patterns
                for err_kw in error_keywords:
                    for sol_kw in solution_keywords:
                        pattern = (err_kw, sol_kw)
                        pattern_counter[pattern] += 1

                        # Store example
                        if pattern not in pattern_examples:
                            pattern_examples[pattern] = error["id"]

            # Extract significant patterns (3+ occurrences)
            patterns = []
            for (error_type, solution_type), count in pattern_counter.most_common(limit):
                if count >= 3:
                    patterns.append({
                        "pattern": f"'{error_type}' errors usually fixed by '{solution_type}'",
                        "error_keyword": error_type,
                        "solution_keyword": solution_type,
                        "frequency": count,
                        "confidence": round(count / len(resolved_errors), 3),
                        "example_memory_id": pattern_examples.get((error_type, solution_type))
                    })

            return patterns

        except Exception as e:
            logger.error(f"Pattern discovery failed: {e}")
            return []

    @staticmethod
    def analyze_expertise_profile() -> Dict:
        """
        Determine user's expertise areas based on memory distribution.

        Returns insights like:
        - "You're a React expert" (50+ React memories)
        - "You frequently troubleshoot Docker" (20 Docker error resolutions)

        Expertise levels:
        - expert: 50+ memories
        - proficient: 20-49 memories
        - familiar: 10-19 memories
        - beginner: <10 memories
        """
        try:
            client = collections.get_client()

            # Get all memories
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                limit=5000,
                with_payload=True,
                with_vectors=False
            )

            # Count tech stack mentions
            tech_counter = Counter()
            tech_by_type = {}  # Track what type of work user does with each tech

            for record in records:
                payload = record.payload
                tags = payload.get("tags", [])
                memory_type = payload.get("type")

                for tag in tags:
                    tag_lower = tag.lower()
                    if tag_lower in TECH_STACK_KEYWORDS:
                        tech_counter[tag_lower] += 1

                        # Track type distribution
                        if tag_lower not in tech_by_type:
                            tech_by_type[tag_lower] = Counter()
                        tech_by_type[tag_lower][memory_type] += 1

            # Determine expertise levels
            expertise = {}
            for tech, count in tech_counter.most_common(15):
                if count >= 50:
                    level = "expert"
                elif count >= 20:
                    level = "proficient"
                elif count >= 10:
                    level = "familiar"
                else:
                    continue  # Skip beginners for brevity

                # Calculate recent activity (last 30 days)
                recent_count = InsightGenerator._count_recent_tech_memories(records, tech, days=30)

                # Get primary activity type
                type_dist = tech_by_type.get(tech, Counter())
                primary_activity = type_dist.most_common(1)[0][0] if type_dist else "general"

                expertise[tech] = {
                    "level": level,
                    "memory_count": count,
                    "recent_activity": recent_count,
                    "primary_activity_type": primary_activity,
                    "percentage_of_total": round(count / len(records) * 100, 1)
                }

            return expertise

        except Exception as e:
            logger.error(f"Expertise analysis failed: {e}")
            return {}

    @staticmethod
    def _count_recent_tech_memories(records: List, tech: str, days: int) -> int:
        """Count memories mentioning a tech in the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        count = 0

        for record in records:
            payload = record.payload
            created_at = datetime.fromisoformat(payload["created_at"].replace('Z', '+00:00'))

            if created_at >= cutoff:
                tags_lower = [t.lower() for t in payload.get("tags", [])]
                if tech in tags_lower:
                    count += 1

        return count

    @staticmethod
    def detect_memory_anomalies() -> List[Dict]:
        """
        Find unusual/suspicious memories that may need attention.

        Detects:
        - Extremely short content (<20 chars)
        - Orphaned memories (no relationships)
        - Old but never accessed (>30 days, 0 access)
        - High importance but low access (importance >0.8, access <2)
        """
        try:
            client = collections.get_client()

            # Get all memories
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                limit=5000,
                with_payload=True,
                with_vectors=False
            )

            anomalies = []
            now = datetime.now(timezone.utc)

            for record in records:
                payload = record.payload
                # Skip archived memories
                if payload.get("archived", False):
                    continue
                reasons = []

                # Check content length
                content = payload.get("content", "")
                if len(content) < 20:
                    reasons.append("extremely_short")

                # Compute age early — needed by multiple checks below
                created_at = datetime.fromisoformat(payload["created_at"].replace('Z', '+00:00'))
                age_days = (now - created_at).days
                access_count = payload.get("access_count", 0)

                # Check relationships (orphaned) — only flag after 3 days
                # (inference needs time to connect new memories)
                relations = payload.get("relations", [])
                if not relations and age_days >= 3:
                    reasons.append("orphaned")

                # Check age vs access
                if age_days > 30 and access_count == 0:
                    reasons.append("old_unaccessed")

                # Check importance vs access — only flag after 7 days
                # (new high-quality memories naturally start with low access)
                importance = payload.get("importance_score", 0.5)
                if importance > 0.8 and access_count < 2 and age_days >= 7:
                    reasons.append("high_importance_low_access")

                # If any anomalies found, add to list
                if reasons:
                    anomalies.append({
                        "memory_id": str(record.id),
                        "content_preview": content[:100],
                        "anomaly_reasons": reasons,
                        "suggested_action": InsightGenerator._suggest_action(reasons),
                        "age_days": age_days,
                        "access_count": access_count,
                        "importance": importance
                    })

            # Sort by number of anomaly reasons (most anomalous first)
            anomalies.sort(key=lambda x: len(x["anomaly_reasons"]), reverse=True)

            return anomalies[:50]  # Return top 50

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []

    @staticmethod
    def _suggest_action(reasons: List[str]) -> str:
        """Suggest action based on anomaly reasons."""
        if "extremely_short" in reasons:
            return "Review and expand content or archive if not valuable"
        elif "orphaned" in reasons and "old_unaccessed" in reasons:
            return "Consider archiving - no connections and never used"
        elif "high_importance_low_access" in reasons:
            return "Verify importance score or link to related memories"
        elif "old_unaccessed" in reasons:
            return "Archive or re-tag for better discoverability"
        else:
            return "Review for quality and relevance"

    @staticmethod
    def analyze_error_trends(days: int = 30) -> Dict:
        """
        Analyze error frequency, resolution rate, and common error types.

        Returns:
        - Total errors in period
        - Resolution rate (% with solutions)
        - Most frequent error types
        - Trend (increasing/decreasing compared to previous period)
        """
        try:
            client = collections.get_client()

            # Get all error memories
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                limit=5000,
                with_payload=True,
                with_vectors=False
            )

            # Filter for errors
            now = datetime.now(timezone.utc)
            cutoff_recent = now - timedelta(days=days)
            cutoff_previous = now - timedelta(days=days * 2)

            recent_errors = []
            previous_errors = []

            for record in records:
                payload = record.payload
                if payload.get("type") != "error":
                    continue

                created_at = datetime.fromisoformat(payload["created_at"].replace('Z', '+00:00'))

                if created_at >= cutoff_recent:
                    recent_errors.append(payload)
                elif cutoff_previous <= created_at < cutoff_recent:
                    previous_errors.append(payload)

            # Calculate resolution rate
            resolved_count = sum(1 for e in recent_errors if e.get("resolved"))
            resolution_rate = resolved_count / len(recent_errors) if recent_errors else 0

            # Count error types (from tags)
            error_types = Counter()
            for error in recent_errors:
                tags = error.get("tags", [])
                # Use first tag as error type, or extract from error message
                if tags:
                    error_types[tags[0]] += 1
                else:
                    error_types["untagged"] += 1

            # Calculate trend
            if previous_errors:
                trend_pct = ((len(recent_errors) - len(previous_errors)) / len(previous_errors)) * 100
            else:
                trend_pct = 0

            trend = "increasing" if trend_pct > 10 else "decreasing" if trend_pct < -10 else "stable"

            return {
                "total_errors": len(recent_errors),
                "resolved_errors": resolved_count,
                "unresolved_errors": len(recent_errors) - resolved_count,
                "resolution_rate": round(resolution_rate * 100, 1),
                "top_error_types": [
                    {"type": etype, "count": count}
                    for etype, count in error_types.most_common(10)
                ],
                "trend": trend,
                "trend_percentage": round(trend_pct, 1),
                "period_days": days,
                "previous_period_total": len(previous_errors)
            }

        except Exception as e:
            logger.error(f"Error trend analysis failed: {e}")
            return {
                "total_errors": 0,
                "resolution_rate": 0,
                "trend": "unknown",
                "error": str(e)
            }

    @staticmethod
    def generate_intelligence_summary(limit: int = 5) -> List[str]:
        """
        Generate human-readable intelligence insights.

        Returns insights like:
        - "You've successfully resolved 45 Docker errors"
        - "React is your most-used technology (150 memories)"
        - "Your error resolution rate is 85%"
        """
        insights = []

        try:
            client = collections.get_client()

            # Get all memories
            records, _ = client.scroll(
                collection_name=collections.COLLECTION_NAME,
                limit=5000,
                with_payload=True,
                with_vectors=False
            )

            # Count resolved errors
            resolved_errors = sum(
                1 for r in records
                if r.payload.get("type") == "error" and r.payload.get("resolved")
            )
            if resolved_errors > 10:
                insights.append(f"You've successfully resolved {resolved_errors} errors")

            # Find top technology
            tech_counter = Counter()
            for record in records:
                tags = record.payload.get("tags", [])
                for tag in tags:
                    tag_lower = tag.lower()
                    if tag_lower in TECH_STACK_KEYWORDS:
                        tech_counter[tag_lower] += 1

            if tech_counter:
                top_tech, count = tech_counter.most_common(1)[0]
                if count > 20:
                    insights.append(f"{top_tech.title()} is your most-used technology ({count} memories)")

            # Calculate error resolution rate
            total_errors = sum(1 for r in records if r.payload.get("type") == "error")
            if total_errors > 5:
                resolution_rate = (resolved_errors / total_errors) * 100
                insights.append(f"Your error resolution rate is {resolution_rate:.0f}%")

            # Count recent learnings
            now = datetime.now(timezone.utc)
            cutoff_30d = now - timedelta(days=30)
            recent_learnings = sum(
                1 for r in records
                if r.payload.get("type") == "learning" and
                datetime.fromisoformat(r.payload["created_at"].replace('Z', '+00:00')) >= cutoff_30d
            )
            if recent_learnings > 5:
                insights.append(f"You've documented {recent_learnings} learnings this month")

            # Detect pattern insight
            patterns = InsightGenerator.discover_recurring_patterns(limit=1)
            if patterns:
                insights.append(f"Pattern detected: {patterns[0]['pattern']}")

            # Memory count insight
            if len(records) > 100:
                insights.append(f"Your knowledge base contains {len(records)} memories")

            return insights[:limit]

        except Exception as e:
            logger.error(f"Intelligence summary generation failed: {e}")
            return ["Unable to generate insights due to error"]
