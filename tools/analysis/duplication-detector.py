#!/usr/bin/env python3
"""
Tool Name: duplication-detector.py
Purpose: Find duplicate code blocks in a directory
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./duplication-detector.py <directory> [min_lines]

Example:
    ./duplication-detector.py /path/to/codebase
    ./duplication-detector.py src/ 10

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
from collections import defaultdict
import subprocess

# Tool metadata
TOOL_NAME = "duplication-detector"
TOOL_VERSION = "1.0.0"

# Default minimum lines for duplication
DEFAULT_MIN_LINES = 5

# Source file extensions to scan
SOURCE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.c', '.cpp', '.go', '.rb', '.php'}


def validate_path(path: str) -> bool:
    """
    Validate directory path to prevent directory traversal attacks

    Args:
        path: Directory path to validate

    Returns:
        bool: True if path is valid and safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()

        # Check path exists
        if not resolved.exists():
            return False

        # Check it's a directory
        if not resolved.is_dir():
            return False

        # Prevent access to sensitive system directories
        # Note: On macOS, /etc -> /private/etc
        sensitive_dirs = ['/etc', '/sys', '/proc', '/dev', '/root', '/boot',
                         '/private/etc', '/System', '/Library']
        path_str = str(resolved)

        # Check if path is within any sensitive directory
        for sensitive in sensitive_dirs:
            if path_str.startswith(sensitive + '/'):
                return False

        return True
    except Exception:
        return False


def validate_numeric(value: str, min_val: int = 1, max_val: int = 1000) -> bool:
    """
    Validate numeric input

    Args:
        value: String to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        bool: True if valid number in range
    """
    try:
        num = int(value)
        return min_val <= num <= max_val
    except ValueError:
        return False


def try_jscpd(directory: Path, min_lines: int) -> Dict[str, Any]:
    """
    Try to use jscpd for duplicate detection

    Args:
        directory: Directory to scan
        min_lines: Minimum lines for duplication

    Returns:
        dict: jscpd results or None if not available

    Raises:
        RuntimeError: If jscpd execution fails
    """
    try:
        # Check if jscpd is available
        result = subprocess.run(
            ['jscpd', '--version'],
            capture_output=True,
            shell=False,
            timeout=5,
            check=False
        )

        if result.returncode != 0:
            return None

        # Run jscpd
        result = subprocess.run(
            ['jscpd', str(directory), '--min-lines', str(min_lines), '--format', 'json'],
            capture_output=True,
            text=True,
            shell=False,
            timeout=60,
            check=False
        )

        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return {
                'method': 'jscpd',
                'result': data
            }

        return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None
    except Exception:
        return None


def hash_based_detection(directory: Path, min_lines: int) -> Dict[str, Any]:
    """
    Fallback hash-based duplicate detection

    Args:
        directory: Directory to scan
        min_lines: Minimum lines for duplication

    Returns:
        dict: Duplicate detection results
    """
    # Find all source files
    files_to_scan = []

    for ext in SOURCE_EXTENSIONS:
        files_to_scan.extend(directory.rglob(f'*{ext}'))

    # Filter out hidden files
    files_to_scan = [
        f for f in files_to_scan
        if not any(part.startswith('.') for part in f.parts)
    ]

    # Store hashes of code blocks
    hash_locations = defaultdict(list)
    total_files = len(files_to_scan)

    for file_path in files_to_scan:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Sliding window of min_lines
            for start_idx in range(len(lines) - min_lines + 1):
                window = lines[start_idx:start_idx + min_lines]

                # Normalize: strip whitespace for better matching
                normalized = [line.strip() for line in window]
                block_text = '\n'.join(normalized)

                # Skip if block is mostly empty
                if len(block_text.strip()) < 20:
                    continue

                # Hash the block
                block_hash = hashlib.md5(block_text.encode('utf-8')).hexdigest()

                # Store location
                location = {
                    'file': str(file_path),
                    'line': start_idx + 1
                }
                hash_locations[block_hash].append(location)

        except Exception:
            # Skip files that can't be read
            continue

    # Find duplicates (blocks that appear more than once)
    duplicates = []

    for block_hash, locations in hash_locations.items():
        if len(locations) > 1:
            duplicates.append({
                'hash': block_hash,
                'occurrences': len(locations),
                'locations': locations
            })

    # Sort by occurrences (most duplicated first)
    duplicates.sort(key=lambda x: x['occurrences'], reverse=True)

    return {
        'total_files': total_files,
        'min_lines': min_lines,
        'duplicates_count': len(duplicates),
        'duplicates': duplicates[:50]  # Limit to top 50 for readability
    }


def analyze_directory(directory: str, min_lines: int) -> Dict[str, Any]:
    """
    Analyze directory for code duplicates

    Args:
        directory: Directory path to analyze
        min_lines: Minimum lines for duplicate detection

    Returns:
        dict: Analysis results

    Raises:
        ValueError: If directory validation fails
    """
    # Validate directory
    if not validate_path(directory):
        raise ValueError(f"Invalid or unsafe directory path: {directory}")

    dir_path = Path(directory).resolve()

    # Try jscpd first
    jscpd_result = try_jscpd(dir_path, min_lines)

    if jscpd_result is not None:
        return jscpd_result

    # Fall back to hash-based detection
    return hash_based_detection(dir_path, min_lines)


def create_output(success: bool, data: Any = None, errors: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create standardized JSON output

    Args:
        success: Whether operation succeeded
        data: Result data (if successful)
        errors: List of error dictionaries (if failed)

    Returns:
        dict: Standardized output structure
    """
    return {
        "success": success,
        "data": data if data is not None else {},
        "errors": errors if errors is not None else [],
        "metadata": {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        }
    }


def main():
    """Main entry point with error handling"""

    # Help text
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    try:
        # Parse arguments
        directory = sys.argv[1]
        min_lines = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MIN_LINES

        # Validate min_lines
        if not validate_numeric(str(min_lines)):
            raise ValueError(f"min_lines must be between 1 and 1000, got: {min_lines}")

        # Perform analysis
        results = analyze_directory(directory, min_lines)

        # Create success output
        output = create_output(success=True, data=results)

    except ValueError as e:
        # Input validation errors
        output = create_output(
            success=False,
            errors=[{"type": "ValidationError", "message": str(e)}]
        )
    except RuntimeError as e:
        # Operation errors
        output = create_output(
            success=False,
            errors=[{"type": "RuntimeError", "message": str(e)}]
        )
    except Exception as e:
        # Unexpected errors
        output = create_output(
            success=False,
            errors=[{"type": type(e).__name__, "message": str(e)}]
        )

    # Output JSON
    print(json.dumps(output, indent=2))

    # Exit with appropriate code
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()
