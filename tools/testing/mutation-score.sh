#!/usr/bin/env bash
#
# Tool Name: mutation-score.sh
# Purpose: Calculate mutation testing scores using mutmut (Python) or stryker (JS/TS)
# Security: Safe subprocess execution, input validation, quoted variables
#
# Usage:
#     ./mutation-score.sh <directory>
#
# Example:
#     ./mutation-score.sh src/
#     ./mutation-score.sh lib/
#
# Output:
#     JSON with structure: {"success": bool, "data": {}, "errors": [], "metadata": {}}

set -euo pipefail

# Tool metadata
TOOL_NAME="mutation-score"
TOOL_VERSION="1.0.0"

# Get current timestamp in ISO 8601 UTC format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Create standardized JSON output
create_json_output() {
    local success="$1"
    local data="${2:-{}}"
    local errors="${3:-[]}"
    local timestamp
    timestamp=$(get_timestamp)

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

# Create error output
output_error() {
    local error_type="$1"
    local error_message="$2"

    local errors
    errors=$(cat <<EOF
[
  {
    "type": "$error_type",
    "message": "$error_message"
  }
]
EOF
)
    create_json_output "false" "{}" "$errors"
}

# Validate directory path
validate_path() {
    local path="$1"

    # Check if path exists
    if [[ ! -e "$path" ]]; then
        return 1
    fi

    # Check if it's a directory
    if [[ ! -d "$path" ]]; then
        return 1
    fi

    # Prevent access to sensitive directories (macOS-aware)
    local sensitive_dirs=(
        "/etc"
        "/sys"
        "/proc"
        "/dev"
        "/root"
        "/boot"
        "/private/etc"
        "/System"
        "/Library"
    )

    local resolved_path
    resolved_path=$(cd "$path" && pwd -P)

    for sensitive in "${sensitive_dirs[@]}"; do
        if [[ "$resolved_path" == "$sensitive"* ]]; then
            return 1
        fi
    done

    return 0
}

# Parse mutmut JSON output
parse_mutmut_results() {
    local mutmut_output="$1"

    # Extract mutation score from mutmut output
    # mutmut results shows: killed, survived, timeout, suspicious

    if echo "$mutmut_output" | grep -q "No mutants"; then
        echo '{"total_mutants": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0, "mutation_score": 100.0, "tool": "mutmut", "note": "No mutants generated"}'
        return 0
    fi

    # Try to parse as JSON if mutmut outputs JSON
    if echo "$mutmut_output" | jq empty 2>/dev/null; then
        echo "$mutmut_output"
        return 0
    fi

    # Parse text output
    local killed=0
    local survived=0
    local timeout=0
    local suspicious=0

    if echo "$mutmut_output" | grep -q "killed"; then
        killed=$(echo "$mutmut_output" | grep -oP '\d+(?= killed)' || echo "0")
    fi

    if echo "$mutmut_output" | grep -q "survived"; then
        survived=$(echo "$mutmut_output" | grep -oP '\d+(?= survived)' || echo "0")
    fi

    if echo "$mutmut_output" | grep -q "timeout"; then
        timeout=$(echo "$mutmut_output" | grep -oP '\d+(?= timeout)' || echo "0")
    fi

    if echo "$mutmut_output" | grep -q "suspicious"; then
        suspicious=$(echo "$mutmut_output" | grep -oP '\d+(?= suspicious)' || echo "0")
    fi

    local total=$((killed + survived + timeout + suspicious))
    local score=0

    if [[ $total -gt 0 ]]; then
        score=$(awk "BEGIN {printf \"%.2f\", ($killed / $total) * 100}")
    fi

    cat <<EOF
{
  "total_mutants": $total,
  "killed": $killed,
  "survived": $survived,
  "timeout": $timeout,
  "suspicious": $suspicious,
  "mutation_score": $score,
  "tool": "mutmut"
}
EOF
}

# Parse stryker JSON output
parse_stryker_results() {
    local stryker_output="$1"

    # Stryker outputs JSON by default
    if echo "$stryker_output" | jq empty 2>/dev/null; then
        # Transform stryker output to standard format
        echo "$stryker_output" | jq '{
            total_mutants: .totalMutants,
            killed: .killed,
            survived: .survived,
            timeout: .timeout,
            no_coverage: .noCoverage,
            mutation_score: .mutationScore,
            tool: "stryker"
        }'
        return 0
    fi

    echo '{"total_mutants": 0, "killed": 0, "survived": 0, "mutation_score": 0, "tool": "stryker", "note": "Unable to parse stryker output"}'
}

# Run mutation testing
run_mutation_testing() {
    local directory="$1"

    # Check for mutmut (Python)
    if command -v mutmut &> /dev/null; then
        # Run mutmut
        local output
        output=$(mutmut run --paths-to-mutate="$directory" 2>&1 || true)

        # Get results
        local results
        results=$(mutmut results 2>&1 || echo "No results available")

        parse_mutmut_results "$results"
        return 0
    fi

    # Check for stryker (JS/TS)
    if command -v stryker &> /dev/null; then
        # Run stryker
        local output
        output=$(cd "$directory" && stryker run --concurrency 4 2>&1 || true)

        parse_stryker_results "$output"
        return 0
    fi

    # Neither tool found - provide installation instructions
    local setup_instructions
    setup_instructions=$(cat <<'EOF_INSTRUCTIONS'
{
  "tools_available": false,
  "instructions": {
    "python": {
      "tool": "mutmut",
      "install": "pip install mutmut",
      "usage": "mutmut run --paths-to-mutate=src/"
    },
    "javascript": {
      "tool": "stryker",
      "install": "npm install --save-dev @stryker-mutator/core",
      "usage": "stryker run"
    },
    "typescript": {
      "tool": "stryker",
      "install": "npm install --save-dev @stryker-mutator/core @stryker-mutator/typescript-checker",
      "usage": "stryker run"
    }
  },
  "note": "No mutation testing tools found. Install mutmut (Python) or stryker (JS/TS) to run mutation tests."
}
EOF_INSTRUCTIONS
)

    echo "$setup_instructions"
}

# Main function
main() {
    # Validate arguments
    if [[ $# -lt 1 ]]; then
        output_error "ValidationError" "Missing required argument: directory"
        exit 1
    fi

    local directory="$1"

    # Validate path
    if ! validate_path "$directory"; then
        output_error "ValidationError" "Invalid or inaccessible directory: $directory"
        exit 1
    fi

    # Run mutation testing
    local results
    results=$(run_mutation_testing "$directory")

    # Create success output
    create_json_output "true" "$results" "[]"
    exit 0
}

# Execute main
main "$@"
