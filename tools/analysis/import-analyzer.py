#!/usr/bin/env python3
"""
Tool Name: import-analyzer.py
Purpose: Analyze import dependencies, detect circular imports, and find unused imports
Security: Command injection prevention, input validation, safe subprocess patterns

Usage:
    ./import-analyzer.py <file_or_directory>

Example:
    ./import-analyzer.py /path/to/file.py
    ./import-analyzer.py src/

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import ast
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timezone
from collections import defaultdict

# Tool metadata
TOOL_NAME = "import-analyzer"
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


def extract_imports(file_path: Path) -> Dict[str, Any]:
    """
    Extract import statements from a Python file

    Args:
        file_path: Path to Python file

    Returns:
        dict: Imports and usage information
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))

        imports = []
        imported_names = set()

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'name': name,
                        'line': node.lineno
                    })
                    imported_names.add(name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'name': name,
                        'line': node.lineno
                    })
                    imported_names.add(name)

        # Check which imports are actually used
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                # Check if this name is an imported name
                if node.id in imported_names:
                    used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Check if base is an imported module
                if isinstance(node.value, ast.Name) and node.value.id in imported_names:
                    used_names.add(node.value.id)

        # Determine unused imports
        unused_imports = []
        for imp in imports:
            if imp['name'] not in used_names:
                unused_imports.append(imp)

        return {
            'file': str(file_path),
            'imports': imports,
            'unused_imports': unused_imports
        }

    except SyntaxError as e:
        raise ValueError(f"Python syntax error in {file_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to analyze {file_path}: {e}")


def build_dependency_graph(files_data: List[Dict[str, Any]], base_path: Path) -> Dict[str, Set[str]]:
    """
    Build dependency graph from import data

    Args:
        files_data: List of file import data
        base_path: Base directory path

    Returns:
        dict: Adjacency list representing dependencies
    """
    graph = defaultdict(set)

    # Create mapping of module names to file paths
    module_to_file = {}

    for file_data in files_data:
        file_path = Path(file_data['file'])

        # Convert file path to module name
        try:
            rel_path = file_path.relative_to(base_path)
            module_name = str(rel_path.with_suffix('')).replace('/', '.')
            module_to_file[module_name] = str(file_path)
        except ValueError:
            # File not relative to base_path
            continue

    # Build graph
    for file_data in files_data:
        file_path = file_data['file']

        for imp in file_data['imports']:
            # Check if import is a local module
            module = imp['module']

            # Try to resolve relative imports
            for mod_name, mod_file in module_to_file.items():
                if module == mod_name or module.startswith(mod_name + '.'):
                    graph[file_path].add(mod_file)
                    break

    return graph


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detect circular dependencies using DFS

    Args:
        graph: Adjacency list of dependencies

    Returns:
        list: List of cycles (each cycle is a list of file paths)
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> bool:
        """DFS helper to detect cycles"""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    # Run DFS from each node
    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


def analyze_target(target: str) -> Dict[str, Any]:
    """
    Analyze imports for file or directory

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
        if path.suffix == '.py':
            files_to_analyze.append(path)
        else:
            raise ValueError("File must be a Python (.py) file")
    elif path.is_dir():
        # Find all Python files
        files_to_analyze.extend(path.rglob('*.py'))

        # Filter out hidden files and directories
        files_to_analyze = [
            f for f in files_to_analyze
            if not any(part.startswith('.') for part in f.parts)
        ]
    else:
        raise ValueError(f"Path is neither file nor directory: {target}")

    if not files_to_analyze:
        raise ValueError("No Python files found")

    # Analyze each file
    files_data = []
    all_unused_imports = []
    total_imports = 0

    for file_path in files_to_analyze:
        try:
            file_data = extract_imports(file_path)
            files_data.append(file_data)

            total_imports += len(file_data['imports'])

            if file_data['unused_imports']:
                for imp in file_data['unused_imports']:
                    all_unused_imports.append({
                        'file': file_data['file'],
                        'import': imp['name'],
                        'module': imp['module'],
                        'line': imp['line']
                    })
        except Exception:
            # Skip files that can't be analyzed
            continue

    if not files_data:
        raise ValueError("No files could be analyzed")

    # Build dependency graph and detect cycles
    base_path = path if path.is_dir() else path.parent
    graph = build_dependency_graph(files_data, base_path)
    circular_imports = detect_cycles(graph)

    # Format circular imports for output
    circular_import_details = []
    for cycle in circular_imports:
        circular_import_details.append({
            'cycle': cycle,
            'length': len(cycle) - 1  # Subtract 1 because last element repeats first
        })

    return {
        'total_files': len(files_data),
        'total_imports': total_imports,
        'unused_imports_count': len(all_unused_imports),
        'circular_imports_count': len(circular_imports),
        'circular_imports': circular_import_details,
        'unused_imports': all_unused_imports[:20]  # Limit to first 20 for readability
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
