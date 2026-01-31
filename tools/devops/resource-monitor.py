#!/usr/bin/env python3
"""
Tool Name: resource-monitor.py
Purpose: Monitor CPU, memory, and disk usage
Security: Safe process monitoring, input validation
Usage:
    # Monitor system resources
    ./resource-monitor.py

    # Monitor specific process
    ./resource-monitor.py --pid 1234

    # Monitor process by name
    ./resource-monitor.py --process-name python

    # Include per-CPU stats
    ./resource-monitor.py --per-cpu
"""

import json
import sys
import argparse
import os
from typing import Dict, Any, Optional, List

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_system_resources(per_cpu: bool = False) -> Dict[str, Any]:
    """Get system-wide resource usage"""
    if not PSUTIL_AVAILABLE:
        raise RuntimeError("psutil not installed. Install with: pip install psutil")

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)

    cpu_data = {
        "percent": cpu_percent,
        "count_logical": cpu_count,
        "count_physical": cpu_count_physical
    }

    if per_cpu:
        cpu_data["per_cpu_percent"] = psutil.cpu_percent(interval=1, percpu=True)

    # Memory usage
    memory = psutil.virtual_memory()
    memory_data = {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "percent": memory.percent,
        "total_gb": round(memory.total / (1024**3), 2),
        "available_gb": round(memory.available / (1024**3), 2),
        "used_gb": round(memory.used / (1024**3), 2)
    }

    # Swap usage
    swap = psutil.swap_memory()
    swap_data = {
        "total_bytes": swap.total,
        "used_bytes": swap.used,
        "percent": swap.percent,
        "total_gb": round(swap.total / (1024**3), 2),
        "used_gb": round(swap.used / (1024**3), 2)
    }

    # Disk usage (root partition)
    disk = psutil.disk_usage('/')
    disk_data = {
        "total_bytes": disk.total,
        "used_bytes": disk.used,
        "free_bytes": disk.free,
        "percent": disk.percent,
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2)
    }

    return {
        "cpu": cpu_data,
        "memory": memory_data,
        "swap": swap_data,
        "disk": disk_data
    }


def get_process_resources(pid: int) -> Dict[str, Any]:
    """Get resource usage for specific process"""
    if not PSUTIL_AVAILABLE:
        raise RuntimeError("psutil not installed. Install with: pip install psutil")

    try:
        process = psutil.Process(pid)

        # Process info
        with process.oneshot():
            cpu_percent = process.cpu_percent(interval=1)
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            status = process.status()
            name = process.name()
            cmdline = process.cmdline()

        return {
            "pid": pid,
            "name": name,
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_bytes": memory_info.rss,
            "memory_mb": round(memory_info.rss / (1024**2), 2),
            "memory_percent": round(memory_percent, 2),
            "cmdline": " ".join(cmdline) if cmdline else ""
        }

    except psutil.NoSuchProcess:
        raise ValueError(f"Process with PID {pid} not found")
    except psutil.AccessDenied:
        raise PermissionError(f"Access denied to process {pid}")


def find_processes_by_name(name: str) -> List[Dict[str, Any]]:
    """Find processes by name"""
    if not PSUTIL_AVAILABLE:
        raise RuntimeError("psutil not installed. Install with: pip install psutil")

    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            if name.lower() in proc.info['name'].lower():
                # Get detailed info for matching process
                with proc.oneshot():
                    memory_info = proc.memory_info()
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.cpu_percent(interval=0.1),
                        "memory_bytes": memory_info.rss,
                        "memory_mb": round(memory_info.rss / (1024**2), 2),
                        "memory_percent": round(proc.memory_percent(), 2)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes


def validate_pid(pid: int) -> bool:
    """Validate PID is positive integer"""
    return isinstance(pid, int) and pid > 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Monitor CPU, memory, and disk usage"
    )
    parser.add_argument(
        "--pid",
        type=int,
        help="Monitor specific process by PID"
    )
    parser.add_argument(
        "--process-name",
        help="Monitor processes by name (searches for matching names)"
    )
    parser.add_argument(
        "--per-cpu",
        action="store_true",
        help="Include per-CPU statistics"
    )

    args = parser.parse_args()

    try:
        if not PSUTIL_AVAILABLE:
            raise RuntimeError(
                "psutil library not installed. Install with: pip install psutil"
            )

        data = {}

        # Get system resources
        if not args.pid and not args.process_name:
            data = get_system_resources(per_cpu=args.per_cpu)

        # Get process-specific resources
        elif args.pid:
            if not validate_pid(args.pid):
                raise ValueError(f"Invalid PID: {args.pid}")

            data = {
                "system": get_system_resources(per_cpu=False),
                "process": get_process_resources(args.pid)
            }

        elif args.process_name:
            processes = find_processes_by_name(args.process_name)
            if not processes:
                raise ValueError(f"No processes found matching: {args.process_name}")

            data = {
                "system": get_system_resources(per_cpu=False),
                "processes": processes,
                "process_count": len(processes)
            }

        output = {
            "success": True,
            "data": data,
            "errors": [],
            "metadata": {
                "tool": "resource-monitor",
                "version": "1.0.0"
            }
        }

        print(json.dumps(output, indent=2))
        sys.exit(0)

    except Exception as e:
        output = {
            "success": False,
            "data": None,
            "errors": [{"type": type(e).__name__, "message": str(e)}],
            "metadata": {
                "tool": "resource-monitor",
                "version": "1.0.0"
            }
        }
        print(json.dumps(output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
