#!/usr/bin/env python3
"""
Tool Name: metrics-aggregator.py
Purpose: Aggregate time-series metrics and compute statistics
Security: Path validation, no command execution
Usage:
    ./metrics-aggregator.py <metrics_file> [--format csv|json] [--metric <name>]

Examples:
    ./metrics-aggregator.py metrics.csv
    ./metrics-aggregator.py metrics.json --format json --metric response_time
    ./metrics-aggregator.py data.csv --metric cpu_usage

Input Format (CSV):
    timestamp,response_time
    2025-11-06T10:00:00Z,100
    2025-11-06T10:01:00Z,150

Input Format (JSON):
    [
        {"timestamp": "2025-11-06T10:00:00Z", "response_time": 100},
        {"timestamp": "2025-11-06T10:01:00Z", "response_time": 150}
    ]
"""

import json
import sys
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
from statistics import mean, median, stdev
import argparse

# Security: Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# macOS system paths that should be blocked
BLOCKED_PATHS = [
    "/System/", "/Library/", "/private/etc/", "/private/var/log/", "/usr/", "/bin/", "/sbin/",
    "/Applications/", "/Volumes/"
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


def percentile(data: List[float], p: float) -> float:
    """
    Calculate percentile of data

    Args:
        data: Sorted list of values
        p: Percentile (0-100)

    Returns:
        Percentile value
    """
    if not data:
        return 0.0

    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1

    if c >= len(sorted_data):
        return sorted_data[-1]

    d0 = sorted_data[f]
    d1 = sorted_data[c]

    return d0 + (d1 - d0) * (k - f)


def detect_anomalies(values: List[float], threshold: float = 2.0) -> List[Tuple[int, float]]:
    """
    Detect anomalies using standard deviation

    Args:
        values: List of metric values
        threshold: Number of standard deviations (default: 2.0)

    Returns:
        List of (index, value) tuples for anomalous points
    """
    if len(values) < 3:
        return []

    avg = mean(values)
    std = stdev(values)

    if std == 0:
        return []

    anomalies = []
    for i, value in enumerate(values):
        z_score = abs(value - avg) / std
        if z_score > threshold:
            anomalies.append((i, value))

    return anomalies


def parse_csv_metrics(file_path: str, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse metrics from CSV file

    Args:
        file_path: Path to CSV file
        metric_name: Optional specific metric to extract

    Returns:
        List of metric entries
    """
    metrics = []

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Validate headers
        if not reader.fieldnames:
            raise ValueError("CSV file has no headers")

        timestamp_field = None
        for field in ['timestamp', 'time', 'date', 'datetime']:
            if field in reader.fieldnames:
                timestamp_field = field
                break

        if not timestamp_field:
            raise ValueError("CSV must have a timestamp column (timestamp, time, date, or datetime)")

        # Determine metric field
        metric_field = metric_name
        if not metric_field:
            # Use first non-timestamp numeric column
            for field in reader.fieldnames:
                if field != timestamp_field:
                    metric_field = field
                    break

        if not metric_field:
            raise ValueError("No metric column found in CSV")

        # Parse rows
        for row in reader:
            try:
                timestamp = row.get(timestamp_field, "")
                value_str = row.get(metric_field, "")

                if not value_str:
                    continue

                value = float(value_str)

                metrics.append({
                    "timestamp": timestamp,
                    "value": value,
                    "metric": metric_field
                })
            except (ValueError, KeyError):
                continue

    return metrics


def parse_json_metrics(file_path: str, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse metrics from JSON file

    Args:
        file_path: Path to JSON file
        metric_name: Optional specific metric to extract

    Returns:
        List of metric entries
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must contain an array of metric objects")

    metrics = []

    for entry in data:
        if not isinstance(entry, dict):
            continue

        # Find timestamp field
        timestamp = entry.get("timestamp") or entry.get("time") or entry.get("date") or entry.get("@timestamp")

        # Find metric value
        if metric_name:
            value = entry.get(metric_name)
            metric_field = metric_name
        else:
            # Use first numeric field that's not timestamp
            value = None
            metric_field = None
            for key, val in entry.items():
                if key not in ["timestamp", "time", "date", "@timestamp", "datetime"]:
                    try:
                        value = float(val)
                        metric_field = key
                        break
                    except (ValueError, TypeError):
                        continue

        if value is not None and metric_field:
            metrics.append({
                "timestamp": timestamp,
                "value": value,
                "metric": metric_field
            })

    return metrics


def aggregate_metrics(
    file_path: str,
    file_format: str = "csv",
    metric_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggregate metrics and compute statistics

    Args:
        file_path: Path to metrics file
        file_format: File format (csv or json)
        metric_name: Optional specific metric to analyze

    Returns:
        Aggregated statistics
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        raise ValueError(error)

    # Parse metrics
    if file_format == "csv":
        metrics = parse_csv_metrics(file_path, metric_name)
    elif file_format == "json":
        metrics = parse_json_metrics(file_path, metric_name)
    else:
        raise ValueError(f"Unsupported format: {file_format}")

    if not metrics:
        raise ValueError("No valid metrics found in file")

    # Extract values
    values = [m["value"] for m in metrics]
    metric_field = metrics[0]["metric"]

    # Calculate statistics
    if len(values) < 2:
        raise ValueError("Need at least 2 data points for statistical analysis")

    stats = {
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "p50": round(percentile(values, 50), 2),
        "p95": round(percentile(values, 95), 2),
        "p99": round(percentile(values, 99), 2),
    }

    # Add standard deviation if possible
    if len(values) >= 2:
        stats["stddev"] = round(stdev(values), 2)

    # Detect anomalies
    anomaly_indices = detect_anomalies(values)
    anomalies = []
    for idx, value in anomaly_indices:
        anomaly = {
            "index": idx,
            "value": value,
            "timestamp": metrics[idx]["timestamp"]
        }
        anomalies.append(anomaly)

    # Determine period (from first and last timestamp)
    first_ts = metrics[0]["timestamp"]
    last_ts = metrics[-1]["timestamp"]
    period = f"{first_ts} to {last_ts}" if first_ts and last_ts else "unknown"

    return {
        "metric": metric_field,
        "period": period,
        "count": len(values),
        "statistics": stats,
        "anomalies": anomalies[:20],  # Limit to top 20 anomalies
        "anomaly_count": len(anomalies)
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Aggregate time-series metrics and compute statistics")
    parser.add_argument("file_path", help="Path to metrics file (CSV or JSON)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="File format")
    parser.add_argument("--metric", help="Specific metric name to analyze (optional)")

    try:
        args = parser.parse_args()

        data = aggregate_metrics(
            file_path=args.file_path,
            file_format=args.format,
            metric_name=args.metric
        )

        output = {
            "success": True,
            "data": data,
            "errors": [],
            "metadata": {
                "tool": "metrics-aggregator",
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
                "tool": "metrics-aggregator",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat() + "Z"
            }
        }

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()
