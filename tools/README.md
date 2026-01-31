# Custom Tools Library

**Version**: 1.0.0
**Last Updated**: 2025-11-06
**Total Tools**: 23
**Supported Platforms**: macOS, Linux

A comprehensive library of 23 security-hardened, JSON-based command-line tools designed for autonomous agent integration. Each tool follows strict security patterns, provides standardized JSON output, and includes robust error handling for production use.

---

## Table of Contents

1. [Introduction & Quick Start](#introduction--quick-start)
2. [Tool Categories & Overview](#tool-categories--overview)
3. [Tool Reference](#tool-reference)
   - [Security Tools (4)](#security-tools)
   - [Analysis Tools (4)](#analysis-tools)
   - [Testing Tools (4)](#testing-tools)
   - [Data Analysis Tools (3)](#data-analysis-tools)
   - [DevOps Tools (5)](#devops-tools)
   - [Core Utilities (3)](#core-utilities)
4. [Security Best Practices](#security-best-practices)
5. [Agent Integration Guide](#agent-integration-guide)
6. [Installation & Dependencies](#installation--dependencies)
7. [Troubleshooting](#troubleshooting)

---

## Introduction & Quick Start

### What is the Custom Tools Library?

The Custom Tools Library is a collection of 23 production-ready command-line tools built specifically for integration with Claude Code's autonomous agent ecosystem. Each tool is designed with three core principles:

1. **Security First**: All tools implement command injection prevention, path traversal protection, and input validation
2. **Standardized Output**: Every tool returns structured JSON for easy parsing by agents
3. **Agent-Friendly**: Tools are optimized for batch processing, silent operation, and programmatic use

### Why Agents Need These Tools

Autonomous agents require reliable, predictable tools that:
- **Return machine-readable output** (JSON) instead of human-formatted text
- **Fail gracefully** with structured error messages
- **Prevent security vulnerabilities** when processing untrusted input
- **Provide actionable insights** without requiring human interpretation

### Quick Installation

```bash
# Navigate to Claude Code directory
cd ~/.claude

# Verify tools are present
ls -la tools/

# Test tool availability
./tools/core/health-check.sh

# Make tools executable (if needed)
find tools/ -name "*.py" -o -name "*.sh" | xargs chmod +x
```

### Basic Usage Example

```bash
# Scan a directory for secrets
cd ~/.claude
./tools/security/secret-scanner.py ./src

# Output (JSON):
{
  "success": true,
  "data": {
    "scanned_files": 45,
    "findings": [
      {
        "file": "src/config.py",
        "line": 12,
        "type": "api_key",
        "preview": "AK***************XY"
      }
    ],
    "summary": "Found 1 potential secret(s) in 1 file(s)"
  },
  "errors": [],
  "metadata": {
    "tool": "secret-scanner",
    "version": "1.0.0",
    "timestamp": "2025-11-06T12:34:56Z"
  }
}
```

---

## Tool Categories & Overview

The 23 tools are organized into 6 categories based on their primary function:

### Security Tools (4 tools)
**Purpose**: Identify security vulnerabilities, secrets, and permission issues
**When Used**: During code audits, pre-deployment checks, security reviews
**Key Agents**: security-practice-reviewer, code-reviewer, deployment-engineer

| Tool | Purpose | Output |
|------|---------|--------|
| secret-scanner.py | Detect hardcoded secrets (API keys, passwords, tokens) | Findings with redacted secrets |
| permission-auditor.py | Identify dangerous file permissions (777, 666, setuid) | Permission issues by severity |
| cert-validator.sh | Validate SSL certificates (expiration, validity) | Certificate status and days remaining |
| vuln-checker.sh | Check dependencies for known vulnerabilities | Vulnerability counts by severity |

### Analysis Tools (4 tools)
**Purpose**: Analyze code quality, complexity, types, and duplication
**When Used**: During refactoring, code reviews, technical debt assessment
**Key Agents**: refactoring-specialist, code-reviewer, code-architect

| Tool | Purpose | Output |
|------|---------|--------|
| complexity-check.py | Calculate cyclomatic complexity | Complexity grades (A-F) per function |
| type-coverage.py | Measure type hint coverage | Coverage percentage and low-coverage files |
| duplication-detector.py | Find duplicate code blocks | Duplicate locations grouped by hash |
| import-analyzer.py | Detect circular imports and unused imports | Import issues and dependency graph |

### Testing Tools (4 tools)
**Purpose**: Measure test coverage, select tests, detect flakiness
**When Used**: During test execution, CI/CD pipelines, quality gates
**Key Agents**: test-engineer, api-tester, code-reviewer

| Tool | Purpose | Output |
|------|---------|--------|
| coverage-reporter.py | Parse coverage reports (XML, LCOV) | Line/branch coverage percentages |
| test-selector.py | Select tests based on git diff | Test files to run for changed code |
| mutation-score.sh | Calculate mutation testing scores | Mutation survival rate |
| flakiness-detector.py | Identify flaky tests from history | Flaky tests with failure rates |

### Data Analysis Tools (3 tools)
**Purpose**: Analyze logs, SQL queries, and time-series metrics
**When Used**: During debugging, performance optimization, data analysis
**Key Agents**: data-scientist, debugger, database-optimizer

| Tool | Purpose | Output |
|------|---------|--------|
| log-analyzer.py | Extract error patterns from logs | Error patterns with frequencies |
| sql-explain.py | Analyze SQL for optimization | Index suggestions and anti-patterns |
| metrics-aggregator.py | Compute statistics on metrics | p50/p95/p99, anomaly detection |

### DevOps Tools (5 tools)
**Purpose**: Manage infrastructure, deployments, and service health
**When Used**: During deployments, health checks, resource monitoring
**Key Agents**: deployment-engineer, observability-engineer, infrastructure-architect

| Tool | Purpose | Output |
|------|---------|--------|
| docker-manager.sh | Manage Docker containers and images | Container/image lists, prune results |
| env-manager.py | Validate .env files for secrets | Environment variable issues |
| service-health.sh | Check HTTP endpoint health | Health status and response time |
| ci-status.sh | Check CI/CD pipeline status | Build status and duration |
| resource-monitor.py | Monitor system resources | CPU, memory, disk usage |

### Core Utilities (3 tools)
**Purpose**: File conversion, HTTP mocking, health checks
**When Used**: During testing, data transformation, system validation
**Key Agents**: All agents (utility functions)

| Tool | Purpose | Output |
|------|---------|--------|
| file-converter.py | Convert between JSON/YAML/TOML | Converted file content |
| mock-server.py | HTTP mock server for testing | Server status and routes |
| health-check.sh | Test all tools in library | Tool availability report |

---

## Tool Reference

### Security Tools

#### secret-scanner.py

**Purpose**: Scans directories for hardcoded secrets like API keys, passwords, AWS credentials, GitHub tokens, and private keys. Detects 6 secret patterns and redacts findings for secure reporting.

**Location**: `~/.claude/tools/security/secret-scanner.py`

**Usage**:
```bash
./tools/security/secret-scanner.py <directory>
```

**Example**:
```bash
cd ~/.claude
./tools/security/secret-scanner.py ./src

# Output:
{
  "success": true,
  "data": {
    "scanned_files": 45,
    "skipped_files": 12,
    "findings": [
      {
        "file": "src/config.py",
        "line": 12,
        "type": "api_key",
        "preview": "AK***************XY"
      },
      {
        "file": "src/auth.py",
        "line": 28,
        "type": "github_token",
        "preview": "gh***********************************AB"
      }
    ],
    "summary": "Found 2 potential secret(s) in 2 file(s)"
  },
  "errors": [],
  "metadata": {
    "tool": "secret-scanner",
    "version": "1.0.0",
    "timestamp": "2025-11-06T12:34:56Z"
  }
}
```

**Detected Secret Patterns**:
- API keys: `api_key="..."` (20+ characters)
- Passwords: `password="..."` (8+ characters)
- AWS keys: `AKIA[0-9A-Z]{16}`
- GitHub tokens: `ghp_[A-Za-z0-9]{36}`
- Private keys: `-----BEGIN (RSA|PRIVATE) KEY-----`
- Generic secrets: `secret="..."` (16+ characters)

**Security Features**:
- Redacts secrets to first 2 + last 2 characters only
- Skips binary files and files larger than 10MB
- Blocks scanning of system directories (/etc, /System, /Library)
- Skips hidden files and directories

**Agent Use Case**: When security-practice-reviewer performs pre-deployment audits, it uses secret-scanner to identify and alert about hardcoded credentials before code reaches production.

---

#### permission-auditor.py

**Purpose**: Audits file permissions for security issues including world-writable files (777), dangerous permissions (666), and sensitive files with improper access controls.

**Location**: `~/.claude/tools/security/permission-auditor.py`

**Usage**:
```bash
./tools/security/permission-auditor.py <directory>
```

**Example**:
```bash
cd ~/.claude
./tools/security/permission-auditor.py ./src

# Output:
{
  "success": true,
  "data": {
    "scanned_files": 123,
    "skipped_files": 8,
    "total_issues": 3,
    "files_with_issues": 2,
    "severity_counts": {
      "critical": 1,
      "high": 1,
      "medium": 1,
      "low": 0
    },
    "issues": [
      {
        "file": "./src/config.sh",
        "issue": "full_access",
        "severity": "critical",
        "permissions": "rwxrwxrwx",
        "octal": "0o777",
        "description": "File has 777 permissions (full access to everyone)"
      },
      {
        "file": "./src/.env",
        "issue": "sensitive_world_readable",
        "severity": "high",
        "permissions": "rw-r--r--",
        "octal": "0o644",
        "description": "Sensitive file is world-readable"
      }
    ],
    "summary": "Found 3 permission issue(s) in 2 file(s)"
  }
}
```

**Detected Permission Issues**:
- **Critical**: 777 permissions (full access)
- **High**: World-writable (002), world-readable sensitive files
- **Medium**: Group-writable sensitive files, setgid executables
- **High**: Setuid executables (run with owner privileges)

**Sensitive File Patterns**: `.env`, `.key`, `.pem`, `.crt`, `.ssh`, `password`, `secret`, `credentials`, `token`, `private`

**Agent Use Case**: When deployment-engineer prepares application deployment, permission-auditor verifies that configuration files and secrets have proper access controls (600 for sensitive files, no 777 permissions).

---

#### cert-validator.sh

**Purpose**: Validates SSL/TLS certificates from files or URLs, checking expiration dates, validity status, and calculating days until expiration for proactive renewal.

**Location**: `~/.claude/tools/security/cert-validator.sh`

**Usage**:
```bash
# Validate certificate from URL
./tools/security/cert-validator.sh <url:port>

# Validate certificate from file
./tools/security/cert-validator.sh <file.crt>
```

**Example**:
```bash
cd ~/.claude
./tools/security/cert-validator.sh example.com:443

# Output:
{
  "success": true,
  "data": {
    "certificate": "example.com:443",
    "valid": true,
    "status": "valid",
    "expires": "2025-12-15 23:59:59 GMT",
    "days_remaining": 71,
    "issuer": "DigiCert Inc",
    "subject": "example.com"
  },
  "errors": [],
  "metadata": {
    "tool": "cert-validator",
    "version": "1.0.0"
  }
}

# Expiring soon:
./tools/security/cert-validator.sh old-site.com:443

# Output:
{
  "success": true,
  "data": {
    "certificate": "old-site.com:443",
    "valid": true,
    "status": "expiring_soon",
    "expires": "2025-11-20 23:59:59 GMT",
    "days_remaining": 14,
    "warning": "Certificate expires in less than 30 days"
  }
}
```

**Certificate Statuses**:
- `valid`: More than 30 days until expiration
- `expiring_soon`: Less than 30 days until expiration
- `expired`: Certificate has expired

**Supported Sources**:
- Remote URLs: `example.com:443` (uses openssl s_client)
- Local files: `/path/to/cert.crt` (uses openssl x509)

**Agent Use Case**: When infrastructure-architect performs security audits, cert-validator checks all production certificates to ensure none are expired or expiring soon, preventing service outages.

---

#### vuln-checker.sh

**Purpose**: Checks project dependencies for known security vulnerabilities using npm audit (JavaScript/Node.js) or safety (Python) depending on the project type.

**Location**: `~/.claude/tools/security/vuln-checker.sh`

**Usage**:
```bash
# Check package.json (npm)
./tools/security/vuln-checker.sh package.json

# Check requirements.txt (Python)
./tools/security/vuln-checker.sh requirements.txt
```

**Example**:
```bash
cd ~/.claude
./tools/security/vuln-checker.sh /path/to/package.json

# Output:
{
  "success": true,
  "data": {
    "file": "/path/to/package.json",
    "package_manager": "npm",
    "vulnerabilities": {
      "critical": 2,
      "high": 5,
      "moderate": 8,
      "low": 3,
      "total": 18
    },
    "details": [
      {
        "severity": "critical",
        "package": "lodash",
        "version": "4.17.15",
        "vulnerability": "Prototype Pollution"
      }
    ],
    "summary": "Found 18 vulnerabilities (2 critical, 5 high)"
  }
}
```

**Supported Package Managers**:
- **npm** (package.json): Uses `npm audit --json`
- **safety** (requirements.txt): Uses `safety check --json`

**Graceful Degradation**: If npm or safety is not installed, returns error with installation instructions instead of failing silently.

**Agent Use Case**: When security-practice-reviewer audits a codebase, vuln-checker identifies vulnerable dependencies and reports severity counts, allowing the agent to prioritize critical updates before deployment.

---

### Analysis Tools

#### complexity-check.py

**Purpose**: Calculates cyclomatic complexity for Python and JavaScript code to identify functions that may be difficult to maintain or test. Uses radon (if available) or falls back to AST-based calculation.

**Location**: `~/.claude/tools/analysis/complexity-check.py`

**Usage**:
```bash
./tools/analysis/complexity-check.py <file.py|file.js> [--threshold 10]
```

**Example**:
```bash
cd ~/.claude
./tools/analysis/complexity-check.py ./src/complex_function.py

# Output:
{
  "success": true,
  "data": {
    "file": "./src/complex_function.py",
    "average_complexity": 7.3,
    "grade": "B",
    "functions": [
      {
        "name": "process_data",
        "complexity": 15,
        "grade": "C",
        "line": 45
      },
      {
        "name": "validate_input",
        "complexity": 3,
        "grade": "A",
        "line": 12
      }
    ],
    "summary": "Average complexity: 7.3 (Grade B). 1 function(s) exceed threshold of 10."
  }
}
```

**Complexity Grades**:
- **A**: 1-5 (simple, easy to test)
- **B**: 6-10 (moderate complexity)
- **C**: 11-20 (complex, should refactor)
- **D**: 21-30 (high risk)
- **F**: 31+ (very high risk, refactor immediately)

**Supported Languages**:
- Python (.py): AST-based analysis
- JavaScript (.js, .jsx, .ts, .tsx): Basic pattern matching

**Agent Use Case**: When refactoring-specialist identifies technical debt, complexity-check finds functions with grade C or worse, helping prioritize refactoring efforts on the most complex code.

---

#### type-coverage.py

**Purpose**: Analyzes Python and TypeScript codebases to measure type hint coverage, identifying functions with missing type annotations to improve code safety and IDE support.

**Location**: `~/.claude/tools/analysis/type-coverage.py`

**Usage**:
```bash
./tools/analysis/type-coverage.py <file.py|directory/> [--threshold 80]
```

**Example**:
```bash
cd ~/.claude
./tools/analysis/type-coverage.py ./src

# Output:
{
  "success": true,
  "data": {
    "total_functions": 45,
    "typed_functions": 38,
    "coverage_percentage": 84.4,
    "low_coverage_files": [
      {
        "file": "./src/legacy.py",
        "coverage": 33.3,
        "typed": 2,
        "total": 6
      }
    ],
    "summary": "Type coverage: 84.4% (38/45 functions). 1 file(s) below 80% threshold."
  }
}
```

**Coverage Metrics**:
- **Parameters**: Tracks type-annotated parameters
- **Return types**: Tracks return type annotations
- **Function-level**: Per-function and per-file granularity

**Supported Languages**:
- Python (.py): Full AST analysis (parameters + return types)
- TypeScript (.ts, .tsx): Regex-based detection

**Agent Use Case**: When python-expert or typescript-expert refactors code, type-coverage identifies files with low type safety, guiding the agent to add type hints where they're most needed.

---

#### duplication-detector.py

**Purpose**: Finds duplicate code blocks using a sliding window hash approach, helping identify copy-paste duplication that should be refactored into shared functions.

**Location**: `~/.claude/tools/analysis/duplication-detector.py`

**Usage**:
```bash
./tools/analysis/duplication-detector.py <directory> [--window 5] [--min-duplicates 2]
```

**Example**:
```bash
cd ~/.claude
./tools/analysis/duplication-detector.py ./src --window 5

# Output:
{
  "success": true,
  "data": {
    "scanned_files": 23,
    "duplicates_found": 8,
    "duplicate_groups": [
      {
        "hash": "abc123def456",
        "occurrences": 3,
        "locations": [
          {"file": "./src/auth.py", "line": 45},
          {"file": "./src/users.py", "line": 123},
          {"file": "./src/admin.py", "line": 89}
        ],
        "preview": "def validate_email(email):\n    if not email..."
      }
    ],
    "summary": "Found 8 duplicate blocks in 23 files."
  }
}
```

**Detection Algorithm**:
- Sliding window of N lines (default: 5)
- SHA-256 hash of normalized code (whitespace removed)
- Groups duplicates by hash for easy identification

**Supported Languages**: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.java`, `.c`, `.cpp`, `.go`

**Configuration**:
- `--window N`: Size of sliding window (default: 5 lines)
- `--min-duplicates N`: Minimum occurrences to report (default: 2)

**Agent Use Case**: When refactoring-specialist performs DRY (Don't Repeat Yourself) refactoring, duplication-detector identifies copy-pasted code blocks that should be extracted into reusable functions or classes.

---

#### import-analyzer.py

**Purpose**: Analyzes Python import statements to detect circular dependencies (module A imports B, B imports A) and unused imports that can be safely removed.

**Location**: `~/.claude/tools/analysis/import-analyzer.py`

**Usage**:
```bash
./tools/analysis/import-analyzer.py <file.py|directory/>
```

**Example**:
```bash
cd ~/.claude
./tools/analysis/import-analyzer.py ./src

# Output:
{
  "success": true,
  "data": {
    "total_files": 15,
    "circular_dependencies": [
      {
        "cycle": ["src/models.py", "src/views.py", "src/models.py"],
        "description": "models.py -> views.py -> models.py"
      }
    ],
    "unused_imports": [
      {
        "file": "./src/utils.py",
        "imports": ["os", "sys"],
        "line": 3
      }
    ],
    "summary": "Found 1 circular dependency cycle and 2 unused imports."
  }
}
```

**Analysis Features**:
- **Circular dependency detection**: Uses DFS graph traversal to find import cycles
- **Unused import detection**: Checks if imported names are used in code
- **Import types**: Handles `import module` and `from module import name` patterns

**Supported Languages**: Python only (uses AST parsing)

**Agent Use Case**: When code-architect designs system architecture, import-analyzer detects circular dependencies that violate design principles, allowing the agent to recommend refactoring to break the cycles.

---

### Testing Tools

#### coverage-reporter.py

**Purpose**: Parses code coverage reports from pytest (Cobertura XML) or Jest/Istanbul (LCOV) and extracts coverage percentages, uncovered lines, and file-level metrics.

**Location**: `~/.claude/tools/testing/coverage-reporter.py`

**Usage**:
```bash
./tools/testing/coverage-reporter.py <coverage.xml|lcov.info> [--format auto]
```

**Example**:
```bash
cd ~/.claude
./tools/testing/coverage-reporter.py ./coverage.xml

# Output:
{
  "success": true,
  "data": {
    "format": "cobertura",
    "line_coverage": 85.2,
    "branch_coverage": 78.5,
    "files": [
      {
        "path": "src/utils.py",
        "line_coverage": 92.3,
        "lines_covered": 120,
        "lines_total": 130,
        "uncovered_lines": [45, 67, 89, 123, 125, 126, 128, 129, 130, 131]
      }
    ],
    "summary": "Overall coverage: 85.2% lines, 78.5% branches"
  }
}
```

**Supported Formats**:
- **Cobertura XML**: pytest --cov --cov-report=xml
- **LCOV**: Jest --coverage --coverageReporters=lcov
- **Auto-detection**: Analyzes file content to determine format

**Coverage Metrics**:
- Line coverage: Percentage of executable lines tested
- Branch coverage: Percentage of conditional branches tested
- Uncovered lines: Specific line numbers missing coverage

**Agent Use Case**: When test-engineer validates test quality, coverage-reporter parses coverage files to identify untested code, failing builds that don't meet the 80% coverage threshold.

---

#### test-selector.py

**Purpose**: Selects which tests to run based on git diff changes, mapping modified source files to their corresponding test files to speed up CI/CD pipelines.

**Location**: `~/.claude/tools/testing/test-selector.py`

**Usage**:
```bash
./tools/testing/test-selector.py [--base main] [--head HEAD]
```

**Example**:
```bash
cd ~/.claude
./tools/testing/test-selector.py --base main --head feature-branch

# Output:
{
  "success": true,
  "data": {
    "changed_files": [
      "src/auth.py",
      "src/models/user.py"
    ],
    "selected_tests": [
      "tests/test_auth.py",
      "tests/models/test_user.py",
      "tests/integration/test_user_flow.py"
    ],
    "summary": "2 file(s) changed, 3 test file(s) selected"
  }
}
```

**Test Mapping Patterns**:
- Python: `src/module.py` → `tests/test_module.py`
- JavaScript: `src/utils.js` → `tests/utils.test.js`
- TypeScript: `src/api.ts` → `tests/api.spec.ts`
- Java: `src/Service.java` → `tests/ServiceTest.java`
- Ruby: `lib/model.rb` → `spec/model_spec.rb`
- Go: `pkg/handler.go` → `pkg/handler_test.go`

**Agent Use Case**: When test-engineer runs tests in CI/CD, test-selector determines which tests need to run based on code changes, reducing test execution time from 10 minutes to 2 minutes for small pull requests.

---

#### mutation-score.sh

**Purpose**: Calculates mutation testing scores by integrating with mutmut (Python) or Stryker (JavaScript/TypeScript), measuring how well tests detect intentional code mutations.

**Location**: `~/.claude/tools/testing/mutation-score.sh`

**Usage**:
```bash
# Python with mutmut
./tools/testing/mutation-score.sh /path/to/project mutmut

# JavaScript with stryker
./tools/testing/mutation-score.sh /path/to/project stryker
```

**Example**:
```bash
cd ~/.claude
./tools/testing/mutation-score.sh ./src mutmut

# Output:
{
  "success": true,
  "data": {
    "tool": "mutmut",
    "total_mutations": 150,
    "killed": 135,
    "survived": 10,
    "timeout": 5,
    "score": 90.0,
    "summary": "Mutation score: 90.0% (135/150 killed)"
  }
}
```

**Supported Tools**:
- **mutmut** (Python): `mutmut run && mutmut results`
- **Stryker** (JavaScript/TypeScript): `stryker run`

**Mutation Score Interpretation**:
- **90-100%**: Excellent test suite (detects nearly all bugs)
- **80-89%**: Good test coverage
- **70-79%**: Adequate (room for improvement)
- **Below 70%**: Weak test suite (many bugs slip through)

**Agent Use Case**: When test-engineer validates test suite quality, mutation-score measures how effective tests are at catching bugs, not just covering lines. A 90% mutation score indicates tests actually verify behavior, not just execute code.

---

#### flakiness-detector.py

**Purpose**: Identifies flaky tests (tests that sometimes pass, sometimes fail) by analyzing test history from multiple runs, helping teams fix or quarantine unreliable tests.

**Location**: `~/.claude/tools/testing/flakiness-detector.py`

**Usage**:
```bash
./tools/testing/flakiness-detector.py <test-results.xml> [--threshold 0.3]
```

**Example**:
```bash
cd ~/.claude
./tools/testing/flakiness-detector.py ./test-history/*.xml --threshold 0.3

# Output:
{
  "success": true,
  "data": {
    "total_tests": 234,
    "flaky_tests": 5,
    "flakiness_threshold": 0.3,
    "flaky_test_details": [
      {
        "name": "test_concurrent_database_access",
        "flakiness_score": 0.4,
        "total_runs": 10,
        "failures": 4,
        "description": "Failed 4 out of 10 runs (40% failure rate)"
      },
      {
        "name": "test_api_timeout",
        "flakiness_score": 0.3,
        "total_runs": 10,
        "failures": 3,
        "description": "Failed 3 out of 10 runs (30% failure rate)"
      }
    ],
    "summary": "Found 5 flaky tests (failure rate >= 30%)"
  }
}
```

**Supported Formats**:
- JUnit XML (pytest --junit-xml)
- pytest JSON (pytest --json)

**Flakiness Threshold**: Tests that fail X% of the time (default: 30%)

**Agent Use Case**: When test-engineer analyzes CI/CD failures, flakiness-detector identifies unreliable tests that cause false positives, recommending they be fixed (race conditions, timing issues) or quarantined until stable.

---

### Data Analysis Tools

#### log-analyzer.py

**Purpose**: Parses application logs to extract error patterns, count log levels, and identify the most common errors for troubleshooting and monitoring.

**Location**: `~/.claude/tools/data/log-analyzer.py`

**Usage**:
```bash
./tools/data/log-analyzer.py <logfile.log> [--format plain|json|apache] [--level ERROR]
```

**Example**:
```bash
cd ~/.claude
./tools/data/log-analyzer.py /var/log/app.log --format plain --level ERROR

# Output:
{
  "success": true,
  "data": {
    "total_lines": 1523,
    "log_levels": {
      "ERROR": 45,
      "WARN": 12,
      "INFO": 1450,
      "DEBUG": 16
    },
    "error_patterns": [
      {
        "pattern": "Database connection failed",
        "count": 15,
        "first_seen": "2025-11-06T10:23:45Z",
        "last_seen": "2025-11-06T12:15:30Z",
        "example": "2025-11-06 12:15:30 ERROR Database connection failed: timeout after 5s"
      },
      {
        "pattern": "API rate limit exceeded",
        "count": 8,
        "first_seen": "2025-11-06T11:00:00Z",
        "last_seen": "2025-11-06T11:30:00Z"
      }
    ],
    "summary": "Analyzed 1523 lines, found 45 errors with 12 unique patterns"
  }
}
```

**Supported Log Formats**:
- **Plain text**: Standard application logs
- **JSON**: Structured JSON logs (one per line)
- **Apache**: Common/Combined log format

**Pattern Extraction**: Removes timestamps, numbers, and IDs to group similar errors

**Agent Use Case**: When debugger investigates production issues, log-analyzer extracts the top 20 error patterns with frequencies, helping identify if errors are recurring (database timeouts) or one-off (specific user data).

---

#### sql-explain.py

**Purpose**: Analyzes SQL queries to detect anti-patterns (SELECT *, missing indexes, inefficient JOINs) and suggests optimizations for database performance.

**Location**: `~/.claude/tools/data/sql-explain.py`

**Usage**:
```bash
./tools/data/sql-explain.py <query.sql> [--db postgres|mysql]
```

**Example**:
```bash
cd ~/.claude
echo "SELECT * FROM users WHERE email LIKE '%@gmail.com'" | ./tools/data/sql-explain.py -

# Output:
{
  "success": true,
  "data": {
    "query": "SELECT * FROM users WHERE email LIKE '%@gmail.com'",
    "anti_patterns": [
      {
        "type": "select_star",
        "description": "Using SELECT * retrieves unnecessary columns",
        "recommendation": "Specify only needed columns: SELECT id, name, email FROM users"
      },
      {
        "type": "leading_wildcard",
        "description": "LIKE '%...' prevents index usage",
        "recommendation": "Use full-text search or avoid leading wildcards"
      }
    ],
    "suggested_indexes": [
      {
        "table": "users",
        "columns": ["email"],
        "reason": "Column used in WHERE clause"
      }
    ],
    "estimated_cost": 8.5,
    "summary": "Found 2 anti-patterns, suggested 1 index"
  }
}
```

**Detected Anti-Patterns**:
- SELECT * (retrieves unnecessary columns)
- Missing WHERE clause (full table scan)
- OR conditions (prevent index usage)
- LIKE '%...' (leading wildcard, no index)
- NOT IN subqueries (inefficient, use NOT EXISTS)
- Functions on indexed columns (prevent index usage)

**Suggested Optimizations**:
- Specific column lists
- Composite indexes on WHERE/JOIN columns
- Query rewriting (OR → UNION, NOT IN → NOT EXISTS)

**Agent Use Case**: When database-optimizer reviews queries before deployment, sql-explain identifies inefficient patterns and suggests indexes, preventing performance issues in production.

---

#### metrics-aggregator.py

**Purpose**: Computes statistics (mean, median, p95, p99) on time-series metrics and detects anomalies using z-score analysis for performance monitoring.

**Location**: `~/.claude/tools/data/metrics-aggregator.py`

**Usage**:
```bash
./tools/data/metrics-aggregator.py <metrics.csv> [--metric response_time] [--format csv|json]
```

**Example**:
```bash
cd ~/.claude
./tools/data/metrics-aggregator.py ./response_times.csv --metric latency

# Output:
{
  "success": true,
  "data": {
    "metric": "latency",
    "count": 1000,
    "statistics": {
      "min": 45.2,
      "max": 1520.8,
      "mean": 128.5,
      "median": 105.3,
      "p50": 105.3,
      "p95": 285.7,
      "p99": 450.2,
      "stddev": 89.3
    },
    "anomalies": [
      {
        "timestamp": "2025-11-06T12:15:30Z",
        "value": 1520.8,
        "z_score": 3.8,
        "description": "Value 1520.8 is 3.8 standard deviations from mean"
      }
    ],
    "summary": "Processed 1000 metrics, found 1 anomaly (z-score > 2.0)"
  }
}
```

**Supported Formats**:
- **CSV**: Columns for timestamp and metric value
- **JSON**: Array of objects with timestamp and metric fields

**Statistics Computed**:
- Central tendency: min, max, mean, median
- Percentiles: p50, p95, p99 (latency SLAs)
- Variability: standard deviation

**Anomaly Detection**: Z-score threshold (default: 2.0)
Formula: `z = (value - mean) / stddev`

**Agent Use Case**: When performance-profiler analyzes API response times, metrics-aggregator calculates p95/p99 percentiles for SLA compliance and identifies outlier requests that need investigation.

---

### DevOps Tools

#### docker-manager.sh

**Purpose**: Safely manages Docker containers and images with commands for listing, inspecting, and pruning resources. Requires `--confirm` flag for destructive operations.

**Location**: `~/.claude/tools/devops/docker-manager.sh`

**Usage**:
```bash
# List containers
./tools/devops/docker-manager.sh list-containers

# Prune images (requires --confirm)
./tools/devops/docker-manager.sh prune-images --confirm

# Inspect container
./tools/devops/docker-manager.sh inspect <container-id>
```

**Example**:
```bash
cd ~/.claude
./tools/devops/docker-manager.sh list-containers

# Output:
{
  "success": true,
  "data": {
    "command": "list-containers",
    "containers": [
      {
        "id": "a1b2c3d4e5f6",
        "name": "web-app",
        "image": "nginx:latest",
        "status": "running",
        "ports": "80:8080"
      },
      {
        "id": "f6e5d4c3b2a1",
        "name": "db",
        "image": "postgres:13",
        "status": "running",
        "ports": "5432:5432"
      }
    ],
    "summary": "Found 2 running containers"
  }
}

# Prune images (reclaim space):
./tools/devops/docker-manager.sh prune-images --confirm

# Output:
{
  "success": true,
  "data": {
    "command": "prune-images",
    "space_reclaimed": "2.3 GB",
    "images_removed": 15,
    "summary": "Pruned 15 dangling images, reclaimed 2.3 GB"
  }
}
```

**Supported Commands**:
- `list-containers`: Show all containers (running + stopped)
- `list-images`: Show all Docker images
- `inspect <id>`: Detailed container information
- `prune-images --confirm`: Remove unused images
- `prune-containers --confirm`: Remove stopped containers

**Safety Features**:
- Destructive commands require `--confirm` flag
- Validates Docker is installed and daemon running
- Sanitizes container/image identifiers (alphanumeric only)

**Agent Use Case**: When deployment-engineer performs infrastructure cleanup, docker-manager safely removes unused images and stopped containers, reclaiming disk space without accidentally deleting active services.

---

#### env-manager.py

**Purpose**: Validates .env files for security issues including plaintext secrets, dangerous default values, and empty critical variables.

**Location**: `~/.claude/tools/devops/env-manager.py`

**Usage**:
```bash
./tools/devops/env-manager.py <.env-file> [--schema schema.json]
```

**Example**:
```bash
cd ~/.claude
./tools/devops/env-manager.py ./.env

# Output:
{
  "success": true,
  "data": {
    "file": "./.env",
    "variables_found": 15,
    "critical_issues": 2,
    "high_issues": 3,
    "total_issues": 5,
    "issues": [
      {
        "variable": "DATABASE_PASSWORD",
        "severity": "critical",
        "issue": "default_password",
        "value": "password",
        "recommendation": "Change default password to strong, unique value"
      },
      {
        "variable": "API_KEY",
        "severity": "high",
        "issue": "plaintext_secret",
        "value": "sk_live_abc123...",
        "recommendation": "Store in secrets manager, reference by ID"
      },
      {
        "variable": "SECRET_KEY",
        "severity": "critical",
        "issue": "empty_critical_var",
        "recommendation": "Must set SECRET_KEY for production"
      }
    ],
    "summary": "Found 5 issues: 2 critical, 3 high"
  }
}
```

**Detected Issues**:
- **Critical**: Default passwords (password, admin, 123456), empty critical variables
- **High**: Plaintext API keys, passwords, tokens, AWS credentials, GitHub tokens
- **Medium**: Short passwords (<8 chars), weak passwords (test, demo)

**Critical Variables**: `DATABASE_URL`, `SECRET_KEY`, `API_KEY`, `AWS_ACCESS_KEY_ID`, `GITHUB_TOKEN`

**Agent Use Case**: When deployment-engineer prepares application for production, env-manager scans .env files to catch insecure configurations before deployment, preventing credential leaks and security breaches.

---

#### service-health.sh

**Purpose**: Checks HTTP/HTTPS endpoint health by measuring response time, validating status codes, and determining service availability with SSRF protection.

**Location**: `~/.claude/tools/devops/service-health.sh`

**Usage**:
```bash
./tools/devops/service-health.sh <url> [timeout_seconds]
```

**Example**:
```bash
cd ~/.claude
./tools/devops/service-health.sh https://api.example.com/health 5

# Output:
{
  "success": true,
  "data": {
    "url": "https://api.example.com/health",
    "status": "healthy",
    "http_code": 200,
    "response_time_ms": 245,
    "content_type": "application/json",
    "response_preview": "{\"status\":\"ok\",\"uptime\":86400}",
    "curl_exit_code": 0
  },
  "metadata": {
    "tool": "service-health",
    "version": "1.0.0"
  }
}

# Unhealthy service:
./tools/devops/service-health.sh https://down-service.com/api 5

# Output:
{
  "success": true,
  "data": {
    "url": "https://down-service.com/api",
    "status": "unhealthy",
    "http_code": 503,
    "response_time_ms": 1250,
    "error": "Service Unavailable"
  }
}
```

**Health Statuses**:
- `healthy`: HTTP 200-299, response time normal
- `degraded`: HTTP 200-299, response time slow
- `unhealthy`: HTTP 400-599, or client error
- `unreachable`: Connection failed

**Security Features**:
- Blocks localhost (127.0.0.1, ::1, 0.0.0.0)
- Blocks private IP ranges (10.x, 172.16-31.x, 192.168.x)
- Only allows http:// and https:// schemes

**Agent Use Case**: When observability-engineer monitors service health in production, service-health checks endpoints every 30 seconds, alerting when response times exceed SLA thresholds (>1000ms) or services return error codes.

---

#### ci-status.sh

**Purpose**: Checks CI/CD pipeline status by integrating with GitHub Actions, GitLab CI, CircleCI, or Jenkins APIs to determine if builds are passing or failing.

**Location**: `~/.claude/tools/devops/ci-status.sh`

**Usage**:
```bash
# GitHub Actions
./tools/devops/ci-status.sh github <owner/repo> <token>

# GitLab CI
./tools/devops/ci-status.sh gitlab <project-id> <token>

# CircleCI
./tools/devops/ci-status.sh circleci <project-slug> <token>

# Jenkins
./tools/devops/ci-status.sh jenkins <job-url> <user:token>
```

**Example**:
```bash
cd ~/.claude
./tools/devops/ci-status.sh github myorg/myrepo ghp_abc123

# Output:
{
  "success": true,
  "data": {
    "platform": "github",
    "repository": "myorg/myrepo",
    "status": "passing",
    "latest_run": {
      "id": 123456789,
      "status": "completed",
      "conclusion": "success",
      "branch": "main",
      "commit": "a1b2c3d4",
      "started_at": "2025-11-06T10:00:00Z",
      "completed_at": "2025-11-06T10:15:30Z",
      "duration_seconds": 930
    },
    "summary": "Build passing on main branch (duration: 15m 30s)"
  }
}
```

**Supported CI Platforms**:
- GitHub Actions (workflow runs API)
- GitLab CI (pipelines API)
- CircleCI (pipelines API)
- Jenkins (build status JSON)

**Build Statuses**:
- `passing`: Latest build successful
- `failing`: Latest build failed
- `pending`: Build in progress
- `unknown`: Unable to determine status

**Agent Use Case**: When deployment-engineer prepares deployment, ci-status verifies that all tests and checks passed in CI/CD before promoting code to production, preventing deployment of broken builds.

---

#### resource-monitor.py

**Purpose**: Monitors system resources (CPU, memory, disk usage) for capacity planning and performance troubleshooting. Requires psutil library.

**Location**: `~/.claude/tools/devops/resource-monitor.py`

**Usage**:
```bash
./tools/devops/resource-monitor.py [--interval 5] [--samples 10]
```

**Example**:
```bash
cd ~/.claude
./tools/devops/resource-monitor.py --interval 1 --samples 5

# Output:
{
  "success": true,
  "data": {
    "cpu": {
      "percent": 45.2,
      "count": 8,
      "load_avg_1min": 2.3,
      "load_avg_5min": 1.8,
      "load_avg_15min": 1.5
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 12.3,
      "available_gb": 3.7,
      "percent": 76.9
    },
    "disk": {
      "total_gb": 500.0,
      "used_gb": 320.5,
      "free_gb": 179.5,
      "percent": 64.1
    },
    "warnings": [
      "Memory usage above 75% (76.9%)"
    ],
    "summary": "CPU: 45.2%, Memory: 76.9%, Disk: 64.1%"
  }
}
```

**Monitored Resources**:
- **CPU**: Usage percentage, core count, load averages
- **Memory**: Total, used, available (GB), percentage
- **Disk**: Total, used, free (GB), percentage

**Warning Thresholds**:
- CPU > 80%
- Memory > 75%
- Disk > 90%

**Dependency**: Requires `pip install psutil`

**Agent Use Case**: When infrastructure-architect investigates performance issues, resource-monitor identifies resource bottlenecks (high memory usage, disk full) that may be causing application slowdowns or crashes.

---

### Core Utilities

#### file-converter.py

**Purpose**: Converts configuration files between JSON, YAML, and TOML formats with auto-detection and validation.

**Location**: `~/.claude/tools/core/file-converter.py`

**Usage**:
```bash
./tools/core/file-converter.py <input-file> <output-file> [--input-format auto] [--output-format json]
```

**Example**:
```bash
cd ~/.claude
./tools/core/file-converter.py config.yaml config.json

# Output:
{
  "success": true,
  "data": {
    "input_file": "config.yaml",
    "output_file": "config.json",
    "input_format": "yaml",
    "output_format": "json",
    "content": {
      "database": {
        "host": "localhost",
        "port": 5432
      },
      "api": {
        "timeout": 30
      }
    },
    "summary": "Converted config.yaml (yaml) to config.json (json)"
  }
}
```

**Supported Formats**:
- **JSON**: JavaScript Object Notation
- **YAML**: YAML Ain't Markup Language
- **TOML**: Tom's Obvious, Minimal Language

**Auto-Detection**: Analyzes file extension and content to determine format

**Agent Use Case**: When backend-architect migrates configuration from YAML to TOML, file-converter handles the conversion while preserving data structure and validating syntax, preventing manual conversion errors.

---

#### mock-server.py

**Purpose**: Lightweight HTTP mock server for testing APIs with configurable routes, responses, and status codes. Runs as a background process.

**Location**: `~/.claude/tools/core/mock-server.py`

**Usage**:
```bash
# Start server
./tools/core/mock-server.py start --port 8080 --routes routes.json

# Stop server
./tools/core/mock-server.py stop --port 8080

# Status check
./tools/core/mock-server.py status --port 8080
```

**Example**:
```bash
cd ~/.claude

# Create routes configuration
cat > routes.json <<EOF
{
  "/api/users": {
    "method": "GET",
    "status": 200,
    "response": {"users": [{"id": 1, "name": "Alice"}]}
  },
  "/api/health": {
    "method": "GET",
    "status": 200,
    "response": {"status": "ok"}
  }
}
EOF

# Start mock server
./tools/core/mock-server.py start --port 8080 --routes routes.json

# Output:
{
  "success": true,
  "data": {
    "command": "start",
    "port": 8080,
    "pid": 12345,
    "routes": 2,
    "status": "running",
    "summary": "Mock server started on port 8080 with 2 routes"
  }
}

# Test endpoint
curl http://localhost:8080/api/users
# Returns: {"users": [{"id": 1, "name": "Alice"}]}
```

**Route Configuration**:
```json
{
  "/path": {
    "method": "GET|POST|PUT|DELETE",
    "status": 200,
    "response": {"key": "value"},
    "delay_ms": 100
  }
}
```

**Agent Use Case**: When frontend-developer builds UI components, mock-server provides realistic API responses for testing without requiring a running backend, enabling parallel development and isolated testing.

---

#### health-check.sh

**Purpose**: Self-test utility that verifies all 23 tools in the library are executable, functional, and return valid JSON output.

**Location**: `~/.claude/tools/core/health-check.sh`

**Usage**:
```bash
# Check all tools in ~/.claude/tools
./tools/core/health-check.sh

# Check tools in specific directory
./tools/core/health-check.sh /path/to/tools
```

**Example**:
```bash
cd ~/.claude
./tools/core/health-check.sh

# Output:
{
  "success": true,
  "data": {
    "total_tools": 23,
    "available": 23,
    "unavailable": 0,
    "errors": 0,
    "health_percentage": 100,
    "tools": [
      {
        "name": "secret-scanner.py",
        "category": "security",
        "status": "available",
        "version": "1.0.0"
      },
      {
        "name": "complexity-check.py",
        "category": "analysis",
        "status": "available",
        "version": "1.0.0"
      }
    ]
  },
  "errors": [],
  "metadata": {
    "tool": "health-check",
    "version": "1.0.0",
    "tools_directory": "/Users/h4ckm1n/.claude/tools"
  }
}
```

**Health Checks Performed**:
- Executable permission verification
- Help flag responsiveness (--help or -h)
- Exit code validation (0 for success)
- Cross-platform timeout handling

**Health Percentage**: (Available tools / Total tools) × 100

**Agent Use Case**: When deployment-engineer validates the agent environment before starting a project, health-check ensures all required tools are functional, preventing mid-execution failures due to missing or broken tools.

---

## Security Best Practices

### Command Injection Prevention

All tools in this library follow strict patterns to prevent command injection vulnerabilities:

**Python Tools**:
```python
# CORRECT: shell=False prevents command injection
subprocess.run(["git", "diff", filename], shell=False, capture_output=True)

# INCORRECT: shell=True allows injection
subprocess.run(f"git diff {filename}", shell=True)  # NEVER DO THIS
```

**Bash Tools**:
```bash
# CORRECT: Quote all variables
local filename="$1"
command --flag "$filename"

# INCORRECT: Unquoted variables allow injection
command --flag $filename  # VULNERABLE
```

### Path Traversal Protection

**Directory Validation Pattern**:
```python
def validate_path(path: str) -> bool:
    """Validate directory path to prevent traversal attacks"""
    try:
        resolved = Path(path).resolve()

        # Check path exists
        if not resolved.exists():
            return False

        # Check it's a directory (for directory-based tools)
        if not resolved.is_dir():
            return False

        # Prevent access to sensitive system directories
        sensitive_dirs = [
            '/etc', '/sys', '/proc', '/dev', '/root', '/boot',
            '/private/etc', '/private/var', '/System', '/Library'
        ]
        path_str = str(resolved)

        for sensitive in sensitive_dirs:
            if path_str == sensitive or path_str.startswith(sensitive + '/'):
                return False

        return True
    except Exception:
        return False
```

**Blocked Directories**:
- Linux: `/etc`, `/sys`, `/proc`, `/dev`, `/root`, `/boot`
- macOS: `/private/etc`, `/private/var`, `/System`, `/Library`
- Universal: `/root`, `~/.ssh`, `~/.aws`, `~/.kube`

### Input Validation Patterns

**Numeric Validation**:
```python
def validate_numeric(value: str, min_val: int = 1, max_val: int = 1000) -> int:
    """Validate numeric input with bounds"""
    try:
        num = int(value)
        if num < min_val or num > max_val:
            raise ValueError(f"Value must be between {min_val} and {max_val}")
        return num
    except ValueError:
        raise ValueError("Invalid numeric value")
```

**URL Validation with SSRF Prevention**:
```bash
validate_url() {
    local url="$1"

    # Check URL format
    if ! [[ "$url" =~ ^https?:// ]]; then
        echo "Error: URL must start with http:// or https://"
        return 1
    fi

    # Block localhost
    if [[ "$url" =~ localhost|127\.0\.0\.1|::1|0\.0\.0\.0 ]]; then
        echo "Error: Localhost URLs not allowed (SSRF prevention)"
        return 1
    fi

    # Block private IP ranges
    if [[ "$url" =~ 10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\. ]]; then
        echo "Error: Private IP ranges not allowed (SSRF prevention)"
        return 1
    fi

    return 0
}
```

### macOS-Specific Considerations

**Symlink Resolution**:
- macOS uses symlinks: `/etc` → `/private/etc`, `/tmp` → `/private/tmp`
- Always use `Path.resolve()` in Python or `readlink -f` in bash
- Block both the symlink path and the resolved path

**Bash Version**:
- macOS ships with bash 3.2 (released 2006)
- Avoid bash 4+ features: associative arrays, `readarray`, `&>>`
- Use portable patterns: `2>&1` instead of `&>`

**Date Command**:
- GNU date (Linux): `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- BSD date (macOS): `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- Workaround: Use Python for cross-platform timestamps

### Tool Development Guidelines

**Standard Output Structure**:
```json
{
  "success": true,
  "data": {
    // Tool-specific results
  },
  "errors": [
    {
      "type": "ValidationError",
      "message": "Descriptive error message"
    }
  ],
  "metadata": {
    "tool": "tool-name",
    "version": "1.0.0",
    "timestamp": "2025-11-06T12:34:56Z"
  }
}
```

**Error Types**:
- `ValidationError`: Invalid input (path, format, bounds)
- `RuntimeError`: Operation failed (tool not found, timeout)
- `PermissionError`: Access denied (file permissions)
- `FileNotFoundError`: Required file missing

**Exit Codes**:
- `0`: Success (success: true in JSON)
- `1`: Failure (success: false in JSON)

---

## Agent Integration Guide

### How Agents Invoke Tools

Agents use the `Bash` tool to invoke custom tools and parse JSON output:

**Example Agent Workflow**:
```python
# 1. Agent invokes tool via Bash
result = bash("""
cd ~/.claude
./tools/security/secret-scanner.py ./src
""")

# 2. Parse JSON output
import json
output = json.loads(result.stdout)

# 3. Check success status
if output["success"]:
    findings = output["data"]["findings"]

    # 4. Take action based on results
    if len(findings) > 0:
        # Create security issue
        for finding in findings:
            print(f"SECURITY: Found {finding['type']} in {finding['file']}:{finding['line']}")
else:
    # Handle errors
    for error in output["errors"]:
        print(f"ERROR: {error['type']}: {error['message']}")
```

### Parsing JSON Outputs

**Python Parsing**:
```python
import json

# Parse tool output
try:
    data = json.loads(tool_output)
    if data["success"]:
        # Access tool-specific data
        results = data["data"]
        print(f"Tool: {data['metadata']['tool']}")
    else:
        # Handle errors
        for error in data["errors"]:
            print(f"{error['type']}: {error['message']}")
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

**Bash Parsing (using jq)**:
```bash
# Extract specific fields with jq
./tools/security/secret-scanner.py ./src | jq -r '.data.summary'
# Output: "Found 3 potential secret(s) in 2 file(s)"

# Check success status
if ./tools/security/secret-scanner.py ./src | jq -e '.success' > /dev/null; then
    echo "Scan successful"
else
    echo "Scan failed"
fi

# Extract findings
./tools/security/secret-scanner.py ./src | jq -r '.data.findings[] | "\(.file):\(.line) - \(.type)"'
```

### Error Handling Strategies

**Graceful Degradation**:
```python
def scan_with_fallback(directory):
    """Try primary tool, fall back to alternative"""

    # Try secret-scanner (fast, comprehensive)
    result = run_tool("./tools/security/secret-scanner.py", directory)
    if result["success"]:
        return result["data"]

    # Fallback: manual regex scan
    print("WARNING: secret-scanner failed, using fallback")
    return manual_secret_scan(directory)
```

**Timeout Handling**:
```python
import subprocess

def run_tool_with_timeout(tool_path, args, timeout=30):
    """Execute tool with timeout protection"""
    try:
        result = subprocess.run(
            [tool_path] + args,
            capture_output=True,
            timeout=timeout,
            text=True
        )
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {
            "success": false,
            "errors": [{"type": "TimeoutError", "message": f"Tool exceeded {timeout}s timeout"}]
        }
    except Exception as e:
        return {
            "success": false,
            "errors": [{"type": type(e).__name__, "message": str(e)}]
        }
```

### Example Agent Workflows

**Security Audit Workflow** (security-practice-reviewer):
```python
def security_audit(codebase_path):
    """Comprehensive security audit using multiple tools"""

    issues = []

    # 1. Scan for secrets
    secrets = run_tool("./tools/security/secret-scanner.py", codebase_path)
    if secrets["data"]["findings"]:
        issues.append(f"Found {len(secrets['data']['findings'])} hardcoded secrets")

    # 2. Check file permissions
    perms = run_tool("./tools/security/permission-auditor.py", codebase_path)
    critical = perms["data"]["severity_counts"]["critical"]
    if critical > 0:
        issues.append(f"Found {critical} critical permission issues")

    # 3. Check dependencies
    if Path("package.json").exists():
        vulns = run_tool("./tools/security/vuln-checker.sh", "package.json")
        if vulns["data"]["vulnerabilities"]["critical"] > 0:
            issues.append("Critical vulnerabilities in dependencies")

    return issues
```

**Performance Analysis Workflow** (performance-profiler):
```python
def analyze_performance(metrics_file, logs_file):
    """Analyze performance using metrics and logs"""

    # 1. Compute response time statistics
    metrics = run_tool("./tools/data/metrics-aggregator.py", metrics_file)
    p95 = metrics["data"]["statistics"]["p95"]

    # 2. Extract error patterns from logs
    logs = run_tool("./tools/data/log-analyzer.py", logs_file)
    error_count = logs["data"]["log_levels"]["ERROR"]

    # 3. Identify bottlenecks
    if p95 > 1000:  # SLA: p95 < 1s
        print(f"PERFORMANCE: p95 latency {p95}ms exceeds SLA")

    if error_count > 100:
        print(f"RELIABILITY: {error_count} errors detected")

        # Show top error patterns
        for pattern in logs["data"]["error_patterns"][:5]:
            print(f"  - {pattern['pattern']} ({pattern['count']} times)")
```

**Test Quality Workflow** (test-engineer):
```python
def validate_test_quality(project_path, coverage_file):
    """Validate test suite meets quality thresholds"""

    # 1. Check code coverage
    coverage = run_tool("./tools/testing/coverage-reporter.py", coverage_file)
    line_coverage = coverage["data"]["line_coverage"]

    if line_coverage < 80:
        print(f"FAIL: Coverage {line_coverage}% below 80% threshold")
        return False

    # 2. Check for flaky tests
    flaky = run_tool("./tools/testing/flakiness-detector.py", "./test-results/*.xml")
    if flaky["data"]["flaky_tests"] > 0:
        print(f"WARNING: {flaky['data']['flaky_tests']} flaky tests detected")

    # 3. Run mutation testing
    mutation = run_tool("./tools/testing/mutation-score.sh", project_path, "mutmut")
    if mutation["data"]["score"] < 80:
        print(f"FAIL: Mutation score {mutation['data']['score']}% below 80%")
        return False

    return True
```

### Tool Chaining Examples

**Chain 1: Security Pipeline**:
```bash
#!/bin/bash
# Pre-deployment security pipeline

cd ~/.claude

# Step 1: Scan for secrets
echo "=== Scanning for secrets ==="
./tools/security/secret-scanner.py ./src > secrets.json

if jq -e '.data.findings | length > 0' secrets.json; then
    echo "BLOCKED: Secrets found in code"
    exit 1
fi

# Step 2: Check permissions
echo "=== Auditing permissions ==="
./tools/security/permission-auditor.py ./src > perms.json

if jq -e '.data.severity_counts.critical > 0' perms.json; then
    echo "BLOCKED: Critical permission issues"
    exit 1
fi

# Step 3: Validate certificates
echo "=== Validating SSL certificates ==="
./tools/security/cert-validator.sh api.example.com:443 > cert.json

if jq -e '.data.status == "expiring_soon"' cert.json; then
    echo "WARNING: Certificate expiring soon"
fi

echo "Security checks passed"
```

**Chain 2: Code Quality Pipeline**:
```bash
#!/bin/bash
# Code quality gate for pull requests

cd ~/.claude

# Step 1: Check complexity
echo "=== Checking complexity ==="
./tools/analysis/complexity-check.py ./src/*.py --threshold 10 > complexity.json

if jq -e '.data.functions[] | select(.grade > "C")' complexity.json; then
    echo "WARNING: High complexity functions detected"
fi

# Step 2: Check for duplication
echo "=== Detecting duplication ==="
./tools/analysis/duplication-detector.py ./src --window 5 > duplication.json

# Step 3: Analyze imports
echo "=== Analyzing imports ==="
./tools/analysis/import-analyzer.py ./src > imports.json

if jq -e '.data.circular_dependencies | length > 0' imports.json; then
    echo "BLOCKED: Circular dependencies detected"
    exit 1
fi

echo "Code quality checks passed"
```

---

## Installation & Dependencies

### Python Dependencies

Most tools use only Python standard library. Optional dependencies provide enhanced functionality:

**Optional (Recommended)**:
```bash
# Install optional dependencies for enhanced features
pip install psutil requests pyyaml

# psutil: Used by resource-monitor.py
# requests: Used for HTTP health checks (fallback to curl)
# pyyaml: Used by file-converter.py for YAML support
```

**External Tools (Optional)**:
```bash
# Python analysis tools
pip install radon        # Used by complexity-check.py (fallback to AST)
pip install jscpd        # Used by duplication-detector.py (fallback to hash-based)
pip install mutmut       # Used by mutation-score.sh (Python projects)
pip install safety       # Used by vuln-checker.sh (Python dependencies)

# JavaScript/TypeScript tools
npm install -g @stryker-mutator/core  # Used by mutation-score.sh (JS/TS projects)
```

### Bash Requirements

**Required**:
- bash 3.2+ (macOS default) or bash 4.0+ (Linux)
- Standard POSIX utilities: `grep`, `sed`, `awk`, `find`, `sort`

**Optional**:
- `shellcheck`: Bash script linting (development only)
- `jq`: JSON parsing in bash scripts (highly recommended)
- `gtimeout` (macOS): GNU timeout via Homebrew (`brew install coreutils`)

### Platform Considerations

**macOS**:
```bash
# Install Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install optional tools
brew install coreutils  # Provides gtimeout
brew install jq         # JSON processing
brew install shellcheck # Bash linting
```

**Linux (Debian/Ubuntu)**:
```bash
# Install optional tools
sudo apt-get update
sudo apt-get install jq shellcheck
```

**Verify Installation**:
```bash
# Check Python version (3.7+ required)
python3 --version

# Check bash version
bash --version

# Run health check
cd ~/.claude
./tools/core/health-check.sh
```

---

## Troubleshooting

### Common Errors

#### "Tool not found" or "Command not found"

**Symptom**: `bash: ./tools/security/secret-scanner.py: No such file or directory`

**Cause**: Tool not executable or path incorrect

**Fix**:
```bash
# Make all tools executable
cd ~/.claude
find tools/ -name "*.py" -o -name "*.sh" | xargs chmod +x

# Verify permissions
ls -la tools/security/secret-scanner.py
# Should show: -rwxr-xr-x
```

#### "Invalid JSON" or JSON Parsing Failures

**Symptom**: `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**Cause**: Tool printed error to stdout instead of JSON, or tool crashed

**Fix**:
```bash
# Run tool manually to see raw output
cd ~/.claude
./tools/security/secret-scanner.py ./src

# Check for error messages before JSON
# If seeing Python traceback, file a bug report with full output
```

#### Permission Denied Errors

**Symptom**: `PermissionError: [Errno 13] Permission denied: '/path/to/file'`

**Cause**: Tool trying to access restricted directory or file

**Fix**:
```bash
# Check file permissions
ls -la /path/to/file

# Ensure current user has read access
# For security tools, this is expected behavior for system directories

# Use appropriate directory for testing
cd ~/.claude
./tools/security/secret-scanner.py ./src  # OK
./tools/security/secret-scanner.py /etc   # BLOCKED (by design)
```

#### Missing Optional Dependencies

**Symptom**: `ModuleNotFoundError: No module named 'psutil'`

**Cause**: Optional Python package not installed

**Fix**:
```bash
# Install missing package
pip install psutil

# Or install all optional dependencies
pip install psutil requests pyyaml

# Verify installation
python3 -c "import psutil; print('OK')"
```

#### Timeout Errors on Slow Systems

**Symptom**: Tool exceeds default timeout (5 seconds)

**Cause**: Large codebases or slow disk I/O

**Fix**:
```bash
# Increase timeout for specific tools
# Example: service-health.sh
./tools/devops/service-health.sh https://slow-api.com 30  # 30-second timeout

# For Python tools, timeout is built-in (no parameter)
# Consider scanning smaller directories or improving disk I/O
```

#### Health Check Reports Unavailable Tools

**Symptom**: `health-check.sh` shows tools as "unavailable"

**Cause**: Tools missing execute permission or syntax errors

**Fix**:
```bash
# Run health check with details
cd ~/.claude
./tools/core/health-check.sh | jq '.data.tools[] | select(.status != "available")'

# Check specific tool
./tools/security/secret-scanner.py --help

# Fix permissions if needed
chmod +x tools/security/secret-scanner.py
```

### Platform-Specific Issues

**macOS: "date: illegal option" Error**

**Symptom**: Bash tools fail with date command errors

**Cause**: BSD date vs GNU date syntax differences

**Fix**: Tools use portable date syntax, but if you encounter issues:
```bash
# Install GNU coreutils (provides gdate)
brew install coreutils

# Use gdate instead of date
gdate -u +"%Y-%m-%dT%H:%M:%SZ"
```

**macOS: Bash 3.2 Compatibility**

**Symptom**: Bash tools fail with "declare: -A: invalid option"

**Cause**: Associative arrays require bash 4.0+

**Fix**: All tools in this library are bash 3.2 compatible. If you encounter this error, file a bug report.

**Linux: Missing timeout Command**

**Symptom**: `timeout: command not found`

**Cause**: timeout utility not in PATH

**Fix**:
```bash
# Install coreutils (usually pre-installed)
sudo apt-get install coreutils

# Verify timeout is available
which timeout
```

### Getting Help

**Check Tool Documentation**:
```bash
# All tools support --help
./tools/security/secret-scanner.py --help
./tools/devops/docker-manager.sh --help
```

**Validate JSON Output**:
```bash
# Pipe tool output through jq for validation
./tools/security/secret-scanner.py ./src | jq '.'

# Check for success status
./tools/security/secret-scanner.py ./src | jq '.success'
```

**Run Health Check**:
```bash
# Verify all tools are functional
cd ~/.claude
./tools/core/health-check.sh

# Check specific category
ls -la tools/security/
```

**Enable Debug Mode** (for developers):
```bash
# Add set -x to bash tools for debugging
bash -x ./tools/devops/docker-manager.sh list-containers

# Add print statements to Python tools
# (Edit tool file temporarily)
```

---

## Summary

The Custom Tools Library provides 23 production-ready tools organized into 6 categories (Security, Analysis, Testing, Data, DevOps, Core). Each tool follows strict security patterns, returns standardized JSON output, and integrates seamlessly with Claude Code's autonomous agent ecosystem.

**Key Features**:
- Security-first design (no command injection, path traversal protection)
- Consistent JSON output format for easy parsing
- Comprehensive error handling with actionable messages
- Cross-platform support (macOS and Linux)
- Agent-friendly (batch processing, silent operation)

**Quick Reference**:
- **Security**: secret-scanner, permission-auditor, cert-validator, vuln-checker
- **Analysis**: complexity-check, type-coverage, duplication-detector, import-analyzer
- **Testing**: coverage-reporter, test-selector, mutation-score, flakiness-detector
- **Data**: log-analyzer, sql-explain, metrics-aggregator
- **DevOps**: docker-manager, env-manager, service-health, ci-status, resource-monitor
- **Core**: file-converter, mock-server, health-check

For agent integration examples, see the [Agent Integration Guide](#agent-integration-guide) section.

For security guidelines, see the [Security Best Practices](#security-best-practices) section.

For troubleshooting, see the [Troubleshooting](#troubleshooting) section.

**Happy tool building!**
