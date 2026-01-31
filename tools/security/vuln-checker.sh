#!/usr/bin/env bash
# Tool Name: vuln-checker.sh
# Purpose: Check dependencies for known vulnerabilities
# Security: Input validation, safe command execution, proper quoting
#
# Usage:
#   ./vuln-checker.sh <package-file>
#
# Example:
#   ./vuln-checker.sh package.json
#   ./vuln-checker.sh requirements.txt
#
# Output:
#   JSON with structure: {"success": true/false, "data": {}, "errors": [], "metadata": {}}

# Strict mode - exit on error, undefined variables, pipe failures
set -euo pipefail

# Tool metadata
TOOL_NAME="vuln-checker"
TOOL_VERSION="1.0.0"

#######################################
# Display usage information
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   Usage text to stdout
#######################################
usage() {
    cat <<EOF
Usage: $(basename "$0") <package-file>

Description:
    Check dependencies for known vulnerabilities using npm audit (for package.json)
    or safety check (for requirements.txt).

Arguments:
    package-file    Package file to check (package.json or requirements.txt)

Examples:
    $(basename "$0") package.json
    $(basename "$0") requirements.txt

Output:
    JSON format: {"success": bool, "data": {}, "errors": [], "metadata": {}}

Requirements:
    - npm (for package.json)
    - safety (for requirements.txt): pip install safety
EOF
}

#######################################
# Validate file path exists and is safe
# Arguments:
#   $1 - Path to validate
# Returns:
#   0 if valid, 1 if invalid
#######################################
validate_path() {
    local path="$1"

    # Check if path exists
    if [[ ! -f "$path" ]]; then
        return 1
    fi

    # Ensure it's a regular file, not a symlink to sensitive location
    if [[ -L "$path" ]]; then
        return 1
    fi

    return 0
}

#######################################
# Create standardized JSON output
# Arguments:
#   $1 - success (true/false)
#   $2 - data (JSON string or empty)
#   $3 - errors (JSON array string or empty)
# Outputs:
#   JSON to stdout
#######################################
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

#######################################
# Create error output
# Arguments:
#   $1 - error type
#   $2 - error message
# Outputs:
#   JSON error to stdout
#######################################
output_error() {
    local error_type="$1"
    local error_message="$2"

    create_json_output "false" "{}" "[{\"type\": \"$error_type\", \"message\": \"$error_message\"}]"
}

#######################################
# Check vulnerabilities using npm audit
# Arguments:
#   $1 - path to package.json
# Outputs:
#   JSON audit results
# Returns:
#   0 on success, 1 on failure
#######################################
check_npm_vulnerabilities() {
    local package_file="$1"
    local package_dir
    package_dir=$(dirname "$package_file")

    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        output_error "DependencyError" "npm is not installed. Please install Node.js and npm."
        return 1
    fi

    # Check if package-lock.json or node_modules exists
    local package_lock="$package_dir/package-lock.json"
    local node_modules="$package_dir/node_modules"

    if [[ ! -f "$package_lock" ]] && [[ ! -d "$node_modules" ]]; then
        output_error "ConfigurationError" "No package-lock.json or node_modules found. Run 'npm install' first."
        return 1
    fi

    # Run npm audit with JSON output
    local audit_output
    local audit_exit_code=0

    # Change to package directory and run audit
    # npm audit returns non-zero if vulnerabilities found, so we capture output regardless
    audit_output=$(cd "$package_dir" && npm audit --json 2>&1) || audit_exit_code=$?

    # npm audit returns 0 (no vulns), 1 (vulns found), or other (error)
    if [[ $audit_exit_code -gt 1 ]]; then
        output_error "RuntimeError" "npm audit failed: $audit_output"
        return 1
    fi

    # Parse the audit output
    local vulnerabilities
    local summary

    # Extract vulnerability counts
    vulnerabilities=$(echo "$audit_output" | jq -c '.vulnerabilities // {}')
    summary=$(echo "$audit_output" | jq -c '.metadata // {}')

    # Create data object
    local data
    data=$(cat <<EOF_DATA
{
  "package_manager": "npm",
  "package_file": "$package_file",
  "vulnerabilities": $vulnerabilities,
  "summary": $summary,
  "has_vulnerabilities": $([ $audit_exit_code -eq 1 ] && echo "true" || echo "false")
}
EOF_DATA
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Check vulnerabilities using safety
# Arguments:
#   $1 - path to requirements.txt
# Outputs:
#   JSON safety results
# Returns:
#   0 on success, 1 on failure
#######################################
check_python_vulnerabilities() {
    local requirements_file="$1"

    # Check if safety is installed
    if ! command -v safety &> /dev/null; then
        output_error "DependencyError" "safety is not installed. Install with: pip install safety"
        return 1
    fi

    # Run safety check with JSON output
    local safety_output
    local safety_exit_code=0

    # safety check returns non-zero if vulnerabilities found
    safety_output=$(safety check --file "$requirements_file" --json 2>&1) || safety_exit_code=$?

    # safety returns 64 if vulns found, 0 if none, other codes for errors
    if [[ $safety_exit_code -ne 0 ]] && [[ $safety_exit_code -ne 64 ]]; then
        output_error "RuntimeError" "safety check failed: $safety_output"
        return 1
    fi

    # Parse safety output
    local vulnerabilities
    vulnerabilities=$(echo "$safety_output" | jq -c '.')

    # Count vulnerabilities
    local vuln_count
    vuln_count=$(echo "$vulnerabilities" | jq 'length')

    # Create data object
    local data
    data=$(cat <<EOF_DATA
{
  "package_manager": "pip",
  "package_file": "$requirements_file",
  "vulnerabilities": $vulnerabilities,
  "vulnerability_count": $vuln_count,
  "has_vulnerabilities": $([ "$vuln_count" -gt 0 ] && echo "true" || echo "false")
}
EOF_DATA
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Main entry point
#######################################
main() {
    # Handle help flag
    if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        usage
        exit 0
    fi

    # Validate required arguments
    if [[ $# -lt 1 ]]; then
        output_error "ValidationError" "Missing required argument. Use --help for usage."
        exit 1
    fi

    # Parse arguments
    local package_file="$1"

    # Validate file exists
    if ! validate_path "$package_file"; then
        output_error "ValidationError" "Invalid or non-existent file: $package_file"
        exit 1
    fi

    # Detect package manager from filename
    local filename
    filename=$(basename "$package_file")

    if [[ "$filename" == "package.json" ]]; then
        # Check npm vulnerabilities
        if check_npm_vulnerabilities "$package_file"; then
            exit 0
        else
            exit 1
        fi
    elif [[ "$filename" == "requirements.txt" ]]; then
        # Check Python vulnerabilities
        if check_python_vulnerabilities "$package_file"; then
            exit 0
        else
            exit 1
        fi
    else
        output_error "ValidationError" "Unsupported package file. Supported: package.json, requirements.txt"
        exit 1
    fi
}

# Execute main function
main "$@"
