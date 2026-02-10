"""Standalone scheduler worker for Claude Memory Service.

Runs all background jobs (consolidation, strength decay, brain intelligence, etc.)
in an isolated process. The API server runs with SCHEDULER_ENABLED=false.

Health check available on port 8101 (/health).
"""

import logging
import os
import signal
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Force scheduler enabled for worker process
os.environ["SCHEDULER_ENABLED"] = "true"

_shutdown_event = threading.Event()


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks and scheduler management."""

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            from .scheduler import get_scheduler_status
            status = get_scheduler_status()
            self._send_json(200, {
                "status": "healthy" if status.get("running") else "degraded",
                "service": "claude-mem-worker",
                "scheduler": status,
            })
        elif self.path == "/scheduler/status":
            from .scheduler import get_scheduler_status
            self._send_json(200, get_scheduler_status())
        else:
            self._send_json(404, {"detail": "Not Found"})

    def do_POST(self):
        # POST /scheduler/jobs/{job_id}/trigger
        if self.path.startswith("/scheduler/jobs/") and self.path.endswith("/trigger"):
            job_id = self.path.split("/scheduler/jobs/")[1].rsplit("/trigger")[0]
            from .scheduler import trigger_job
            if trigger_job(job_id):
                self._send_json(200, {"status": "triggered", "job_id": job_id})
            else:
                self._send_json(404, {"detail": "Job not found or scheduler disabled"})
        elif self.path == "/scheduler/trigger-all":
            from .scheduler import get_scheduler
            from datetime import datetime, timezone
            scheduler = get_scheduler()
            if not scheduler or scheduler == "disabled":
                self._send_json(503, {"detail": "Scheduler not available"})
                return
            triggered = []
            for job in scheduler.get_jobs():
                job.modify(next_run_time=datetime.now(timezone.utc))
                triggered.append(job.id)
            self._send_json(200, {"status": "triggered", "jobs": triggered})
        else:
            self._send_json(404, {"detail": "Not Found"})

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


def _signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    logger.info(f"Received signal {signum}, shutting down...")
    _shutdown_event.set()


def main():
    logger.info("Starting Claude Memory Worker...")

    # Register signal handlers
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Initialize Qdrant collections (same as server lifespan)
    from . import collections
    from . import documents

    collections.init_collections()
    documents.init_documents_collection()

    # Validate embedding dimensions
    try:
        from .embeddings import validate_embedding_config
        validation = validate_embedding_config()
        if not validation.get("valid", True):
            logger.error(f"EMBEDDING VALIDATION FAILED: {validation['message']}")
        else:
            logger.info(f"Embedding validation: {validation['message']}")
    except Exception as e:
        logger.warning(f"Embedding validation skipped: {e}")

    # Start the scheduler
    from .scheduler import start_scheduler, stop_scheduler

    if start_scheduler():
        logger.info("Worker scheduler started successfully")
    else:
        logger.error("Failed to start scheduler — exiting")
        sys.exit(1)

    # Start health check server in a thread
    health_port = int(os.getenv("HEALTH_PORT", "8101"))
    health_server = HTTPServer(("0.0.0.0", health_port), HealthHandler)
    health_thread = threading.Thread(target=health_server.serve_forever, daemon=True)
    health_thread.start()
    logger.info(f"Health check server listening on port {health_port}")

    logger.info("Worker ready — waiting for shutdown signal")

    # Block until shutdown signal
    _shutdown_event.wait()

    # Graceful shutdown
    logger.info("Shutting down worker...")
    health_server.shutdown()
    stop_scheduler()

    try:
        from .graph import close_driver
        close_driver()
    except Exception:
        pass

    logger.info("Worker stopped")


if __name__ == "__main__":
    main()
