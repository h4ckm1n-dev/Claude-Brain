#!/usr/bin/env bash
# Tool Name: integration-test.sh
# Purpose: Validate that all tools in the ecosystem work correctly
# Security: Safe test data, timeout protection, no real API calls
# Usage:
#   ./integration-test.sh                    # Run full test suite
#   ./integration-test.sh --verbose          # Show detailed output
#   ./integration-test.sh --help             # Show help message

set -euo pipefail

# Configuration
CLAUDE_HOME="${HOME}/.claude"
TIMEOUT=10
VERBOSE=false

# Counters
total_tests=0
passed_tests=0

# Colors for output (if terminal supports it)
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    GREEN=''
    RED=''
    YELLOW=''
    NC=''
fi

# Help message
show_help() {
    cat << EOF
Integration Test Suite - Validate ecosystem tools

USAGE:
    integration-test.sh [OPTIONS]

OPTIONS:
    --verbose       Show detailed test output
    --help          Show this help message

DESCRIPTION:
    Tests representative tools from each category:
    - Security tools (2 tests)
    - DevOps tools (2 tests)
    - Analysis tools (2 tests)
    - Testing tools (1 test)
    - Data tools (1 test)
    - Core tools (1 test)

    Pass rate >90% = success (exit 0)
    Pass rate <90% = failure (exit 1)

EXAMPLES:
    # Run all tests
    ./integration-test.sh

    # Run with verbose output
    ./integration-test.sh --verbose

    # Check exit code
    ./integration-test.sh && echo "PASS" || echo "FAIL"
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            echo "Use --help for usage information" >&2
            exit 2
            ;;
    esac
done

# Cross-platform timeout function
run_with_timeout() {
    local timeout_duration="$1"
    shift

    # Try using gtimeout (GNU coreutils on macOS via brew)
    if command -v gtimeout &> /dev/null; then
        gtimeout "$timeout_duration" "$@"
        return $?
    fi

    # Try using timeout (Linux)
    if command -v timeout &> /dev/null; then
        timeout "$timeout_duration" "$@"
        return $?
    fi

    # Fallback: just run without timeout
    "$@"
    return $?
}

# Helper: Test a tool
# Usage: test_tool "tool-name.py" "command to run"
test_tool() {
    local tool_name="$1"
    local command="$2"

    ((total_tests++)) || true

    # Show test start if verbose
    if [[ "$VERBOSE" == true ]]; then
        echo -e "  ${YELLOW}Testing: $tool_name${NC}" >&2
    fi

    # Run tool with timeout and capture output (stdout only, suppress stderr warnings)
    local output
    local exit_code=0

    # Capture stdout only, discard stderr (which may contain warnings)
    output=$(eval "run_with_timeout '$TIMEOUT' $command 2>/dev/null") || exit_code=$?

    # For verbose mode, also capture stderr to show errors
    local stderr_output=""
    if [[ "$VERBOSE" == true && $exit_code -ne 0 ]]; then
        stderr_output=$(eval "$command 2>&1 >/dev/null" || true)
    fi

    # Check if output is valid JSON
    if echo "$output" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
        echo -e "  ${GREEN}✅ $tool_name${NC}"
        ((passed_tests++)) || true

        if [[ "$VERBOSE" == true ]]; then
            echo "     Exit code: $exit_code" >&2
            echo "     JSON: valid" >&2
        fi
    else
        echo -e "  ${RED}❌ $tool_name - invalid JSON or execution failed${NC}"

        if [[ "$VERBOSE" == true ]]; then
            echo "     Exit code: $exit_code" >&2
            if [[ -n "$stderr_output" ]]; then
                echo "     Error: ${stderr_output:0:100}..." >&2
            fi
            echo "     Output: ${output:0:100}..." >&2
        fi
    fi
}

# Main test suite
echo -e "${YELLOW}🧪 Integration Test Suite${NC}"
echo ""

# Security tools (test 2)
echo -e "${YELLOW}Security Tools:${NC}"
test_tool "secret-scanner.py" "python3 '$CLAUDE_HOME/tools/security/secret-scanner.py' '$CLAUDE_HOME/tools'"
test_tool "permission-auditor.py" "python3 '$CLAUDE_HOME/tools/security/permission-auditor.py' '$CLAUDE_HOME/tools'"
echo ""

# DevOps tools (test 2)
echo -e "${YELLOW}DevOps Tools:${NC}"
test_tool "service-health.sh" "'$CLAUDE_HOME/tools/devops/service-health.sh' 'https://example.com'"
test_tool "env-manager.py" "python3 '$CLAUDE_HOME/tools/devops/env-manager.py' '$CLAUDE_HOME/.test.env'"
echo ""

# Analysis tools (test 2)
echo -e "${YELLOW}Analysis Tools:${NC}"
test_tool "complexity-check.py" "python3 '$CLAUDE_HOME/tools/analysis/complexity-check.py' '$CLAUDE_HOME/tools'"
test_tool "import-analyzer.py" "python3 '$CLAUDE_HOME/tools/analysis/import-analyzer.py' '$CLAUDE_HOME/tools'"
echo ""

# Testing tools (test 1)
echo -e "${YELLOW}Testing Tools:${NC}"
test_tool "test-selector.py" "python3 '$CLAUDE_HOME/tools/testing/test-selector.py' '$CLAUDE_HOME/tools'"
echo ""

# Data tools (test 1)
echo -e "${YELLOW}Data Tools:${NC}"
test_tool "log-analyzer.py" "python3 '$CLAUDE_HOME/tools/data/log-analyzer.py' '$CLAUDE_HOME/.tool-usage.log'"
echo ""

# Core tools (test 1)
echo -e "${YELLOW}Core Tools:${NC}"
test_tool "health-check.sh" "'$CLAUDE_HOME/tools/core/health-check.sh'"
echo ""

# Summary
if [[ $total_tests -eq 0 ]]; then
    echo -e "${RED}Error: No tests were run${NC}" >&2
    exit 1
fi

pass_rate=$((passed_tests * 100 / total_tests))
echo "---"
echo -e "${YELLOW}Summary:${NC} $passed_tests/$total_tests tools passed (${pass_rate}%)"

if [[ $pass_rate -ge 90 ]]; then
    echo -e "${GREEN}✅ Integration tests PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ Integration tests FAILED${NC}"
    echo -e "${YELLOW}Tip: Run with --verbose for detailed output${NC}" >&2
    exit 1
fi
