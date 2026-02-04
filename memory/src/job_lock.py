"""Thread-based job locking to prevent scheduler race conditions.

Prevents overlapping execution of conflicting jobs that modify the same data.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Lock groups: jobs in the same group cannot run concurrently
_locks: dict[str, threading.Lock] = {}
_lock_registry_lock = threading.Lock()


def _get_lock(name: str) -> threading.Lock:
    """Get or create a named lock."""
    with _lock_registry_lock:
        if name not in _locks:
            _locks[name] = threading.Lock()
        return _locks[name]


@contextmanager
def job_lock(name: str, timeout: Optional[float] = 30.0):
    """Context manager for job-level locking.

    Args:
        name: Lock group name (jobs sharing a name cannot run concurrently)
        timeout: Max seconds to wait for lock. None = block forever.

    Raises:
        RuntimeError: If lock cannot be acquired within timeout.
    """
    lock = _get_lock(name)
    acquired = lock.acquire(timeout=timeout) if timeout else lock.acquire()

    if not acquired:
        logger.warning(f"Job lock '{name}' not acquired within {timeout}s, skipping")
        raise RuntimeError(f"Could not acquire job lock '{name}'")

    logger.debug(f"Acquired job lock '{name}'")
    try:
        yield
    finally:
        lock.release()
        logger.debug(f"Released job lock '{name}'")


# Lock group names for related jobs
LOCK_QUALITY = "quality_and_promotion"
LOCK_CONSOLIDATION = "consolidation"
LOCK_STRENGTH = "memory_strength"
LOCK_GRAPH = "graph_operations"
