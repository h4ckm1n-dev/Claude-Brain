#!/usr/bin/env python3
"""
Tool Name: env-manager.py
Purpose: Validate .env files, check for secrets, ensure completeness
Security: Path validation, secret detection, schema validation

Usage:
    ./env-manager.py <env-file> [--schema schema.json]

Example:
    ./env-manager.py .env
    ./env-manager.py .env.production --schema env-schema.json

Output:
    JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime, timezone

# Tool metadata
TOOL_NAME = "env-manager"
TOOL_VERSION = "1.0.0"

# Secret detection patterns
SECRET_PATTERNS = {
    'api_key': re.compile(r'(?:api[_-]?key|apikey)[\s]*=[\s]*["\']?([A-Za-z0-9_\-]{20,})["\']?', re.IGNORECASE),
    'password': re.compile(r'password[\s]*=[\s]*["\']?([^\s"\']{1,})["\']?', re.IGNORECASE),
    'secret': re.compile(r'(?:secret|token)[\s]*=[\s]*["\']?([A-Za-z0-9_\-]{16,})["\']?', re.IGNORECASE),
    'aws_key': re.compile(r'(?:aws_access_key_id|aws_secret_access_key)[\s]*=[\s]*["\']?([A-Za-z0-9/+=]{20,})["\']?', re.IGNORECASE),
    'github_token': re.compile(r'(?:github_token|gh_token)[\s]*=[\s]*["\']?(ghp_[A-Za-z0-9]{36})["\']?', re.IGNORECASE),
    'private_key': re.compile(r'private_key[\s]*=[\s]*["\']?(-----BEGIN.*KEY-----)["\']?', re.IGNORECASE),
}

# Dangerous default values that should be changed
DANGEROUS_DEFAULTS = {
    'password': ['password', '123456', 'admin', 'changeme', 'default', ''],
    'secret': ['secret', 'change-me', 'default-secret', ''],
    'api_key': ['your-api-key-here', 'changeme', ''],
}

# Common environment variable names that typically shouldn't be empty
SHOULD_NOT_BE_EMPTY = {
    'DATABASE_URL', 'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
    'API_KEY', 'SECRET_KEY', 'JWT_SECRET',
    'APP_NAME', 'APP_ENV', 'NODE_ENV',
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
        cwd = Path.cwd().resolve()

        # Check path exists
        if not resolved.exists():
            return False

        # Check it's a regular file
        if not resolved.is_file():
            return False

        # Must be within current directory or subdirectories (prevents ../../../etc/passwd)
        try:
            resolved.relative_to(cwd)
        except ValueError:
            # Path is outside current directory
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


def parse_env_file(file_path: str) -> Dict[str, str]:
    """
    Parse .env file into key-value pairs

    Args:
        file_path: Path to .env file

    Returns:
        dict: Environment variables as key-value pairs
    """
    env_vars = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE format
                if '=' in line:
                    # Split on first = only
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    env_vars[key] = value

        return env_vars
    except Exception as e:
        raise RuntimeError(f"Failed to parse .env file: {e}")


def check_secrets(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check for potential secrets in plain text

    Args:
        env_vars: Environment variables to check

    Returns:
        list: List of potential secret findings
    """
    findings = []

    for key, value in env_vars.items():
        # Check each pattern
        for pattern_name, pattern in SECRET_PATTERNS.items():
            if pattern.search(f"{key}={value}"):
                findings.append({
                    'key': key,
                    'issue': f'Possible {pattern_name} in plain text',
                    'severity': 'high',
                    'recommendation': 'Consider using environment-specific secrets management'
                })
                break  # Only report once per key

    return findings


def check_dangerous_values(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Check for dangerous default values

    Args:
        env_vars: Environment variables to check

    Returns:
        list: List of dangerous value warnings
    """
    warnings = []

    for key, value in env_vars.items():
        key_lower = key.lower()

        # Check password defaults
        if 'password' in key_lower or 'passwd' in key_lower:
            if value.lower() in DANGEROUS_DEFAULTS['password']:
                warnings.append({
                    'key': key,
                    'issue': 'Password appears to be default or empty',
                    'severity': 'critical',
                    'recommendation': 'Set a strong, unique password'
                })

        # Check secret defaults
        elif 'secret' in key_lower or 'token' in key_lower:
            if value.lower() in DANGEROUS_DEFAULTS['secret']:
                warnings.append({
                    'key': key,
                    'issue': 'Secret appears to be default or empty',
                    'severity': 'high',
                    'recommendation': 'Generate a secure random secret'
                })

        # Check API key defaults
        elif 'api' in key_lower and 'key' in key_lower:
            if value.lower() in DANGEROUS_DEFAULTS['api_key']:
                warnings.append({
                    'key': key,
                    'issue': 'API key appears to be default or empty',
                    'severity': 'high',
                    'recommendation': 'Configure valid API key from provider'
                })

        # Check for empty critical values
        if key in SHOULD_NOT_BE_EMPTY and not value:
            warnings.append({
                'key': key,
                'issue': 'Critical environment variable is empty',
                'severity': 'medium',
                'recommendation': f'Provide a value for {key}'
            })

    return warnings


def validate_schema(env_vars: Dict[str, str], schema_path: str) -> List[str]:
    """
    Validate .env against a JSON schema

    Args:
        env_vars: Environment variables to validate
        schema_path: Path to JSON schema file

    Returns:
        list: List of missing required variables
    """
    try:
        if not validate_path(schema_path):
            raise ValueError(f"Invalid schema path: {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        # Check for required keys
        required = schema.get('required', [])
        missing = [key for key in required if key not in env_vars]

        return missing
    except Exception as e:
        raise RuntimeError(f"Failed to validate schema: {e}")


def create_output(success: bool, data: Any = None, errors: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Create standardized JSON output

    Args:
        success: Whether operation succeeded
        data: Operation result data
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
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }
    }


def main():
    """
    Main entry point

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse arguments
        if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
            print(__doc__)
            sys.exit(0)

        env_file = sys.argv[1]
        schema_file = None

        # Check for schema argument
        if len(sys.argv) >= 4 and sys.argv[2] == '--schema':
            schema_file = sys.argv[3]

        # Validate env file path
        if not validate_path(env_file):
            output = create_output(
                success=False,
                errors=[{
                    "type": "ValidationError",
                    "message": f"Invalid or inaccessible .env file: {env_file}"
                }]
            )
            print(json.dumps(output, indent=2))
            sys.exit(1)

        # Parse .env file
        env_vars = parse_env_file(env_file)

        # Run checks
        secrets_found = check_secrets(env_vars)
        warnings = check_dangerous_values(env_vars)
        missing_required = []

        # Validate against schema if provided
        if schema_file:
            try:
                missing_required = validate_schema(env_vars, schema_file)
            except Exception as e:
                output = create_output(
                    success=False,
                    errors=[{
                        "type": "SchemaError",
                        "message": str(e)
                    }]
                )
                print(json.dumps(output, indent=2))
                sys.exit(1)

        # Calculate statistics
        empty_count = sum(1 for v in env_vars.values() if not v)
        critical_issues = [w for w in warnings if w['severity'] == 'critical']
        high_issues = [w for w in warnings + secrets_found if w['severity'] == 'high']

        # Build data object
        data = {
            "file": env_file,
            "variables_found": len(env_vars),
            "empty_variables": empty_count,
            "missing_required": missing_required,
            "secrets_found": secrets_found,
            "warnings": warnings,
            "statistics": {
                "critical_issues": len(critical_issues),
                "high_issues": len(high_issues),
                "total_issues": len(secrets_found) + len(warnings)
            }
        }

        # Success output
        output = create_output(success=True, data=data)

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
