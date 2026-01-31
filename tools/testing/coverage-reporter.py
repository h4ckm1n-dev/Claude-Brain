#!/usr/bin/env python3
"""
Tool Name: coverage-reporter.py
Purpose: Parse coverage reports (Cobertura XML and LCOV) and generate JSON summaries
Security: Path validation, safe XML parsing, no command execution

Usage:
    ./coverage-reporter.py <coverage_file>

Example:
    ./coverage-reporter.py coverage.xml
    ./coverage-reporter.py lcov.info

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# Tool metadata
TOOL_NAME = "coverage-reporter"
TOOL_VERSION = "1.0.0"


def validate_path(path: str) -> bool:
    """
    Validate file path to prevent directory traversal attacks

    Args:
        path: File path to validate

    Returns:
        bool: True if path is valid and safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()

        # Check path exists
        if not resolved.exists():
            return False

        # Check it's a file
        if not resolved.is_file():
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


def parse_cobertura_xml(file_path: Path) -> Dict[str, Any]:
    """
    Parse Cobertura XML coverage report

    Args:
        file_path: Path to coverage.xml file

    Returns:
        dict: Coverage data with overall and per-file metrics
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Get overall line and branch coverage
        line_rate = float(root.get('line-rate', 0))
        branch_rate = float(root.get('branch-rate', 0))

        overall_coverage = line_rate * 100
        branch_coverage = branch_rate * 100

        # Parse file-level coverage
        files_coverage = []
        total_lines = 0
        covered_lines = 0

        for package in root.findall('.//package'):
            for cls in package.findall('.//class'):
                filename = cls.get('filename', '')
                cls_line_rate = float(cls.get('line-rate', 0))
                file_coverage = cls_line_rate * 100

                # Collect uncovered lines
                uncovered_lines = []
                for line in cls.findall('.//line'):
                    line_num = int(line.get('number', 0))
                    hits = int(line.get('hits', 0))
                    if hits == 0:
                        uncovered_lines.append(line_num)

                # Count lines
                lines = cls.findall('.//line')
                file_total_lines = len(lines)
                file_covered_lines = sum(1 for l in lines if int(l.get('hits', 0)) > 0)

                total_lines += file_total_lines
                covered_lines += file_covered_lines

                if filename:
                    files_coverage.append({
                        "file": filename,
                        "coverage": round(file_coverage, 2),
                        "uncovered_lines": sorted(uncovered_lines),
                        "total_lines": file_total_lines,
                        "covered_lines": file_covered_lines
                    })

        return {
            "overall_coverage": round(overall_coverage, 2),
            "line_coverage": round(overall_coverage, 2),
            "branch_coverage": round(branch_coverage, 2),
            "files": files_coverage,
            "total_lines": total_lines,
            "covered_lines": covered_lines
        }

    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to parse Cobertura XML: {str(e)}")


def parse_lcov_info(file_path: Path) -> Dict[str, Any]:
    """
    Parse LCOV info coverage report

    Args:
        file_path: Path to lcov.info file

    Returns:
        dict: Coverage data with overall and per-file metrics
    """
    try:
        content = file_path.read_text()
        lines = content.strip().split('\n')

        files_coverage = []
        current_file = None
        current_file_data = {}
        total_lines = 0
        covered_lines = 0
        total_branches = 0
        covered_branches = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('SF:'):
                # Start of file section
                current_file = line[3:]
                current_file_data = {
                    'file': current_file,
                    'line_data': {},
                    'uncovered_lines': []
                }

            elif line.startswith('DA:'):
                # Line data: DA:line_number,hit_count
                parts = line[3:].split(',')
                if len(parts) >= 2:
                    line_num = int(parts[0])
                    hits = int(parts[1])
                    current_file_data['line_data'][line_num] = hits
                    if hits == 0:
                        current_file_data['uncovered_lines'].append(line_num)

            elif line.startswith('LF:'):
                # Lines found
                current_file_data['total_lines'] = int(line[3:])

            elif line.startswith('LH:'):
                # Lines hit
                current_file_data['covered_lines'] = int(line[3:])

            elif line.startswith('BRF:'):
                # Branches found
                current_file_data['total_branches'] = int(line[4:])

            elif line.startswith('BRH:'):
                # Branches hit
                current_file_data['covered_branches'] = int(line[4:])

            elif line == 'end_of_record' and current_file:
                # End of file section
                file_total = current_file_data.get('total_lines', 0)
                file_covered = current_file_data.get('covered_lines', 0)
                file_coverage = (file_covered / file_total * 100) if file_total > 0 else 0

                files_coverage.append({
                    "file": current_file_data['file'],
                    "coverage": round(file_coverage, 2),
                    "uncovered_lines": sorted(current_file_data['uncovered_lines']),
                    "total_lines": file_total,
                    "covered_lines": file_covered
                })

                total_lines += file_total
                covered_lines += file_covered
                total_branches += current_file_data.get('total_branches', 0)
                covered_branches += current_file_data.get('covered_branches', 0)

                current_file = None
                current_file_data = {}

        # Calculate overall coverage
        overall_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0
        branch_coverage = (covered_branches / total_branches * 100) if total_branches > 0 else 0

        return {
            "overall_coverage": round(overall_coverage, 2),
            "line_coverage": round(overall_coverage, 2),
            "branch_coverage": round(branch_coverage, 2),
            "files": files_coverage,
            "total_lines": total_lines,
            "covered_lines": covered_lines
        }

    except Exception as e:
        raise RuntimeError(f"Failed to parse LCOV info: {str(e)}")


def detect_format(file_path: Path) -> str:
    """
    Detect coverage file format

    Args:
        file_path: Path to coverage file

    Returns:
        str: 'xml' or 'lcov'
    """
    try:
        # Check if it's XML
        content_start = file_path.read_text()[:200]
        if content_start.strip().startswith('<?xml') or '<coverage' in content_start:
            return 'xml'
        elif 'SF:' in content_start or 'TN:' in content_start:
            return 'lcov'
        else:
            raise ValueError("Unknown coverage format (expected Cobertura XML or LCOV)")
    except Exception as e:
        raise ValueError(f"Cannot detect coverage format: {str(e)}")


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
        # Validate arguments
        if len(sys.argv) < 2:
            raise ValueError("Missing required argument: coverage_file")

        coverage_file = sys.argv[1]

        # Validate path
        if not validate_path(coverage_file):
            raise ValueError(f"Invalid or inaccessible file path: {coverage_file}")

        file_path = Path(coverage_file).resolve()

        # Detect format
        format_type = detect_format(file_path)

        # Parse based on format
        if format_type == 'xml':
            results = parse_cobertura_xml(file_path)
        else:  # lcov
            results = parse_lcov_info(file_path)

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
