#!/usr/bin/env python3
"""
Tool Name: sql-explain.py
Purpose: Analyze SQL EXPLAIN plans and suggest optimizations
Security: No command execution, pattern-based analysis only
Usage:
    ./sql-explain.py <query_file> [--db postgres|mysql]
    ./sql-explain.py --query "SELECT * FROM users WHERE email = 'test@example.com'"

Examples:
    ./sql-explain.py query.sql
    ./sql-explain.py query.sql --db postgres
    ./sql-explain.py --query "SELECT * FROM users WHERE id > 1000" --db mysql
    echo "SELECT * FROM orders WHERE status = 'pending'" | ./sql-explain.py -
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
import argparse

# Security: Maximum file size (1MB)
MAX_FILE_SIZE = 1024 * 1024

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


def extract_tables_and_columns(query: str) -> Dict[str, List[str]]:
    """
    Extract table names and referenced columns from SQL query

    Returns:
        Dict mapping table names to list of columns used in WHERE/JOIN
    """
    tables = {}

    # Extract table names from FROM clause
    from_pattern = r'FROM\s+(\w+)'
    for match in re.finditer(from_pattern, query, re.IGNORECASE):
        table = match.group(1)
        if table.upper() not in ['SELECT', 'WHERE', 'ORDER', 'GROUP', 'HAVING']:
            tables[table] = []

    # Extract table names from JOIN clauses
    join_pattern = r'JOIN\s+(\w+)'
    for match in re.finditer(join_pattern, query, re.IGNORECASE):
        table = match.group(1)
        if table not in tables:
            tables[table] = []

    # Extract columns from WHERE clause
    where_pattern = r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)'
    where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
    if where_match:
        where_clause = where_match.group(1)

        # Find column references: table.column or column
        column_pattern = r'(\w+)\.(\w+)|(?:^|\s)(\w+)\s*[=<>]'
        for match in re.finditer(column_pattern, where_clause):
            if match.group(1) and match.group(2):
                # table.column format
                table, column = match.group(1), match.group(2)
                if table in tables:
                    tables[table].append(column)
            elif match.group(3):
                # column only - associate with first table
                column = match.group(3)
                if column.upper() not in ['AND', 'OR', 'NOT', 'IN', 'LIKE', 'IS', 'NULL']:
                    if tables:
                        first_table = list(tables.keys())[0]
                        tables[first_table].append(column)

    # Extract columns from JOIN ON conditions
    join_on_pattern = r'ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)'
    for match in re.finditer(join_on_pattern, query, re.IGNORECASE):
        table1, col1, table2, col2 = match.groups()
        if table1 in tables:
            tables[table1].append(col1)
        if table2 in tables:
            tables[table2].append(col2)

    # Deduplicate columns
    for table in tables:
        tables[table] = list(set(tables[table]))

    return tables


def analyze_query_patterns(query: str, db_type: str = "postgres") -> List[Dict[str, Any]]:
    """
    Analyze SQL query for common anti-patterns and optimization opportunities

    Args:
        query: SQL query string
        db_type: Database type (postgres or mysql)

    Returns:
        List of issues with severity and suggestions
    """
    issues = []

    # Normalize query for analysis
    query_upper = query.upper()

    # Issue 1: SELECT * detection
    if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
        issues.append({
            "severity": "medium",
            "issue": "SELECT * detected - fetching all columns",
            "suggestion": "Explicitly specify only the columns you need to reduce data transfer and improve performance",
            "example": "SELECT id, name, email FROM users instead of SELECT * FROM users"
        })

    # Issue 2: Missing WHERE clause
    if 'WHERE' not in query_upper and 'JOIN' not in query_upper:
        if any(word in query_upper for word in ['UPDATE', 'DELETE']):
            issues.append({
                "severity": "critical",
                "issue": "UPDATE/DELETE without WHERE clause - will affect all rows",
                "suggestion": "Always include a WHERE clause in UPDATE/DELETE statements",
                "example": "DELETE FROM users WHERE id = 1"
            })
        elif 'SELECT' in query_upper:
            issues.append({
                "severity": "high",
                "issue": "SELECT without WHERE clause - full table scan likely",
                "suggestion": "Add WHERE clause to filter rows and utilize indexes",
                "example": "SELECT * FROM users WHERE created_at > '2025-01-01'"
            })

    # Issue 3: OR in WHERE clause (often inefficient)
    if re.search(r'WHERE.*\bOR\b', query, re.IGNORECASE):
        issues.append({
            "severity": "medium",
            "issue": "OR condition in WHERE clause may prevent index usage",
            "suggestion": "Consider using UNION or separate queries, or ensure indexes cover OR conditions",
            "example": "Use UNION: SELECT * FROM users WHERE status = 'active' UNION SELECT * FROM users WHERE role = 'admin'"
        })

    # Issue 4: LIKE with leading wildcard
    if re.search(r"LIKE\s+['\"]%", query, re.IGNORECASE):
        issues.append({
            "severity": "high",
            "issue": "LIKE with leading wildcard (LIKE '%...') prevents index usage",
            "suggestion": "Avoid leading wildcards or use full-text search indexes",
            "example": "Use LIKE 'prefix%' or implement full-text search"
        })

    # Issue 5: NOT IN with subquery
    if re.search(r'NOT\s+IN\s*\(', query, re.IGNORECASE):
        issues.append({
            "severity": "medium",
            "issue": "NOT IN with subquery can be slow",
            "suggestion": "Use NOT EXISTS or LEFT JOIN with NULL check instead",
            "example": "SELECT * FROM users WHERE NOT EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)"
        })

    # Issue 6: Function on indexed column in WHERE
    function_on_column = r'WHERE\s+\w+\s*\([^)]*\w+\.\w+[^)]*\)\s*[=<>]'
    if re.search(function_on_column, query, re.IGNORECASE):
        issues.append({
            "severity": "high",
            "issue": "Function applied to column in WHERE clause prevents index usage",
            "suggestion": "Apply function to the comparison value instead, or use functional indexes",
            "example": "Instead of WHERE YEAR(created_at) = 2025, use WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'"
        })

    # Issue 7: ORDER BY without index
    order_by_pattern = r'ORDER\s+BY\s+(\w+(?:\.\w+)?)'
    order_match = re.search(order_by_pattern, query, re.IGNORECASE)
    if order_match and 'LIMIT' in query_upper:
        issues.append({
            "severity": "medium",
            "issue": "ORDER BY with LIMIT may require filesort without proper index",
            "suggestion": "Create index on ORDER BY column(s) to avoid sorting large result sets",
            "example": "CREATE INDEX idx_users_created_at ON users(created_at)"
        })

    return issues


def suggest_indexes(query: str, db_type: str = "postgres") -> List[str]:
    """
    Suggest indexes based on query patterns

    Args:
        query: SQL query string
        db_type: Database type (postgres or mysql)

    Returns:
        List of suggested CREATE INDEX statements
    """
    suggestions = []
    tables_cols = extract_tables_and_columns(query)

    for table, columns in tables_cols.items():
        if not columns:
            continue

        # Suggest index for WHERE clause columns
        if len(columns) == 1:
            col = columns[0]
            if db_type == "postgres":
                suggestions.append(f"CREATE INDEX idx_{table}_{col} ON {table}({col});")
            else:
                suggestions.append(f"CREATE INDEX idx_{table}_{col} ON {table}({col});")
        elif len(columns) > 1:
            # Suggest composite index
            cols_joined = "_".join(columns[:3])  # Limit to 3 columns
            cols_list = ", ".join(columns[:3])
            if db_type == "postgres":
                suggestions.append(f"CREATE INDEX idx_{table}_{cols_joined} ON {table}({cols_list});")
            else:
                suggestions.append(f"CREATE INDEX idx_{table}_{cols_joined} ON {table}({cols_list});")

    return suggestions


def analyze_sql(query: str, db_type: str = "postgres") -> Dict[str, Any]:
    """
    Analyze SQL query and provide optimization suggestions

    Args:
        query: SQL query string
        db_type: Database type (postgres or mysql)

    Returns:
        Analysis results with issues and recommendations
    """
    # Validate query
    if not query or not query.strip():
        raise ValueError("Empty query provided")

    # Security: Reject dangerous commands (this is analysis only, not execution)
    dangerous_patterns = [
        r';\s*DROP\s+', r';\s*DELETE\s+', r';\s*TRUNCATE\s+',
        r'--', r'/\*', r'\*/', r'xp_cmdshell', r'EXEC\s+',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError(f"Query contains potentially dangerous pattern: {pattern}")

    # Analyze query patterns
    issues = analyze_query_patterns(query, db_type)

    # Suggest indexes
    recommendations = suggest_indexes(query, db_type)

    # Estimate relative cost (simplified heuristic)
    cost_factors = {
        "SELECT *": 2.0,
        "no WHERE": 5.0,
        "OR condition": 1.5,
        "LIKE %": 3.0,
        "NOT IN": 2.5,
        "function on column": 2.0,
    }

    estimated_cost = 1.0
    for issue in issues:
        for keyword, multiplier in cost_factors.items():
            if keyword in issue["issue"]:
                estimated_cost *= multiplier

    return {
        "query": query.strip(),
        "db_type": db_type,
        "issues": issues,
        "issue_count": len(issues),
        "estimated_cost": round(estimated_cost, 2),
        "recommendations": recommendations
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Analyze SQL queries and suggest optimizations")
    parser.add_argument("file_path", nargs='?', help="Path to SQL file (or - for stdin)")
    parser.add_argument("--query", help="SQL query string (alternative to file)")
    parser.add_argument("--db", choices=["postgres", "mysql"], default="postgres", help="Database type")

    try:
        args = parser.parse_args()

        # Read query from file, stdin, or --query argument
        if args.query:
            query = args.query
        elif args.file_path == '-':
            query = sys.stdin.read()
        elif args.file_path:
            is_valid, error = validate_path(args.file_path)
            if not is_valid:
                raise ValueError(error)
            with open(args.file_path, 'r', encoding='utf-8') as f:
                query = f.read()
        else:
            raise ValueError("Provide either file_path, --query, or pipe to stdin")

        data = analyze_sql(query=query, db_type=args.db)

        output = {
            "success": True,
            "data": data,
            "errors": [],
            "metadata": {
                "tool": "sql-explain",
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
                "tool": "sql-explain",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat() + "Z"
            }
        }

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()
