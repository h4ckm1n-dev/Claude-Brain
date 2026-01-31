#!/usr/bin/env python3
"""
Tool Name: permission-auditor.py
Purpose: Audit file permissions for security issues
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./permission-auditor.py <directory>

Example:
    ./permission-auditor.py /path/to/codebase
    ./permission-auditor.py . --recursive

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import os
import stat
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Tool metadata
TOOL_NAME = "permission-auditor"
TOOL_VERSION = "1.0.0"

# Dangerous permission masks
DANGEROUS_PERMISSIONS = {
    'world_writable': 0o002,      # Others can write
    'world_readable': 0o004,      # Others can read (warning for sensitive files)
    'world_executable': 0o001,    # Others can execute
    'group_writable': 0o020,      # Group can write
    'setuid': stat.S_ISUID,       # Setuid bit
    'setgid': stat.S_ISGID,       # Setgid bit
    'sticky': stat.S_ISVTX,       # Sticky bit
}

# Files/directories that should never be world-writable
SENSITIVE_PATTERNS = [
    '.env', '.key', '.pem', '.crt', '.ssh', 'password', 'secret',
    'credentials', 'token', 'private'
]


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


def is_sensitive_file(file_path: Path) -> bool:
    """
    Check if file is sensitive based on name patterns

    Args:
        file_path: Path to check

    Returns:
        bool: True if file is considered sensitive
    """
    filename = file_path.name.lower()
    return any(pattern in filename for pattern in SENSITIVE_PATTERNS)


def format_permissions(mode: int) -> str:
    """
    Format file permissions as rwxrwxrwx string

    Args:
        mode: File mode bits

    Returns:
        str: Formatted permission string
    """
    perms = []

    # Owner permissions
    perms.append('r' if mode & stat.S_IRUSR else '-')
    perms.append('w' if mode & stat.S_IWUSR else '-')
    perms.append('x' if mode & stat.S_IXUSR else '-')

    # Group permissions
    perms.append('r' if mode & stat.S_IRGRP else '-')
    perms.append('w' if mode & stat.S_IWGRP else '-')
    perms.append('x' if mode & stat.S_IXGRP else '-')

    # Other permissions
    perms.append('r' if mode & stat.S_IROTH else '-')
    perms.append('w' if mode & stat.S_IWOTH else '-')
    perms.append('x' if mode & stat.S_IXOTH else '-')

    return ''.join(perms)


def check_file_permissions(file_path: Path) -> List[Dict[str, Any]]:
    """
    Check file for permission issues

    Args:
        file_path: Path to file to check

    Returns:
        list: List of permission issues found
    """
    issues = []

    try:
        # Get file stats
        file_stat = file_path.stat()
        mode = file_stat.st_mode
        perms = stat.S_IMODE(mode)

        # Check for world-writable (777, 666)
        if perms & DANGEROUS_PERMISSIONS['world_writable']:
            issues.append({
                'file': str(file_path),
                'issue': 'world_writable',
                'severity': 'high',
                'permissions': format_permissions(perms),
                'octal': oct(perms),
                'description': 'File is world-writable (anyone can modify)'
            })

        # Check for 777 (full access to everyone)
        if perms == 0o777:
            issues.append({
                'file': str(file_path),
                'issue': 'full_access',
                'severity': 'critical',
                'permissions': format_permissions(perms),
                'octal': oct(perms),
                'description': 'File has 777 permissions (full access to everyone)'
            })

        # Check for 666 (read-write for everyone)
        if perms == 0o666:
            issues.append({
                'file': str(file_path),
                'issue': 'read_write_all',
                'severity': 'high',
                'permissions': format_permissions(perms),
                'octal': oct(perms),
                'description': 'File has 666 permissions (read-write for everyone)'
            })

        # Check for setuid/setgid on executables
        if mode & stat.S_IXUSR:  # If executable
            if mode & DANGEROUS_PERMISSIONS['setuid']:
                issues.append({
                    'file': str(file_path),
                    'issue': 'setuid',
                    'severity': 'high',
                    'permissions': format_permissions(perms),
                    'octal': oct(perms),
                    'description': 'Setuid bit set on executable (runs with owner privileges)'
                })

            if mode & DANGEROUS_PERMISSIONS['setgid']:
                issues.append({
                    'file': str(file_path),
                    'issue': 'setgid',
                    'severity': 'medium',
                    'permissions': format_permissions(perms),
                    'octal': oct(perms),
                    'description': 'Setgid bit set on executable (runs with group privileges)'
                })

        # Check sensitive files for world-readable
        if is_sensitive_file(file_path):
            if perms & DANGEROUS_PERMISSIONS['world_readable']:
                issues.append({
                    'file': str(file_path),
                    'issue': 'sensitive_world_readable',
                    'severity': 'high',
                    'permissions': format_permissions(perms),
                    'octal': oct(perms),
                    'description': 'Sensitive file is world-readable'
                })

            if perms & DANGEROUS_PERMISSIONS['group_writable']:
                issues.append({
                    'file': str(file_path),
                    'issue': 'sensitive_group_writable',
                    'severity': 'medium',
                    'permissions': format_permissions(perms),
                    'octal': oct(perms),
                    'description': 'Sensitive file is group-writable'
                })

    except Exception:
        # Skip files that can't be accessed
        pass

    return issues


def audit_directory(directory: str) -> Dict[str, Any]:
    """
    Recursively audit directory for permission issues

    Args:
        directory: Directory path to audit

    Returns:
        dict: Audit results with issues and statistics

    Raises:
        ValueError: If directory validation fails
    """
    # Validate directory
    if not validate_path(directory):
        raise ValueError(f"Invalid or unsafe directory path: {directory}")

    dir_path = Path(directory).resolve()
    all_issues = []
    scanned_files = 0
    skipped_files = 0

    # Recursively scan all files
    for file_path in dir_path.rglob('*'):
        if file_path.is_file():
            # Skip hidden files in hidden directories
            try:
                if any(part.startswith('.') and part != '.' for part in file_path.parts):
                    skipped_files += 1
                    continue
            except Exception:
                skipped_files += 1
                continue

            # Check permissions
            issues = check_file_permissions(file_path)
            all_issues.extend(issues)
            scanned_files += 1

    # Count files with issues
    files_with_issues = len(set(issue['file'] for issue in all_issues))

    # Count by severity
    severity_counts = {
        'critical': len([i for i in all_issues if i['severity'] == 'critical']),
        'high': len([i for i in all_issues if i['severity'] == 'high']),
        'medium': len([i for i in all_issues if i['severity'] == 'medium']),
        'low': len([i for i in all_issues if i['severity'] == 'low']),
    }

    # Create summary
    total_issues = len(all_issues)
    if total_issues == 0:
        summary = "No permission issues found"
    else:
        summary = f"Found {total_issues} permission issue(s) in {files_with_issues} file(s)"

    return {
        'scanned_files': scanned_files,
        'skipped_files': skipped_files,
        'total_issues': total_issues,
        'files_with_issues': files_with_issues,
        'severity_counts': severity_counts,
        'issues': all_issues,
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

        # Perform audit
        results = audit_directory(directory)

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
