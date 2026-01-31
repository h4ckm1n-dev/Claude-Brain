#!/usr/bin/env python3
"""
Tool Name: type-coverage.py
Purpose: Measure type annotation coverage for Python and TypeScript files
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./type-coverage.py <file_or_directory>

Example:
    ./type-coverage.py /path/to/file.py
    ./type-coverage.py src/

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

# Tool metadata
TOOL_NAME = "type-coverage"
TOOL_VERSION = "1.0.0"


def validate_path(path: str) -> bool:
    """
    Validate file or directory path to prevent directory traversal attacks

    Args:
        path: File or directory path to validate

    Returns:
        bool: True if path is valid and safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()

        # Check path exists
        if not resolved.exists():
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


def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze type coverage for a Python file

    Args:
        file_path: Path to Python file

    Returns:
        dict: Type coverage statistics
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))

        total_functions = 0
        typed_functions = 0
        total_params = 0
        typed_params = 0
        functions_with_return = 0
        functions_with_typed_return = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip magic methods for cleaner stats
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue

                total_functions += 1

                # Check function parameters
                func_typed = True
                for arg in node.args.args:
                    # Skip 'self' and 'cls'
                    if arg.arg in ['self', 'cls']:
                        continue

                    total_params += 1
                    if arg.annotation is not None:
                        typed_params += 1
                    else:
                        func_typed = False

                # Check return type
                if node.returns is not None:
                    functions_with_typed_return += 1
                else:
                    func_typed = False

                # Check if function likely returns something (has return statement)
                has_return = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None:
                        has_return = True
                        break

                if has_return:
                    functions_with_return += 1

                # Count function as typed if all params and return are typed
                if func_typed and (total_params > 0 or has_return):
                    typed_functions += 1

        # Calculate coverage percentages
        func_coverage = (typed_functions / total_functions * 100) if total_functions > 0 else 100.0
        param_coverage = (typed_params / total_params * 100) if total_params > 0 else 100.0
        return_coverage = (functions_with_typed_return / functions_with_return * 100) if functions_with_return > 0 else 100.0

        return {
            'file': str(file_path),
            'total_functions': total_functions,
            'typed_functions': typed_functions,
            'coverage_pct': round(func_coverage, 1),
            'details': {
                'total_params': total_params,
                'typed_params': typed_params,
                'param_coverage_pct': round(param_coverage, 1),
                'functions_with_return': functions_with_return,
                'typed_returns': functions_with_typed_return,
                'return_coverage_pct': round(return_coverage, 1)
            }
        }

    except SyntaxError as e:
        raise ValueError(f"Python syntax error in {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to analyze {file_path}: {e}")


def analyze_typescript_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze type coverage for a TypeScript file (simplified)

    Args:
        file_path: Path to TypeScript file

    Returns:
        dict: Type coverage statistics
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        # Simple regex-based analysis (not as accurate as AST, but functional)

        # Find function declarations
        # Matches: function name(...): type, const name = (...): type =>, etc.
        function_pattern = r'(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))'
        typed_function_pattern = r'(?:function\s+\w+\([^)]*\)\s*:\s*\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*:\s*\w+\s*=>)'

        # Find parameter declarations
        param_pattern = r'\(\s*([^)]+)\s*\)'
        typed_param_pattern = r'\w+\s*:\s*\w+'

        functions = re.findall(function_pattern, source)
        typed_functions = re.findall(typed_function_pattern, source)

        total_functions = len(functions)
        typed_func_count = len(typed_functions)

        # Count parameters
        total_params = 0
        typed_params = 0

        for match in re.finditer(param_pattern, source):
            params_str = match.group(1)
            if params_str.strip():
                params = [p.strip() for p in params_str.split(',')]
                total_params += len(params)
                typed_params += len([p for p in params if ':' in p])

        # Calculate coverage
        func_coverage = (typed_func_count / total_functions * 100) if total_functions > 0 else 100.0
        param_coverage = (typed_params / total_params * 100) if total_params > 0 else 100.0

        return {
            'file': str(file_path),
            'total_functions': total_functions,
            'typed_functions': typed_func_count,
            'coverage_pct': round(func_coverage, 1),
            'details': {
                'total_params': total_params,
                'typed_params': typed_params,
                'param_coverage_pct': round(param_coverage, 1)
            }
        }

    except Exception as e:
        raise RuntimeError(f"Failed to analyze {file_path}: {e}")


def analyze_target(target: str) -> Dict[str, Any]:
    """
    Analyze type coverage for file or directory

    Args:
        target: Path to file or directory

    Returns:
        dict: Analysis results

    Raises:
        ValueError: If target validation fails
    """
    # Validate target
    if not validate_path(target):
        raise ValueError(f"Invalid or unsafe path: {target}")

    path = Path(target).resolve()

    files_to_analyze = []

    if path.is_file():
        files_to_analyze.append(path)
    elif path.is_dir():
        # Find all Python and TypeScript files
        files_to_analyze.extend(path.rglob('*.py'))
        files_to_analyze.extend(path.rglob('*.ts'))
        files_to_analyze.extend(path.rglob('*.tsx'))

        # Filter out hidden files and directories
        files_to_analyze = [
            f for f in files_to_analyze
            if not any(part.startswith('.') for part in f.parts)
        ]
    else:
        raise ValueError(f"Path is neither file nor directory: {target}")

    if not files_to_analyze:
        raise ValueError("No Python or TypeScript files found")

    # Analyze each file
    file_results = []
    total_functions = 0
    total_typed_functions = 0

    for file_path in files_to_analyze:
        try:
            suffix = file_path.suffix.lower()

            if suffix == '.py':
                result = analyze_python_file(file_path)
            elif suffix in ['.ts', '.tsx']:
                result = analyze_typescript_file(file_path)
            else:
                continue

            file_results.append(result)
            total_functions += result['total_functions']
            total_typed_functions += result['typed_functions']

        except Exception:
            # Skip files that can't be analyzed
            continue

    if not file_results:
        raise ValueError("No files could be analyzed")

    # Calculate overall coverage
    overall_coverage = (total_typed_functions / total_functions * 100) if total_functions > 0 else 100.0

    # Sort files by coverage (lowest first - needs attention)
    file_results.sort(key=lambda x: x['coverage_pct'])

    return {
        'total_files': len(file_results),
        'total_functions': total_functions,
        'typed_functions': total_typed_functions,
        'coverage_pct': round(overall_coverage, 1),
        'files': file_results
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
        target = sys.argv[1]

        # Perform analysis
        results = analyze_target(target)

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
