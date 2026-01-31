"""Process and job management for background tasks."""

import os
import sys
import subprocess
import signal
import psutil
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Paths
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
LOGS_DIR = Path.home() / ".claude/memory/logs"


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    """Information about a job execution."""
    job_id: str
    script_name: str
    args: List[str]
    status: JobStatus
    started_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    pid: Optional[int] = None


class ProcessManager:
    """
    Manages background processes and script execution.

    Features:
    - Process detection (find running watcher)
    - Process control (start/stop watcher)
    - Job execution (run scripts with tracking)
    - Log access (read/clear log files)
    """

    def __init__(self):
        """Initialize process manager."""
        self.jobs: Dict[str, JobInfo] = {}
        self.jobs_lock = threading.Lock()

    # ============================================================
    # WATCHER PROCESS MANAGEMENT
    # ============================================================

    def get_watcher_status(self) -> Dict:
        """
        Check if file watcher is running.

        Returns:
            Dict with keys:
                - running: bool
                - pid: int (if running)
                - started_at: str ISO timestamp (if running)
                - last_activity: str (last log line)
        """
        try:
            # Iterate all processes to find watch_documents.py
            for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'watch_documents.py' in cmdline:
                        # Found the watcher process
                        started_at = datetime.fromtimestamp(
                            proc.info['create_time']
                        ).isoformat()

                        # Get last activity from log
                        last_activity = self._get_last_log_line("watcher.log")

                        return {
                            "running": True,
                            "pid": proc.info['pid'],
                            "started_at": started_at,
                            "last_activity": last_activity
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Not found
            return {
                "running": False,
                "pid": None,
                "started_at": None,
                "last_activity": None
            }

        except Exception as e:
            logger.error(f"Error checking watcher status: {e}")
            return {
                "running": False,
                "pid": None,
                "error": str(e)
            }

    def start_watcher(self, interval: int = 30) -> Dict:
        """
        Start the file watcher daemon.

        Args:
            interval: Check interval in seconds (10-300)

        Returns:
            Dict with success status and PID

        Raises:
            ValueError: If watcher already running
        """
        # Check if already running
        status = self.get_watcher_status()
        if status['running']:
            raise ValueError(f"Watcher already running (PID {status['pid']})")

        try:
            # Build command
            script_path = SCRIPTS_DIR / "watch_documents.py"
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")

            # Start process in background with nohup
            cmd = [
                sys.executable,
                str(script_path),
                f"--interval={interval}",
                "--quiet"
            ]

            # Use subprocess.Popen to start in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )

            logger.info(f"Started watcher with PID {process.pid}")

            return {
                "success": True,
                "pid": process.pid,
                "interval": interval
            }

        except Exception as e:
            logger.error(f"Error starting watcher: {e}")
            raise

    def stop_watcher(self) -> Dict:
        """
        Stop the file watcher daemon.

        Returns:
            Dict with success status

        Raises:
            ValueError: If watcher not running
        """
        # Find watcher process
        status = self.get_watcher_status()
        if not status['running']:
            raise ValueError("Watcher is not running")

        pid = status['pid']

        try:
            # Send SIGTERM
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to watcher (PID {pid})")

            return {
                "success": True,
                "pid": pid,
                "signal": "SIGTERM"
            }

        except ProcessLookupError:
            raise ValueError("Process not found (may have already stopped)")
        except Exception as e:
            logger.error(f"Error stopping watcher: {e}")
            raise

    # ============================================================
    # SCRIPT EXECUTION & JOB TRACKING
    # ============================================================

    def execute_script(self, script_name: str, args: List[str]) -> str:
        """
        Execute a script and track as a job.

        Args:
            script_name: Script filename (without .py/.sh)
            args: CLI arguments

        Returns:
            job_id: UUID for tracking

        Raises:
            FileNotFoundError: If script doesn't exist
            ValueError: If duplicate job already running
        """
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Check for duplicate running jobs
        with self.jobs_lock:
            for job in self.jobs.values():
                if (job.script_name == script_name and
                    job.status == JobStatus.RUNNING):
                    raise ValueError(f"Script '{script_name}' already running")

        # Find script path
        script_path = self._find_script(script_name)
        if not script_path:
            raise FileNotFoundError(f"Script not found: {script_name}")

        # Create job info
        job = JobInfo(
            job_id=job_id,
            script_name=script_name,
            args=args,
            status=JobStatus.PENDING,
            started_at=datetime.now().isoformat()
        )

        with self.jobs_lock:
            self.jobs[job_id] = job

        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_job,
            args=(job_id, script_path, args),
            daemon=True
        )
        thread.start()

        logger.info(f"Started job {job_id}: {script_name} {args}")

        return job_id

    def _execute_job(self, job_id: str, script_path: Path, args: List[str]):
        """
        Execute job in background thread.

        Args:
            job_id: Job UUID
            script_path: Full path to script
            args: CLI arguments
        """
        job = self.jobs[job_id]

        try:
            # Update status to RUNNING
            job.status = JobStatus.RUNNING

            # Build command
            if script_path.suffix == '.py':
                cmd = [sys.executable, str(script_path)] + args
            elif script_path.suffix == '.sh':
                cmd = ['bash', str(script_path)] + args
            else:
                raise ValueError(f"Unsupported script type: {script_path.suffix}")

            # Execute with output capture
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            job.pid = process.pid

            # Wait for completion (blocking in background thread)
            stdout, stderr = process.communicate()

            # Update job with result
            if process.returncode == 0:
                job.status = JobStatus.COMPLETED
                job.result = {
                    "stdout": stdout[-5000:] if stdout else "",  # Last 5KB
                    "stderr": stderr[-5000:] if stderr else "",
                    "returncode": 0
                }
                logger.info(f"Job {job_id} completed successfully")
            else:
                job.status = JobStatus.FAILED
                job.error = stderr or stdout or f"Exit code {process.returncode}"
                logger.error(f"Job {job_id} failed: {job.error}")

            job.completed_at = datetime.now().isoformat()
            job.pid = None

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()
            job.pid = None
            logger.error(f"Job {job_id} exception: {e}")

    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job status by ID.

        Args:
            job_id: Job UUID

        Returns:
            JobInfo or None if not found
        """
        with self.jobs_lock:
            return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[JobInfo]:
        """
        List recent jobs (most recent first).

        Args:
            limit: Maximum jobs to return

        Returns:
            List of JobInfo sorted by start time descending
        """
        with self.jobs_lock:
            jobs = list(self.jobs.values())

        # Sort by started_at descending
        jobs.sort(key=lambda j: j.started_at, reverse=True)

        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job UUID

        Returns:
            True if cancelled, False if not found or not running
        """
        job = self.get_job_status(job_id)

        if not job:
            return False

        if job.status != JobStatus.RUNNING or not job.pid:
            return False

        try:
            # Kill process
            os.kill(job.pid, signal.SIGTERM)
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now().isoformat()
            job.pid = None
            logger.info(f"Cancelled job {job_id}")
            return True

        except ProcessLookupError:
            logger.warning(f"Job {job_id} process not found")
            return False
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    # ============================================================
    # LOG FILE ACCESS
    # ============================================================

    def read_log(self, log_name: str, lines: int = 50) -> Dict:
        """
        Read last N lines from a log file.

        Args:
            log_name: Log name (watcher, consolidation, document-watcher)
            lines: Number of lines to read

        Returns:
            Dict with keys:
                - exists: bool
                - lines: List[str]
                - size_bytes: int
        """
        # Map log name to filename
        log_files = {
            "watcher": "watcher.log",
            "consolidation": "consolidation.log",
            "document-watcher": "document-watcher.log"
        }

        if log_name not in log_files:
            raise ValueError(f"Invalid log name: {log_name}")

        log_path = LOGS_DIR / log_files[log_name]

        if not log_path.exists():
            return {
                "exists": False,
                "lines": [],
                "size_bytes": 0,
                "message": f"Log file not found: {log_path}"
            }

        try:
            # Get file size
            size_bytes = log_path.stat().st_size

            # Read last N lines efficiently
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read all lines (could optimize with tail for large files)
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            return {
                "exists": True,
                "lines": [line.rstrip('\n') for line in last_lines],
                "size_bytes": size_bytes,
                "total_lines": len(all_lines)
            }

        except Exception as e:
            logger.error(f"Error reading log {log_name}: {e}")
            return {
                "exists": True,
                "lines": [],
                "size_bytes": 0,
                "error": str(e)
            }

    def clear_log(self, log_name: str) -> bool:
        """
        Clear (truncate) a log file.

        Args:
            log_name: Log name

        Returns:
            True if cleared successfully
        """
        log_files = {
            "watcher": "watcher.log",
            "consolidation": "consolidation.log",
            "document-watcher": "document-watcher.log"
        }

        if log_name not in log_files:
            raise ValueError(f"Invalid log name: {log_name}")

        log_path = LOGS_DIR / log_files[log_name]

        try:
            # Truncate file
            with open(log_path, 'w') as f:
                pass

            logger.info(f"Cleared log file: {log_path}")
            return True

        except FileNotFoundError:
            # File doesn't exist, consider it cleared
            return True
        except Exception as e:
            logger.error(f"Error clearing log {log_name}: {e}")
            return False

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _find_script(self, script_name: str) -> Optional[Path]:
        """
        Find script by name in scripts directory.

        Args:
            script_name: Script name (with or without extension)

        Returns:
            Full path to script or None
        """
        # Try with .py extension
        script_path = SCRIPTS_DIR / f"{script_name}.py"
        if script_path.exists():
            return script_path

        # Try with .sh extension
        script_path = SCRIPTS_DIR / f"{script_name}.sh"
        if script_path.exists():
            return script_path

        # Try exact name
        script_path = SCRIPTS_DIR / script_name
        if script_path.exists():
            return script_path

        return None

    def _get_last_log_line(self, log_filename: str) -> Optional[str]:
        """
        Get last line from a log file.

        Args:
            log_filename: Log filename

        Returns:
            Last line or None
        """
        log_path = LOGS_DIR / log_filename

        try:
            if not log_path.exists():
                return None

            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                if lines:
                    return lines[-1].strip()

            return None

        except Exception:
            return None
