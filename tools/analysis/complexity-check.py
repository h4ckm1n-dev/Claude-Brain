#!/usr/bin/env python3
"""
Tool Name: complexity-check.py
Purpose: Analyze cyclomatic complexity and maintainability index for Python and JavaScript files
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./complexity-check.py <file_path>

Example:
    ./complexity-check.py /path/to/file.py
    ./complexity-check.py src/app.js

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import subprocess

# Tool metadata
TOOL_NAME = "complexity-check"
TOOL_VERSION = "1.0.0"

# Complexity grade thresholds (based on radon)
COMPLEXITY_GRADES = {
    'A': (1, 5),    # Simple
    'B': (6, 10),   # Well structured
    'C': (11, 20),  # Slightly complex
    'D': (21, 30),  # More complex
    'E': (31, 40),  # Complex
    'F': (41, float('inf'))  # Very complex
}


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


def get_complexity_grade(complexity: int) -> str:
    """
    Get complexity grade based on cyclomatic complexity score

    Args:
        complexity: Cyclomatic complexity number

    Returns:
        str: Grade (A-F)
    """
    for grade, (low, high) in COMPLEXITY_GRADES.items():
        if low <= complexity <= high:
            return grade
    return 'F'


def analyze_python_with_radon(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Use radon to analyze Python file complexity

    Args:
        file_path: Path to Python file

    Returns:
        dict: Analysis results or None if radon not available
    """
    try:
        # Try to use radon cc (cyclomatic complexity)
        result = subprocess.run(
            ['radon', 'cc', str(file_path), '-j'],
            capture_output=True,
            text=True,
            shell=False,  # CRITICAL: Prevents injection
            timeout=30,
            check=False
        )

        if result.returncode != 0:
            return None

        # Parse radon JSON output
        radon_data = json.loads(result.stdout)

        if not radon_data or str(file_path) not in radon_data:
            return None

        functions = []
        total_complexity = 0
        count = 0

        for item in radon_data[str(file_path)]:
            complexity = item.get('complexity', 0)
            total_complexity += complexity
            count += 1

            functions.append({
                'name': item.get('name', 'unknown'),
                'complexity': complexity,
                'grade': get_complexity_grade(complexity)
            })

        avg_complexity = total_complexity / count if count > 0 else 0

        return {
            'file': str(file_path),
            'average_complexity': round(avg_complexity, 2),
            'functions': functions,
            'grade': get_complexity_grade(int(avg_complexity))
        }

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None
    except Exception:
        return None


def calculate_python_complexity_manual(file_path: Path) -> Dict[str, Any]:
    """
    Manually calculate Python cyclomatic complexity using AST

    Args:
        file_path: Path to Python file

    Returns:
        dict: Analysis results
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Calculate complexity: count decision points + 1
                complexity = 1  # Base complexity

                for child in ast.walk(node):
                    # Decision points: if, for, while, and, or, except, with
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        # and/or operators
                        complexity += len(child.values) - 1
                    elif isinstance(child, (ast.With, ast.AsyncWith)):
                        complexity += 1

                functions.append({
                    'name': node.name,
                    'complexity': complexity,
                    'grade': get_complexity_grade(complexity)
                })

        if not functions:
            return {
                'file': str(file_path),
                'average_complexity': 0,
                'functions': [],
                'grade': 'A'
            }

        total_complexity = sum(f['complexity'] for f in functions)
        avg_complexity = total_complexity / len(functions)

        return {
            'file': str(file_path),
            'average_complexity': round(avg_complexity, 2),
            'functions': functions,
            'grade': get_complexity_grade(int(avg_complexity))
        }

    except SyntaxError as e:
        raise ValueError(f"Python syntax error in file: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to analyze Python file: {e}")


def calculate_javascript_complexity(file_path: Path) -> Dict[str, Any]:
    """
    Calculate JavaScript cyclomatic complexity (simplified)

    Args:
        file_path: Path to JavaScript file

    Returns:
        dict: Analysis results
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        # Simple regex-based complexity calculation for JavaScript
        # This is a simplified approach; full AST parsing would require js parser

        # Find function definitions
        function_pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))'
        functions_found = re.finditer(function_pattern, source)

        functions = []

        # Split by functions (rough approximation)
        for match in functions_found:
            func_name = match.group(1) or match.group(2) or 'anonymous'

            # Count decision points in a rough way
            # Find the function body (simplified - just look ahead)
            start_pos = match.end()

            # Look for next 500 chars (rough function body)
            body_sample = source[start_pos:start_pos + 500]

            complexity = 1
            # Count if, for, while, switch, &&, ||, ?, catch
            complexity += body_sample.count('if')
            complexity += body_sample.count('for')
            complexity += body_sample.count('while')
            complexity += body_sample.count('switch')
            complexity += body_sample.count('catch')
            complexity += body_sample.count('&&')
            complexity += body_sample.count('||')
            complexity += body_sample.count('?')  # Ternary

            functions.append({
                'name': func_name,
                'complexity': min(complexity, 50),  # Cap at 50 for rough estimate
                'grade': get_complexity_grade(complexity)
            })

        if not functions:
            # No functions found, analyze whole file
            complexity = 1
            complexity += source.count('if')
            complexity += source.count('for')
            complexity += source.count('while')
            complexity += source.count('switch')
            complexity += source.count('catch')

            return {
                'file': str(file_path),
                'average_complexity': complexity,
                'functions': [{'name': 'file', 'complexity': complexity, 'grade': get_complexity_grade(complexity)}],
                'grade': get_complexity_grade(complexity)
            }

        total_complexity = sum(f['complexity'] for f in functions)
        avg_complexity = total_complexity / len(functions)

        return {
            'file': str(file_path),
            'average_complexity': round(avg_complexity, 2),
            'functions': functions,
            'grade': get_complexity_grade(int(avg_complexity))
        }

    except Exception as e:
        raise RuntimeError(f"Failed to analyze JavaScript file: {e}")


def analyze_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze file complexity based on file type

    Args:
        file_path: Path to file to analyze

    Returns:
        dict: Analysis results

    Raises:
        ValueError: If file validation fails or unsupported file type
    """
    # Validate file
    if not validate_path(file_path):
        raise ValueError(f"Invalid or unsafe file path: {file_path}")

    path = Path(file_path).resolve()
    suffix = path.suffix.lower()

    # Check file type
    if suffix == '.py':
        # Try radon first, fall back to manual
        result = analyze_python_with_radon(path)
        if result is not None:
            return result
        return calculate_python_complexity_manual(path)

    elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
        return calculate_javascript_complexity(path)

    else:
        raise ValueError(f"Unsupported file type: {suffix}. Supports: .py, .js, .jsx, .ts, .tsx")


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
        file_path = sys.argv[1]

        # Perform analysis
        results = analyze_file(file_path)

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
