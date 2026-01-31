#!/usr/bin/env python3
"""
Tool Name: test-selector.py
Purpose: Select tests to run based on git diff (changed files)
Security: Safe git execution with subprocess, path validation, no shell=True

Usage:
    ./test-selector.py [<directory>]

Example:
    ./test-selector.py
    ./test-selector.py /path/to/repo

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

# Tool metadata
TOOL_NAME = "test-selector"
TOOL_VERSION = "1.0.0"

# Test file patterns for different languages
TEST_PATTERNS = {
    'python': ['test_*.py', '*_test.py'],
    'javascript': ['*.test.js', '*.spec.js'],
    'typescript': ['*.test.ts', '*.spec.ts', '*.test.tsx', '*.spec.tsx'],
    'go': ['*_test.go'],
    'java': ['*Test.java'],
    'ruby': ['*_spec.rb', '*_test.rb'],
}

# Common test directory names
TEST_DIRECTORIES = ['tests', 'test', '__tests__', 'spec', 'specs']


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

        # Prevent access to sensitive system directories (macOS-aware)
        sensitive_dirs = ['/etc', '/sys', '/proc', '/dev', '/root', '/boot',
                         '/private/etc', '/System', '/Library']
        path_str = str(resolved)

        for sensitive in sensitive_dirs:
            if path_str.startswith(sensitive + '/'):
                return False

        return True
    except Exception:
        return False


def is_git_repository(directory: Path) -> bool:
    """
    Check if directory is a git repository

    Args:
        directory: Directory to check

    Returns:
        bool: True if directory is a git repo
    """
    try:
        result = subprocess.run(
            ['git', '-C', str(directory), 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            shell=False,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def get_changed_files(directory: Path) -> List[str]:
    """
    Get list of changed files using git diff

    Args:
        directory: Git repository directory

    Returns:
        list: Changed file paths relative to repo root
    """
    try:
        # Get uncommitted changes
        result = subprocess.run(
            ['git', '-C', str(directory), 'diff', '--name-only', 'HEAD'],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            timeout=10
        )

        if result.returncode != 0:
            # No HEAD (new repo) or other error - get all tracked files
            result = subprocess.run(
                ['git', '-C', str(directory), 'ls-files'],
                capture_output=True,
                text=True,
                shell=False,
                check=False,
                timeout=10
            )

        if result.returncode == 0 and result.stdout:
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

        return []
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git command timed out")
    except Exception as e:
        raise RuntimeError(f"Failed to get changed files: {str(e)}")


def find_test_files(directory: Path, patterns: List[str]) -> Set[Path]:
    """
    Find all test files matching patterns in directory

    Args:
        directory: Directory to search
        patterns: List of glob patterns to match

    Returns:
        set: Set of test file paths
    """
    test_files = set()

    for test_dir in TEST_DIRECTORIES:
        test_path = directory / test_dir
        if test_path.exists() and test_path.is_dir():
            # Search for test files in test directory
            for pattern in patterns:
                test_files.update(test_path.rglob(pattern))

    return test_files


def map_source_to_tests(source_file: str, directory: Path) -> List[str]:
    """
    Map a source file to its potential test files

    Args:
        source_file: Source file path (relative to repo root)
        directory: Repository root directory

    Returns:
        list: Potential test file paths
    """
    source_path = Path(source_file)
    filename = source_path.stem  # filename without extension
    extension = source_path.suffix

    # Determine test patterns based on file extension
    test_patterns_to_use = []
    if extension == '.py':
        test_patterns_to_use = TEST_PATTERNS['python']
    elif extension in ['.js', '.jsx']:
        test_patterns_to_use = TEST_PATTERNS['javascript']
    elif extension in ['.ts', '.tsx']:
        test_patterns_to_use = TEST_PATTERNS['typescript']
    elif extension == '.go':
        test_patterns_to_use = TEST_PATTERNS['go']
    elif extension == '.java':
        test_patterns_to_use = TEST_PATTERNS['java']
    elif extension == '.rb':
        test_patterns_to_use = TEST_PATTERNS['ruby']

    if not test_patterns_to_use:
        return []

    # Find all test files
    all_test_files = find_test_files(directory, test_patterns_to_use)

    # Find tests that might correspond to this source file
    potential_tests = []
    filename_lower = filename.lower()

    for test_file in all_test_files:
        test_name_lower = test_file.stem.lower()

        # Check if test file name contains source file name
        if filename_lower in test_name_lower or test_name_lower in filename_lower:
            potential_tests.append(str(test_file.relative_to(directory)))

    return potential_tests


def select_tests(directory: Path) -> Dict[str, Any]:
    """
    Select tests based on changed files

    Args:
        directory: Git repository directory

    Returns:
        dict: Changed files and corresponding tests
    """
    # Get changed files
    changed_files = get_changed_files(directory)

    if not changed_files:
        return {
            "changed_files": [],
            "tests_to_run": [],
            "total_tests": 0,
            "note": "No changed files detected"
        }

    # Map changed files to tests
    tests_to_run = set()
    for changed_file in changed_files:
        # Skip if it's already a test file
        is_test = any(
            changed_file.endswith(suffix)
            for patterns in TEST_PATTERNS.values()
            for pattern in patterns
            for suffix in [pattern.replace('*', '')]
        )

        if is_test:
            tests_to_run.add(changed_file)
        else:
            # Find corresponding test files
            related_tests = map_source_to_tests(changed_file, directory)
            tests_to_run.update(related_tests)

    return {
        "changed_files": changed_files,
        "tests_to_run": sorted(list(tests_to_run)),
        "total_tests": len(tests_to_run)
    }


def create_output(success: bool, data: Any = None, errors: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create standardized JSON output

    Args:
        success: Whether operation succeeded
        data: Result data
        errors: List of error objects

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
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    }


def main() -> None:
    """Main entry point with comprehensive error handling"""
    try:
        # Get directory from arguments or use current directory
        if len(sys.argv) >= 2:
            directory_path = sys.argv[1]
        else:
            directory_path = '.'

        # Validate path
        if not validate_path(directory_path):
            raise ValueError(f"Invalid or inaccessible directory path: {directory_path}")

        directory = Path(directory_path).resolve()

        # Check if git repository
        if not is_git_repository(directory):
            raise ValueError(f"Directory is not a git repository: {directory}")

        # Select tests
        results = select_tests(directory)

        # Success output
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

    # Always output JSON
    print(json.dumps(output, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()
