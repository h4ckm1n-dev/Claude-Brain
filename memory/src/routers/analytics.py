"""Analytics, insights, and recommendation endpoints.

Provides error trend analysis, knowledge gap detection, pattern clustering,
recommendation engine, and intelligence insights.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

from .. import collections

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analytics"])


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/analytics/pattern-clusters")
async def get_pattern_clusters(min_cluster_size: int = Query(3, ge=1)):
    """Return pattern cluster statistics.
    Currently returns cluster errors grouped by tags using ErrorTrendAnalyzer.
    """
    from ..analytics import ErrorTrendAnalyzer

    try:
        client = collections.get_client()
        clusters = ErrorTrendAnalyzer.cluster_errors_by_tags(
            client=client,
            collection_name=collections.COLLECTION_NAME,
            time_window_days=30,
            min_cluster_size=min_cluster_size
        )
        return {"clusters": clusters}
    except Exception as e:
        logger.error(f"Failed to get pattern clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/comprehensive")
async def get_comprehensive_analytics():
    """Get comprehensive analytics across all dimensions.

    Includes:
    - Error trends (clusters, spikes, recurring)
    - Knowledge gaps (errors without patterns, low documentation)
    - Expertise clusters

    Returns:
        Complete analytics report
    """
    from ..analytics import get_comprehensive_analytics as _get_comprehensive_analytics

    try:
        client = collections.get_client()
        analytics = _get_comprehensive_analytics(
            client,
            collections.COLLECTION_NAME
        )
        return analytics

    except Exception as e:
        logger.error(f"Failed to get comprehensive analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/error-trends")
async def get_error_trends(
    time_window_days: int = Query(default=30, ge=1, le=365, description="Time window in days"),
    min_cluster_size: int = Query(default=2, ge=1, description="Minimum cluster size")
):
    """Get error trend analysis.

    Includes:
    - Error clusters by tags
    - Spike detection
    - Recurring errors

    Args:
        time_window_days: Time window for analysis (default: 30 days)
        min_cluster_size: Minimum errors to form a cluster (default: 2)

    Returns:
        Error trend analysis
    """
    from ..analytics import ErrorTrendAnalyzer

    try:
        client = collections.get_client()

        trends = {
            "clusters": ErrorTrendAnalyzer.cluster_errors_by_tags(
                client,
                collections.COLLECTION_NAME,
                time_window_days=time_window_days,
                min_cluster_size=min_cluster_size
            ),
            "spikes": ErrorTrendAnalyzer.detect_error_spikes(
                client,
                collections.COLLECTION_NAME,
                time_window_days=time_window_days
            ),
            "recurring": ErrorTrendAnalyzer.find_recurring_errors(
                client,
                collections.COLLECTION_NAME,
                time_window_days=time_window_days
            ),
            "time_window_days": time_window_days
        }

        return trends

    except Exception as e:
        logger.error(f"Failed to get error trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/knowledge-gaps")
async def get_knowledge_gaps():
    """Detect knowledge gaps in the system.

    Includes:
    - Topics with errors but no patterns
    - Projects with low documentation
    - Expertise clusters and gaps

    Returns:
        Knowledge gap analysis
    """
    from ..analytics import KnowledgeGapDetector

    try:
        client = collections.get_client()

        gaps = {
            "errors_without_patterns": KnowledgeGapDetector.find_errors_without_patterns(
                client,
                collections.COLLECTION_NAME
            ),
            "low_documentation_projects": KnowledgeGapDetector.find_low_documentation_projects(
                client,
                collections.COLLECTION_NAME
            ),
            "expertise_clusters": KnowledgeGapDetector.identify_expertise_clusters(
                client,
                collections.COLLECTION_NAME
            )
        }

        return gaps

    except Exception as e:
        logger.error(f"Failed to get knowledge gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Recommendation Engine Endpoints
# ============================================================================


@router.post("/recommendations/patterns-for-error")
async def suggest_patterns_for_error(
    error_tags: List[str] = Query(..., description="Tags from the error"),
    error_content: str = Query(..., description="Error content"),
    limit: int = Query(default=5, ge=1, le=20)
):
    """Suggest relevant patterns/docs for an error.

    Args:
        error_tags: Tags from the error
        error_content: Error content
        limit: Maximum suggestions

    Returns:
        List of suggested patterns/docs
    """
    from ..recommendations import RecommendationEngine

    try:
        client = collections.get_client()
        suggestions = RecommendationEngine.suggest_patterns_for_error(
            client,
            collections.COLLECTION_NAME,
            error_tags,
            error_content,
            limit=limit
        )

        return {
            "error_tags": error_tags,
            "suggestions": suggestions,
            "count": len(suggestions)
        }

    except Exception as e:
        logger.error(f"Failed to suggest patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/preventive-patterns")
async def get_preventive_patterns(
    search_query: str = Query(..., description="Search query"),
    query_tags: Optional[List[str]] = Query(None, description="Optional tags"),
    limit: int = Query(default=5, ge=1, le=20)
):
    """Recommend preventive patterns based on a search query.

    Args:
        search_query: User's search query
        query_tags: Optional tags from search context
        limit: Maximum recommendations

    Returns:
        List of preventive patterns
    """
    from ..recommendations import RecommendationEngine

    try:
        client = collections.get_client()
        patterns = RecommendationEngine.recommend_preventive_patterns(
            client,
            collections.COLLECTION_NAME,
            search_query,
            query_tags=query_tags,
            limit=limit
        )

        return {
            "search_query": search_query,
            "patterns": patterns,
            "count": len(patterns)
        }

    except Exception as e:
        logger.error(f"Failed to recommend preventive patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/documentation-topics")
async def suggest_documentation_topics(
    project: Optional[str] = Query(None, description="Optional project filter"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """Suggest topics that need documentation.

    Args:
        project: Optional project filter
        limit: Maximum suggestions

    Returns:
        List of suggested documentation topics
    """
    from ..recommendations import RecommendationEngine

    try:
        client = collections.get_client()
        topics = RecommendationEngine.suggest_documentation_topics(
            client,
            collections.COLLECTION_NAME,
            project=project,
            limit=limit
        )

        return {
            "project": project,
            "topics": topics,
            "count": len(topics)
        }

    except Exception as e:
        logger.error(f"Failed to suggest documentation topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/co-access/stats")
async def get_co_access_stats():
    """Get co-access tracking statistics."""
    from ..recommendations import get_co_access_tracker

    try:
        tracker = get_co_access_tracker()
        stats = tracker.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get co-access stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/co-access/reset")
async def reset_co_access_tracking():
    """Reset co-access tracking data."""
    from ..recommendations import get_co_access_tracker

    try:
        tracker = get_co_access_tracker()
        tracker.reset()
        return {"success": True, "message": "Co-access tracking data reset"}

    except Exception as e:
        logger.error(f"Failed to reset co-access tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/{memory_id}")
async def get_recommendations_for_memory(
    memory_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get comprehensive recommendations for a memory.

    Includes:
    - Context-aware suggestions
    - Suggested patterns (for errors)
    - Collaborative filtering recommendations

    Args:
        memory_id: Memory ID
        limit: Maximum recommendations per category

    Returns:
        Comprehensive recommendations
    """
    from ..recommendations import generate_comprehensive_recommendations

    try:
        # Get the memory
        memory = collections.get_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        client = collections.get_client()
        recommendations = generate_comprehensive_recommendations(
            client,
            collections.COLLECTION_NAME,
            memory.model_dump(),
            limit=limit
        )

        return recommendations

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Insights Endpoints
# ============================================================================


@router.get("/insights/recurring-patterns")
async def get_recurring_patterns(limit: int = Query(default=10, ge=1, le=50)):
    """Get recurring error->solution patterns."""
    try:
        from ..insights import InsightGenerator

        patterns = InsightGenerator.discover_recurring_patterns(limit)
        return {"patterns": patterns, "count": len(patterns)}

    except Exception as e:
        logger.error(f"Recurring patterns API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/expertise-profile")
async def get_expertise_profile():
    """Analyze user's technical expertise based on memory distribution."""
    try:
        from ..insights import InsightGenerator

        profile = InsightGenerator.analyze_expertise_profile()
        return {
            "expertise": profile,
            "total_technologies": len(profile),
            "expert_in": [tech for tech, data in profile.items() if data["level"] == "expert"],
            "proficient_in": [tech for tech, data in profile.items() if data["level"] == "proficient"]
        }

    except Exception as e:
        logger.error(f"Expertise profile API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/anomalies")
async def get_memory_anomalies():
    """Find unusual/suspicious memories that may need attention."""
    try:
        from ..insights import InsightGenerator

        anomalies = InsightGenerator.detect_memory_anomalies()
        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "by_reason": {
                "extremely_short": sum(1 for a in anomalies if "extremely_short" in a["anomaly_reasons"]),
                "orphaned": sum(1 for a in anomalies if "orphaned" in a["anomaly_reasons"]),
                "old_unaccessed": sum(1 for a in anomalies if "old_unaccessed" in a["anomaly_reasons"]),
                "high_importance_low_access": sum(1 for a in anomalies if "high_importance_low_access" in a["anomaly_reasons"])
            }
        }

    except Exception as e:
        logger.error(f"Anomaly detection API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/error-trends")
async def get_insights_error_trends(days: int = Query(default=30, ge=7, le=90)):
    """Analyze error frequency and resolution trends."""
    try:
        from ..insights import InsightGenerator

        trends = InsightGenerator.analyze_error_trends(days)
        return trends

    except Exception as e:
        logger.error(f"Error trends API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/summary")
async def get_intelligence_summary(limit: int = Query(default=5, ge=1, le=10)):
    """Get top intelligence insights about user's memory patterns."""
    try:
        from ..insights import InsightGenerator

        insights = InsightGenerator.generate_intelligence_summary(limit)
        return {"insights": insights, "count": len(insights)}

    except Exception as e:
        logger.error(f"Intelligence summary API failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
