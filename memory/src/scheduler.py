"""Background job scheduler for memory maintenance tasks.

Runs periodic consolidation and cleanup jobs.
Uses job locking to prevent race conditions between conflicting jobs.
"""

import logging
import os
from typing import Optional

from .job_lock import job_lock, LOCK_QUALITY, LOCK_CONSOLIDATION, LOCK_STRENGTH, LOCK_GRAPH

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

            # Add session consolidation job (Phase 1.3)
            _scheduler.add_job(
                run_session_consolidation,
                trigger=IntervalTrigger(hours=12),
                id="session_consolidation_job",
                name="Session Consolidation",
                replace_existing=True
            )

            # Add quality score update job (Phase 3.2)
            _scheduler.add_job(
                run_quality_score_update,
                trigger=IntervalTrigger(hours=24),
                id="quality_score_update_job",
                name="Quality Score Update & Tier Promotion",
                replace_existing=True
            )

            # Add state machine update job (Phase 4.1)
            _scheduler.add_job(
                run_state_machine_update,
                trigger=IntervalTrigger(hours=12),
                id="state_machine_update_job",
                name="Memory State Machine Updates",
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
        with job_lock(LOCK_CONSOLIDATION):
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

    except RuntimeError:
        logger.info("Skipping consolidation - another consolidation job is running")
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
        with job_lock(LOCK_GRAPH):
            from .relationship_inference import RelationshipInference
            import asyncio

            async def infer_all():
                fixes = await RelationshipInference.infer_error_solution_links(lookback_days=30)
                related = await RelationshipInference.infer_related_links(batch_size=20)
                temporal = await RelationshipInference.infer_temporal_links(hours_window=2)
                return fixes, related, temporal

            fixes, related, temporal = asyncio.run(infer_all())

            logger.info(
                f"Scheduled relationship inference complete: "
                f"fixes={fixes}, related={related}, temporal={temporal}"
            )

    except RuntimeError:
        logger.info("Skipping relationship inference - another graph job is running")
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
        with job_lock(LOCK_STRENGTH):
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

    except RuntimeError:
        logger.info("Skipping utility archival - another strength/archival job is running")
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
        with job_lock(LOCK_STRENGTH):
            from .forgetting import update_all_memory_strengths
            from . import collections

            client = collections.get_client()
            result = update_all_memory_strengths(
                client,
                collections.COLLECTION_NAME,
                batch_size=100,
                max_updates=None
            )

            logger.info(
                f"Scheduled memory strength update complete: "
                f"processed={result['total_processed']}, "
                f"updated={result['updated']}, "
                f"archived={result['archived']}, "
                f"purged={result['purged']}, "
                f"avg_strength={result['avg_strength']:.3f}"
            )

    except RuntimeError:
        logger.info("Skipping strength update - another strength/archival job is running")
    except Exception as e:
        logger.error(f"Scheduled memory strength update failed: {e}")


# ============================================================================
# Session Consolidation Scheduled Job (Phase 1.3)
# ============================================================================


def run_session_consolidation():
    """Run session consolidation as a scheduled job."""
    logger.info("Running scheduled session consolidation...")

    try:
        with job_lock(LOCK_CONSOLIDATION):
            from .session_extraction import SessionManager
            from . import collections

            client = collections.get_client()

            # Get sessions ready for consolidation
            ready_sessions = SessionManager.get_sessions_for_consolidation(
                client,
                collections.COLLECTION_NAME,
                older_than_hours=24
            )

            consolidated = 0
            failed = 0

            # Consolidate each session
            for session_id in ready_sessions:
                try:
                    SessionManager.infer_session_relationships(
                        client,
                        collections.COLLECTION_NAME,
                        session_id
                    )

                    summary_id = SessionManager.consolidate_session(
                        client,
                        collections.COLLECTION_NAME,
                        session_id
                    )

                    if summary_id:
                        consolidated += 1
                    else:
                        failed += 1

                except Exception as e:
                    logger.error(f"Failed to consolidate session {session_id}: {e}")
                    failed += 1

            logger.info(
                f"Scheduled session consolidation complete: "
                f"consolidated={consolidated}, failed={failed}"
            )

    except RuntimeError:
        logger.info("Skipping session consolidation - another consolidation job is running")
    except Exception as e:
        logger.error(f"Scheduled session consolidation failed: {e}")


# ============================================================================
# Quality Tracking Scheduled Job (Phase 3.2)
# ============================================================================


def run_quality_score_update():
    """Run quality score update as a scheduled job.

    Note: Tier promotion is handled exclusively by run_state_machine_update()
    to prevent race conditions from duplicate promotion logic.
    """
    logger.info("Running scheduled quality score update...")

    try:
        with job_lock(LOCK_QUALITY):
            from .quality_tracking import QualityTracker
            from . import collections

            client = collections.get_client()

            # Update quality scores for all active memories
            update_result = QualityTracker.update_quality_scores(
                client,
                collections.COLLECTION_NAME,
                batch_size=100
            )

            logger.info(
                f"Scheduled quality score update complete: "
                f"updated={update_result['total_updated']}, "
                f"failed={update_result['failed']}, "
                f"avg_quality={update_result['avg_quality']:.3f}"
            )

    except RuntimeError:
        logger.info("Skipping quality update - another quality/promotion job is running")
    except Exception as e:
        logger.error(f"Scheduled quality score update failed: {e}")


# ============================================================================
# State Machine Scheduled Job (Phase 4.1)
# ============================================================================


def run_state_machine_update():
    """Run memory state machine updates as a scheduled job.

    This job owns all tier promotions (episodic -> semantic -> procedural).
    """
    logger.info("Running scheduled state machine update...")

    try:
        with job_lock(LOCK_QUALITY):
            from .lifecycle import update_memory_states
            from . import collections

            client = collections.get_client()

            # Update memory states based on lifecycle rules
            result = update_memory_states(
                client,
                collections.COLLECTION_NAME,
                batch_size=100,
                max_updates=None
            )

            logger.info(
                f"Scheduled state machine update complete: "
                f"processed={result['total_processed']}, "
                f"transitions={result['transitions']}, "
                f"failed={result['failed']}"
            )

            if result.get("by_transition"):
                transitions_str = ", ".join([
                    f"{k}: {v}" for k, v in result["by_transition"].items()
                ])
                logger.info(f"Transitions: {transitions_str}")

    except RuntimeError:
        logger.info("Skipping state machine update - another quality/promotion job is running")
    except Exception as e:
        logger.error(f"Scheduled state machine update failed: {e}")
