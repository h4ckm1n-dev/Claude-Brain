"""Background job scheduler for memory maintenance tasks.

Runs periodic consolidation and cleanup jobs.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Scheduler configuration
CONSOLIDATION_INTERVAL_HOURS = int(os.getenv("CONSOLIDATION_INTERVAL_HOURS", "24"))
CONSOLIDATION_OLDER_THAN_DAYS = int(os.getenv("CONSOLIDATION_OLDER_THAN_DAYS", "7"))
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"

_scheduler = None


def get_scheduler():
    """Get or create the scheduler instance."""
    global _scheduler

    if _scheduler is None and SCHEDULER_ENABLED:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            _scheduler = BackgroundScheduler()

            # Add consolidation job
            _scheduler.add_job(
                run_scheduled_consolidation,
                trigger=IntervalTrigger(hours=CONSOLIDATION_INTERVAL_HOURS),
                id="consolidation_job",
                name="Memory Consolidation",
                replace_existing=True
            )

            # Add memory strength decay job (FadeMem-inspired adaptive forgetting)
            _scheduler.add_job(
                run_memory_strength_update,
                trigger=IntervalTrigger(hours=24),
                id="memory_strength_update_job",
                name="Adaptive Forgetting (Strength Update)",
                replace_existing=True
            )

            # Add brain intelligence jobs
            _scheduler.add_job(
                run_relationship_inference,
                trigger=IntervalTrigger(hours=24),
                id="relationship_inference_job",
                name="Relationship Inference",
                replace_existing=True
            )

            _scheduler.add_job(
                run_adaptive_importance,
                trigger=IntervalTrigger(hours=24),
                id="adaptive_importance_job",
                name="Adaptive Importance Scoring",
                replace_existing=True
            )

            _scheduler.add_job(
                run_utility_archival,
                trigger=IntervalTrigger(hours=24),
                id="utility_archival_job",
                name="Utility-Based Archival",
                replace_existing=True
            )

            # Full brain mode jobs
            _scheduler.add_job(
                run_memory_replay,
                trigger=IntervalTrigger(hours=12),
                id="memory_replay_job",
                name="Memory Replay (Sleep Mode)",
                replace_existing=True
            )

            _scheduler.add_job(
                run_spaced_repetition,
                trigger=IntervalTrigger(hours=6),
                id="spaced_repetition_job",
                name="Spaced Repetition Review",
                replace_existing=True
            )

            # Advanced brain mode jobs
            _scheduler.add_job(
                run_emotional_analysis,
                trigger=IntervalTrigger(hours=24),
                id="emotional_analysis_job",
                name="Emotional Weight Analysis",
                replace_existing=True
            )

            _scheduler.add_job(
                run_interference_detection,
                trigger=IntervalTrigger(hours=168),  # Weekly
                id="interference_detection_job",
                name="Interference Detection & Resolution",
                replace_existing=True
            )

            _scheduler.add_job(
                run_meta_learning,
                trigger=IntervalTrigger(hours=168),  # Weekly
                id="meta_learning_job",
                name="Meta-Learning (Performance Tuning)",
                replace_existing=True
            )

            logger.info(f"Scheduler initialized with {CONSOLIDATION_INTERVAL_HOURS}h consolidation + FULL BRAIN MODE + ADVANCED BRAIN MODE jobs")

        except ImportError:
            logger.warning("apscheduler not installed, background jobs disabled")
            _scheduler = "disabled"
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            _scheduler = "disabled"

    return _scheduler


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()

    if scheduler and scheduler != "disabled":
        if not scheduler.running:
            scheduler.start()
            logger.info("Background scheduler started")
        return True

    return False


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler and _scheduler != "disabled":
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
        _scheduler = None


def run_scheduled_consolidation():
    """Run consolidation as a scheduled job."""
    logger.info("Running scheduled consolidation...")

    try:
        from .consolidation import run_consolidation
        from . import collections

        client = collections.get_client()
        result = run_consolidation(
            client,
            collections.COLLECTION_NAME,
            older_than_days=CONSOLIDATION_OLDER_THAN_DAYS,
            dry_run=False
        )

        logger.info(
            f"Scheduled consolidation complete: "
            f"analyzed={result.analyzed}, "
            f"consolidated={result.consolidated}, "
            f"archived={result.archived}"
        )

    except Exception as e:
        logger.error(f"Scheduled consolidation failed: {e}")


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    scheduler = get_scheduler()

    if scheduler == "disabled" or scheduler is None:
        return {
            "enabled": False,
            "running": False,
            "jobs": []
        }

    jobs = []
    for job in scheduler.get_jobs():
        try:
            next_run = job.next_run_time.isoformat() if hasattr(job, 'next_run_time') and job.next_run_time else None
        except Exception:
            next_run = None

        jobs.append({
            "id": job.id,
            "name": job.name if hasattr(job, 'name') else job.id,
            "next_run": next_run
        })

    return {
        "enabled": True,
        "running": scheduler.running,
        "jobs": jobs,
        "consolidation_interval_hours": CONSOLIDATION_INTERVAL_HOURS,
        "consolidation_older_than_days": CONSOLIDATION_OLDER_THAN_DAYS
    }


def trigger_job(job_id: str) -> bool:
    """Manually trigger a scheduled job."""
    scheduler = get_scheduler()

    if scheduler and scheduler != "disabled":
        job = scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=None)  # Run immediately
            return True

    return False


# ============================================================================
# Brain Intelligence Scheduled Jobs
# ============================================================================


def run_relationship_inference():
    """Run relationship inference as a scheduled job."""
    logger.info("Running scheduled relationship inference...")

    try:
        from .relationship_inference import RelationshipInference
        import asyncio

        # Run async inference functions
        async def infer_all():
            # Infer error→solution links
            fixes = await RelationshipInference.infer_error_solution_links(lookback_days=30)

            # Infer related links
            related = await RelationshipInference.infer_related_links(batch_size=20)

            # Infer temporal links
            temporal = await RelationshipInference.infer_temporal_links(hours_window=2)

            return fixes, related, temporal

        # Run in event loop
        fixes, related, temporal = asyncio.run(infer_all())

        logger.info(
            f"Scheduled relationship inference complete: "
            f"fixes={fixes}, related={related}, temporal={temporal}"
        )

    except Exception as e:
        logger.error(f"Scheduled relationship inference failed: {e}")


def run_adaptive_importance():
    """Run adaptive importance scoring as a scheduled job."""
    logger.info("Running scheduled adaptive importance scoring...")

    try:
        from .consolidation import update_importance_scores_batch
        from . import collections

        client = collections.get_client()
        updated = update_importance_scores_batch(
            client,
            collections.COLLECTION_NAME,
            limit=100
        )

        logger.info(f"Scheduled importance update complete: updated={updated}")

    except Exception as e:
        logger.error(f"Scheduled importance update failed: {e}")


def run_utility_archival():
    """Run utility-based archival as a scheduled job."""
    logger.info("Running scheduled utility-based archival...")

    try:
        from .consolidation import archive_low_utility_memories
        from . import collections

        client = collections.get_client()
        archived = archive_low_utility_memories(
            client,
            collections.COLLECTION_NAME,
            utility_threshold=0.3,
            max_archive=100,
            dry_run=False
        )

        logger.info(f"Scheduled utility archival complete: archived={archived}")

    except Exception as e:
        logger.error(f"Scheduled utility archival failed: {e}")


# ============================================================================
# Full Brain Mode Scheduled Jobs
# ============================================================================


def run_memory_replay():
    """Run memory replay as a scheduled job (simulates sleep consolidation)."""
    logger.info("Running scheduled memory replay (sleep mode)...")

    try:
        from .memory_replay import replay_random_memories, replay_underutilized_memories

        # Replay random important memories
        random_result = replay_random_memories(count=20, importance_threshold=0.5)

        # Replay underutilized memories
        underutilized_result = replay_underutilized_memories(days_since_access=7, count=15)

        logger.info(
            f"Scheduled memory replay complete: "
            f"random={random_result.get('replayed', 0)}, "
            f"underutilized={underutilized_result.get('replayed', 0)}"
        )

    except Exception as e:
        logger.error(f"Scheduled memory replay failed: {e}")


def run_spaced_repetition():
    """Run spaced repetition review as a scheduled job."""
    logger.info("Running scheduled spaced repetition review...")

    try:
        from .reconsolidation import get_spaced_repetition_candidates, reconsolidate_memory

        # Get memories due for review
        candidates = get_spaced_repetition_candidates(limit=20)

        reviewed = 0
        for candidate in candidates:
            # Reconsolidate each candidate
            result = reconsolidate_memory(candidate["id"])
            if result.get("success"):
                reviewed += 1

        logger.info(f"Scheduled spaced repetition complete: reviewed={reviewed}")

    except Exception as e:
        logger.error(f"Scheduled spaced repetition failed: {e}")


# ============================================================================
# Advanced Brain Mode Scheduled Jobs
# ============================================================================


def run_emotional_analysis():
    """Run emotional weighting analysis as a scheduled job."""
    logger.info("Running scheduled emotional analysis...")

    try:
        from .emotional_weighting import run_emotional_analysis as analyze

        analyzed = analyze(limit=100)

        logger.info(f"Scheduled emotional analysis complete: analyzed={analyzed}")

    except Exception as e:
        logger.error(f"Scheduled emotional analysis failed: {e}")


def run_interference_detection():
    """Run interference detection and resolution as a scheduled job."""
    logger.info("Running scheduled interference detection...")

    try:
        from .interference_detection import run_interference_detection as detect

        result = detect(limit=50)

        logger.info(
            f"Scheduled interference detection complete: "
            f"detected={result.get('conflicts_detected', 0)}, "
            f"resolved={result.get('conflicts_resolved', 0)}"
        )

    except Exception as e:
        logger.error(f"Scheduled interference detection failed: {e}")


def run_meta_learning():
    """Run meta-learning (performance tracking and parameter tuning) as a scheduled job."""
    logger.info("Running scheduled meta-learning...")

    try:
        from .meta_learning import run_meta_learning as learn

        result = learn()

        if "error" in result:
            logger.error(f"Meta-learning failed: {result['error']}")
        else:
            metrics = result.get("metrics", {})
            logger.info(
                f"Scheduled meta-learning complete: "
                f"avg_importance={metrics.get('avg_importance', 0):.3f}, "
                f"access_rate={metrics.get('access_rate', 0):.3f}"
            )

    except Exception as e:
        logger.error(f"Scheduled meta-learning failed: {e}")


# ============================================================================
# Adaptive Forgetting Scheduled Job
# ============================================================================


def run_memory_strength_update():
    """Run memory strength update as a scheduled job (FadeMem-inspired adaptive forgetting)."""
    logger.info("Running scheduled memory strength update...")

    try:
        from .forgetting import update_all_memory_strengths
        from . import collections

        client = collections.get_client()
        result = update_all_memory_strengths(
            client,
            collections.COLLECTION_NAME,
            batch_size=100,
            max_updates=None  # Update all memories
        )

        logger.info(
            f"Scheduled memory strength update complete: "
            f"processed={result['total_processed']}, "
            f"updated={result['updated']}, "
            f"archived={result['archived']}, "
            f"purged={result['purged']}, "
            f"avg_strength={result['avg_strength']:.3f}"
        )

    except Exception as e:
        logger.error(f"Scheduled memory strength update failed: {e}")
