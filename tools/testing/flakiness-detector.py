#!/usr/bin/env python3
"""
Tool Name: flakiness-detector.py
Purpose: Identify flaky tests from test history (JUnit XML, pytest JSON)
Security: Path validation, safe XML parsing, no command execution

Usage:
    ./flakiness-detector.py <test_results_dir> [--threshold=30]

Example:
    ./flakiness-detector.py test-results/
    ./flakiness-detector.py junit-reports/ --threshold=20

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

# Tool metadata
TOOL_NAME = "flakiness-detector"
TOOL_VERSION = "1.0.0"

# Default flakiness threshold (percentage)
DEFAULT_THRESHOLD = 30.0


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


def parse_junit_xml(xml_file: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse JUnit XML test results

    Args:
        xml_file: Path to JUnit XML file

    Returns:
        dict: Test results keyed by test name
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        test_results = {}

        # Handle both <testsuite> and <testsuites> root elements
        testsuites = root.findall('.//testsuite')
        if not testsuites:
            testsuites = [root] if root.tag == 'testsuite' else []

        for testsuite in testsuites:
            suite_name = testsuite.get('name', 'unknown')

            for testcase in testsuite.findall('.//testcase'):
                classname = testcase.get('classname', '')
                name = testcase.get('name', '')
                test_id = f"{classname}::{name}" if classname else name

                # Determine test status
                failure = testcase.find('failure')
                error = testcase.find('error')
                skipped = testcase.find('skipped')

                if failure is not None or error is not None:
                    status = 'failed'
                elif skipped is not None:
                    status = 'skipped'
                else:
                    status = 'passed'

                test_results[test_id] = {
                    'test': name,
                    'file': classname,
                    'status': status,
                    'suite': suite_name
                }

        return test_results

    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format in {xml_file.name}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to parse JUnit XML {xml_file.name}: {str(e)}")


def parse_pytest_json(json_file: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse pytest JSON test results

    Args:
        json_file: Path to pytest JSON file

    Returns:
        dict: Test results keyed by test name
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        test_results = {}

        # pytest-json-report format
        if 'tests' in data:
            for test in data['tests']:
                test_id = test.get('nodeid', '')
                outcome = test.get('outcome', 'unknown')

                # Map pytest outcomes to standard statuses
                status_map = {
                    'passed': 'passed',
                    'failed': 'failed',
                    'skipped': 'skipped',
                    'error': 'failed',
                    'xfailed': 'skipped',
                    'xpassed': 'passed'
                }
                status = status_map.get(outcome, 'unknown')

                test_results[test_id] = {
                    'test': test.get('name', test_id),
                    'file': test.get('filename', ''),
                    'status': status
                }

        return test_results

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in {json_file.name}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to parse pytest JSON {json_file.name}: {str(e)}")


def analyze_test_results(results_dir: Path, threshold: float) -> Dict[str, Any]:
    """
    Analyze test results to identify flaky tests

    Args:
        results_dir: Directory containing test result files
        threshold: Flakiness threshold percentage

    Returns:
        dict: Analysis results with flaky tests
    """
    # Collect all test results
    test_history = defaultdict(lambda: {'passed': 0, 'failed': 0, 'skipped': 0})

    xml_files = list(results_dir.glob('*.xml')) + list(results_dir.glob('**/*.xml'))
    json_files = list(results_dir.glob('*.json')) + list(results_dir.glob('**/*.json'))

    total_runs = 0

    # Parse XML files
    for xml_file in xml_files:
        try:
            results = parse_junit_xml(xml_file)
            total_runs += 1
            for test_id, test_data in results.items():
                status = test_data['status']
                test_history[test_id][status] += 1
                # Store metadata
                if 'test' not in test_history[test_id]:
                    test_history[test_id]['test'] = test_data['test']
                    test_history[test_id]['file'] = test_data['file']
        except Exception:
            # Skip files that can't be parsed
            continue

    # Parse JSON files
    for json_file in json_files:
        try:
            results = parse_pytest_json(json_file)
            total_runs += 1
            for test_id, test_data in results.items():
                status = test_data['status']
                test_history[test_id][status] += 1
                # Store metadata
                if 'test' not in test_history[test_id]:
                    test_history[test_id]['test'] = test_data['test']
                    test_history[test_id]['file'] = test_data['file']
        except Exception:
            # Skip files that can't be parsed
            continue

    if total_runs == 0:
        return {
            "total_tests_analyzed": 0,
            "flaky_tests": [],
            "analysis_period": f"0 runs",
            "note": "No valid test result files found"
        }

    # Identify flaky tests
    flaky_tests = []

    for test_id, history in test_history.items():
        passed = history['passed']
        failed = history['failed']
        skipped = history['skipped']
        total = passed + failed + skipped

        if total == 0:
            continue

        # Calculate flakiness: percentage of runs that failed
        # (excluding skipped tests from denominator)
        relevant_runs = passed + failed
        if relevant_runs > 1 and failed > 0:
            flakiness_score = (failed / relevant_runs) * 100

            # Only include if flakiness is above 0 but below 100
            # (not always failing, not always passing)
            if 0 < flakiness_score < 100 and flakiness_score >= threshold:
                flaky_tests.append({
                    "test": history.get('test', test_id),
                    "file": history.get('file', 'unknown'),
                    "runs": total,
                    "passed": passed,
                    "failures": failed,
                    "skipped": skipped,
                    "flakiness_score": round(flakiness_score, 2)
                })

    # Sort by flakiness score descending
    flaky_tests.sort(key=lambda x: x['flakiness_score'], reverse=True)

    return {
        "total_tests_analyzed": len(test_history),
        "total_runs_analyzed": total_runs,
        "flaky_tests": flaky_tests,
        "flaky_test_count": len(flaky_tests),
        "analysis_period": f"last {total_runs} runs",
        "threshold": threshold
    }


def parse_arguments(args: List[str]) -> tuple:
    """
    Parse command line arguments

    Args:
        args: Command line arguments

    Returns:
        tuple: (directory, threshold)
    """
    if len(args) < 2:
        raise ValueError("Missing required argument: test_results_directory")

    directory = args[1]
    threshold = DEFAULT_THRESHOLD

    # Parse optional threshold
    for arg in args[2:]:
        if arg.startswith('--threshold='):
            try:
                threshold = float(arg.split('=')[1])
                if not 0 <= threshold <= 100:
                    raise ValueError("Threshold must be between 0 and 100")
            except (ValueError, IndexError):
                raise ValueError("Invalid threshold format. Use --threshold=30")

    return directory, threshold


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
        # Parse arguments
        directory, threshold = parse_arguments(sys.argv)

        # Validate path
        if not validate_path(directory):
            raise ValueError(f"Invalid or inaccessible directory path: {directory}")

        results_dir = Path(directory).resolve()

        # Analyze test results
        results = analyze_test_results(results_dir, threshold)

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
