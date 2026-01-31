#!/usr/bin/env python3
"""
Tool Name: log-analyzer.py
Purpose: Parse logs, extract error patterns, compute metrics
Security: Path validation, no command execution, file size limits
Usage:
    ./log-analyzer.py <log_file> [--format apache|json|plain] [--level ERROR|WARN|INFO|DEBUG]

Examples:
    ./log-analyzer.py /var/log/app.log
    ./log-analyzer.py /var/log/access.log --format apache
    ./log-analyzer.py /var/log/json.log --format json --level ERROR
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
from collections import Counter, defaultdict
import argparse

# Security: Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# macOS system paths that should be blocked
BLOCKED_PATHS = [
    "/System/", "/Library/", "/private/etc/", "/private/var/log/", "/usr/", "/bin/", "/sbin/",
    "/Applications/", "/Volumes/"
]

# Log level patterns
LOG_LEVELS = {
    "ERROR": r"ERROR|FATAL|SEVERE|Exception|exception",
    "WARN": r"WARN|WARNING|Warn",
    "INFO": r"INFO|Information",
    "DEBUG": r"DEBUG|TRACE"
}

# Common timestamp patterns
TIMESTAMP_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",  # ISO 8601
    r"\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}",  # Apache
    r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",  # Common format
    r"\[?\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\]?",  # Alternative format
]


def validate_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file path for security

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        resolved = Path(path).resolve()

        # Check if path exists
        if not resolved.exists():
            return False, f"Path does not exist: {path}"

        # Check if it's a file
        if not resolved.is_file():
            return False, f"Path is not a file: {path}"

        # Check for blocked system paths (macOS security)
        resolved_str = str(resolved)
        for blocked in BLOCKED_PATHS:
            if resolved_str.startswith(blocked):
                return False, f"Access denied to system path: {path}"

        # Check file size
        file_size = resolved.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"

        return True, None

    except Exception as e:
        return False, f"Path validation failed: {str(e)}"


def extract_timestamp(line: str) -> Optional[str]:
    """Extract timestamp from log line"""
    for pattern in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    return None


def parse_log_line(line: str, log_format: str = "plain") -> Dict[str, Any]:
    """
    Parse a single log line based on format

    Args:
        line: Log line to parse
        log_format: Format type (apache, json, plain)

    Returns:
        Parsed log entry
    """
    entry = {
        "raw": line.strip(),
        "timestamp": None,
        "level": "UNKNOWN",
        "message": line.strip()
    }

    if log_format == "json":
        try:
            parsed = json.loads(line)
            entry["timestamp"] = parsed.get("timestamp") or parsed.get("time") or parsed.get("@timestamp")
            entry["level"] = parsed.get("level") or parsed.get("severity", "UNKNOWN")
            entry["message"] = parsed.get("message") or parsed.get("msg") or str(parsed)
            return entry
        except json.JSONDecodeError:
            pass

    # Extract timestamp
    entry["timestamp"] = extract_timestamp(line)

    # Detect log level
    for level, pattern in LOG_LEVELS.items():
        if re.search(pattern, line, re.IGNORECASE):
            entry["level"] = level
            break


    # Extract message (remove timestamp and log level)
    message = line.strip()
    if entry["timestamp"]:
        message = message.replace(entry["timestamp"], "").strip()
    for level in LOG_LEVELS.keys():
        message = re.sub(rf'\b{level}\b', '', message, flags=re.IGNORECASE).strip()
    entry["message"] = message

    return entry



def extract_error_pattern(message: str) -> str:
    """
    Extract generic error pattern from specific error message

    Examples:
        "Database connection failed: timeout after 30s" -> "Database connection failed"
        "User 12345 not found" -> "User not found"
    """
    # Remove specific details
    pattern = re.sub(r'\b\d+\b', '', message)  # Remove numbers
    pattern = re.sub(r'[0-9a-f]{8,}', '', pattern)  # Remove hashes/IDs
    pattern = re.sub(r'\b[A-Z0-9]{20,}\b', '', pattern)  # Remove tokens
    pattern = re.sub(r'\s+', ' ', pattern).strip()  # Normalize whitespace

    # Truncate at first colon or newline
    if ':' in pattern:
        pattern = pattern.split(':')[0].strip()
    if '\n' in pattern:
        pattern = pattern.split('\n')[0].strip()

    return pattern or message


def analyze_logs(
    file_path: str,
    log_format: str = "plain",
    min_level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze log file and extract metrics

    Args:
        file_path: Path to log file
        log_format: Log format (apache, json, plain)
        min_level: Minimum log level to include

    Returns:
        Analysis results
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        raise ValueError(error)

    # Level hierarchy for filtering
    level_priority = {"ERROR": 0, "WARN": 1, "INFO": 2, "DEBUG": 3, "UNKNOWN": 4}
    min_priority = level_priority.get(min_level, 4) if min_level else 4

    # Metrics
    total_lines = 0
    level_counts = Counter()
    error_patterns = defaultdict(lambda: {"count": 0, "first_seen": None, "last_seen": None, "examples": []})

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            total_lines += 1

            # Skip empty lines
            if not line.strip():
                continue

            # Parse log line
            entry = parse_log_line(line, log_format)
            level = entry["level"]

            # Count by level
            level_counts[level] += 1

            # Filter by level
            if level_priority.get(level, 4) > min_priority:
                continue

            # Extract error patterns for ERROR and WARN
            if level in ["ERROR", "WARN"]:
                pattern = extract_error_pattern(entry["message"])
                error_patterns[pattern]["count"] += 1

                # Track timestamps
                timestamp = entry["timestamp"]
                if timestamp:
                    if not error_patterns[pattern]["first_seen"]:
                        error_patterns[pattern]["first_seen"] = timestamp
                    error_patterns[pattern]["last_seen"] = timestamp

                # Store example (max 3)
                if len(error_patterns[pattern]["examples"]) < 3:
                    error_patterns[pattern]["examples"].append(entry["message"][:200])

    # Sort error patterns by count
    sorted_patterns = sorted(
        [{"pattern": k, **v} for k, v in error_patterns.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    # Get top errors (aggregated by pattern)
    top_errors = [
        {
            "message": p["pattern"],
            "count": p["count"],
            "first_seen": p["first_seen"],
            "last_seen": p["last_seen"]
        }
        for p in sorted_patterns[:10]
    ]

    return {
        "total_lines": total_lines,
        "errors": level_counts.get("ERROR", 0),
        "warnings": level_counts.get("WARN", 0),
        "info": level_counts.get("INFO", 0),
        "debug": level_counts.get("DEBUG", 0),
        "unknown": level_counts.get("UNKNOWN", 0),
        "error_patterns": sorted_patterns[:20],  # Top 20 patterns
        "top_errors": top_errors
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Analyze log files for error patterns and metrics")
    parser.add_argument("file_path", help="Path to log file")
    parser.add_argument("--format", choices=["apache", "json", "plain"], default="plain", help="Log format")
    parser.add_argument("--level", choices=["ERROR", "WARN", "INFO", "DEBUG"], help="Minimum log level to analyze")

    try:
        args = parser.parse_args()

        data = analyze_logs(
            file_path=args.file_path,
            log_format=args.format,
            min_level=args.level
        )

        output = {
            "success": True,
            "data": data,
            "errors": [],
            "metadata": {
                "tool": "log-analyzer",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat() + "Z"
            }
        }

    except Exception as e:
        output = {
            "success": False,
            "data": None,
            "errors": [{"type": type(e).__name__, "message": str(e)}],
            "metadata": {
                "tool": "log-analyzer",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat() + "Z"
            }
        }

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()
