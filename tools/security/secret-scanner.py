#!/usr/bin/env python3
"""
Tool Name: secret-scanner.py
Purpose: Scan code for secrets (API keys, passwords, AWS keys, GitHub tokens, private keys)
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./secret-scanner.py <directory>

Example:
    ./secret-scanner.py /path/to/codebase
    ./secret-scanner.py . --recursive

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Tool metadata
TOOL_NAME = "secret-scanner"
TOOL_VERSION = "1.0.0"

# Secret detection patterns
SECRET_PATTERNS = {
    'api_key': r'api[_-]?key["\s:=]+["\']?([A-Za-z0-9_\-]{20,})',
    'password': r'password["\s:=]+["\']([^"\']{8,})["\']',
    'aws_key': r'AKIA[0-9A-Z]{16}',
    'github_token': r'ghp_[A-Za-z0-9]{36}',
    'private_key': r'-----BEGIN (RSA|PRIVATE) KEY-----',
    'generic_secret': r'secret["\s:=]+["\']([A-Za-z0-9_\-]{16,})["\']',
}

# File size limit (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
    '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.mp3', '.wav', '.flac', '.aac',
    '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.class', '.o',
}


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
        # Note: On macOS, /etc -> /private/etc, /tmp -> /private/tmp, /var -> /private/var
        sensitive_dirs = ['/etc', '/sys', '/proc', '/dev', '/root', '/boot',
                         '/private/etc', '/private/var', '/System', '/Library']
        path_str = str(resolved)

        # Check if path equals or starts with any sensitive directory
        for sensitive in sensitive_dirs:
            if path_str == sensitive or path_str.startswith(sensitive + '/'):
                return False

        return True
    except Exception:
        return False


def redact_secret(secret: str) -> str:
    """
    Redact secret showing only first and last 2 characters

    Args:
        secret: Secret string to redact

    Returns:
        str: Redacted secret (e.g., "AK***************XY")
    """
    if len(secret) <= 4:
        return '*' * len(secret)

    return f"{secret[:2]}{'*' * (len(secret) - 4)}{secret[-2:]}"


def is_binary_file(file_path: Path) -> bool:
    """
    Check if file is binary or should be skipped

    Args:
        file_path: Path to file

    Returns:
        bool: True if file should be skipped
    """
    # Check extension
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # Check file size
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return True
    except Exception:
        return True

    # Try to read first 8KB and check for null bytes
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                return True
    except Exception:
        return True

    return False


def scan_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Scan a single file for secrets

    Args:
        file_path: Path to file to scan

    Returns:
        list: List of findings with file, line, type, preview
    """
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, start=1):
                # Check each pattern
                for secret_type, pattern in SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # Get the full secret or the captured group
                        if match.groups():
                            secret = match.group(1)
                        else:
                            secret = match.group(0)

                        # Redact the secret
                        redacted = redact_secret(secret)

                        # Create preview with redacted secret
                        preview = line.strip()[:100]  # Limit preview length
                        preview = preview.replace(secret, redacted)

                        findings.append({
                            'file': str(file_path),
                            'line': line_num,
                            'type': secret_type,
                            'preview': preview
                        })

    except Exception:
        # Skip files that can't be read
        pass

    return findings


def scan_directory(directory: str) -> Dict[str, Any]:
    """
    Recursively scan directory for secrets

    Args:
        directory: Directory path to scan

    Returns:
        dict: Scan results with findings and statistics

    Raises:
        ValueError: If directory validation fails
    """
    # Validate directory
    if not validate_path(directory):
        raise ValueError(f"Invalid or unsafe directory path: {directory}")

    dir_path = Path(directory).resolve()
    all_findings = []
    scanned_files = 0
    skipped_files = 0

    # Recursively scan all files
    for file_path in dir_path.rglob('*'):
        if file_path.is_file():
            # Skip binary files and large files
            if is_binary_file(file_path):
                skipped_files += 1
                continue

            # Skip hidden files and directories
            if any(part.startswith('.') for part in file_path.parts):
                skipped_files += 1
                continue

            # Scan the file
            findings = scan_file(file_path)
            all_findings.extend(findings)
            scanned_files += 1

    # Count files with findings
    files_with_secrets = len(set(f['file'] for f in all_findings))

    # Create summary
    summary = f"Found {len(all_findings)} potential secret(s) in {files_with_secrets} file(s)"
    if scanned_files == 0:
        summary = "No files to scan"

    return {
        'scanned_files': scanned_files,
        'skipped_files': skipped_files,
        'findings': all_findings,
        'summary': summary
    }


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
            "timestamp": datetime.utcnow().isoformat() + "Z"
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

        # Perform scan
        results = scan_directory(directory)

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
