#!/usr/bin/env bash
# Tool Name: service-health.sh
# Purpose: Check health endpoints, measure response times, validate status codes
# Security: URL validation, timeout handling, safe command execution
#
# Usage:
#   ./service-health.sh <url> [timeout]
#
# Example:
#   ./service-health.sh https://example.com
#   ./service-health.sh https://api.example.com/health 10
#   ./service-health.sh http://localhost:8080/health 3
#
# Output:
#   JSON with structure: {"success": true/false, "data": {}, "errors": [], "metadata": {}}

# Strict mode - exit on error, undefined variables, pipe failures
set -euo pipefail

# Tool metadata
TOOL_NAME="service-health"
TOOL_VERSION="1.0.0"

# Default timeout in seconds
DEFAULT_TIMEOUT=5

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
Usage: $(basename "$0") <url> [timeout]

Description:
    Check health endpoints and measure response times.
    Supports HTTP/HTTPS endpoints with customizable timeouts.

Arguments:
    url         URL to check (e.g., https://example.com/health)
    timeout     Optional timeout in seconds (default: 5)

Examples:
    $(basename "$0") https://example.com
    $(basename "$0") https://api.example.com/health
    $(basename "$0") http://localhost:8080/health 10

Output:
    JSON format: {"success": bool, "data": {}, "errors": [], "metadata": {}}

Requirements:
    - curl (usually pre-installed on macOS/Linux)
EOF
}

#######################################
# Validate URL format
# Arguments:
#   $1 - URL to validate
# Returns:
#   0 if valid, 1 if invalid
#######################################
validate_url() {
    local url="$1"

    # Check URL scheme
    if [[ ! "$url" =~ ^https?:// ]]; then
        return 1
    fi

    # Block localhost and loopback addresses (SSRF prevention)
    if echo "$url" | grep -qiE "localhost|127\.[0-9]+\.[0-9]+\.[0-9]+|::1|0\.0\.0\.0"; then
        return 1
    fi

    # Block private IP ranges (SSRF prevention)
    # 10.x.x.x, 172.16-31.x.x, 192.168.x.x
    if echo "$url" | grep -qE "//10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|//172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}|//192\.168\.[0-9]{1,3}\.[0-9]{1,3}"; then
        return 1
    fi

    # Basic URL format validation
    if [[ ! "$url" =~ ^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$ ]]; then
        return 1
    fi

    return 0
}

#######################################
# Validate timeout is numeric
# Arguments:
#   $1 - Timeout value to validate
# Returns:
#   0 if valid, 1 if invalid
#######################################
validate_timeout() {
    local timeout="$1"

    # Check if numeric
    if ! [[ "$timeout" =~ ^[0-9]+$ ]]; then
        return 1
    fi

    # Check reasonable range (1-300 seconds)
    if [[ "$timeout" -lt 1 ]] || [[ "$timeout" -gt 300 ]]; then
        return 1
    fi

    return 0
}

#######################################
# Get current time in milliseconds
# Returns:
#   Milliseconds since epoch (cross-platform)
#######################################
get_time_ms() {
    # Use Python for cross-platform millisecond precision
    python3 -c "import time; print(int(time.time() * 1000))"
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
    local data; if [[ -n "${2:-}" ]]; then data="$2"; else data="{}"; fi
    local errors; if [[ -n "${3:-}" ]]; then errors="$3"; else errors="[]"; fi
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

    # Escape quotes in error message
    error_message="${error_message//\"/\\\"}"

    create_json_output "false" "{}" "[{\"type\": \"$error_type\", \"message\": \"$error_message\"}]"
}

#######################################
# Determine health status from HTTP code
# Arguments:
#   $1 - HTTP status code
# Returns:
#   Status string (healthy/degraded/unhealthy/unreachable)
#######################################
determine_status() {
    local http_code="$1"

    if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
        echo "healthy"
    elif [[ "$http_code" -ge 300 && "$http_code" -lt 400 ]]; then
        echo "degraded"
    elif [[ "$http_code" == "000" ]]; then
        echo "unreachable"
    else
        echo "unhealthy"
    fi
}

#######################################
# Check service health
# Arguments:
#   $1 - URL to check
#   $2 - Timeout in seconds
# Outputs:
#   JSON health check result
#######################################
check_health() {
    local url="$1"
    local timeout="$2"

    # Temporary files for response headers and body
    local temp_headers
    local temp_body
    temp_headers=$(mktemp)
    temp_body=$(mktemp)

    # Ensure cleanup
    trap 'rm -f "$temp_headers" "$temp_body"' RETURN

    # Measure start time (milliseconds)
    local start_time
    start_time=$(get_time_ms)

    # Execute curl with timeout
    local http_code
    local curl_exit_code=0
    http_code=$(curl -s -o "$temp_body" -D "$temp_headers" -w "%{http_code}" -m "$timeout" --connect-timeout "$timeout" "$url" 2>/dev/null) || curl_exit_code=$?

    # Measure end time
    local end_time
    end_time=$(get_time_ms)

    # Calculate response time
    local response_time=$((end_time - start_time))

    # Determine status
    local status
    status=$(determine_status "$http_code")

    # Extract content type
    local content_type=""
    if [[ -f "$temp_headers" ]]; then
        content_type=$(grep -i "^content-type:" "$temp_headers" | cut -d: -f2- | tr -d '\r\n' | xargs || echo "unknown")
    fi

    # Read response body (limit to 1KB)
    local body=""
    if [[ -f "$temp_body" ]]; then
        body=$(head -c 1024 "$temp_body" | jq -Rs '.' 2>/dev/null || echo '""')
    else
        body='""'
    fi

    # Build data object
    local data
    data=$(cat <<EOF
{
  "url": $(printf "%s" "$url" | jq -Rs '.'),
  "status": "$status",
  "http_code": $http_code,
  "response_time_ms": $response_time,
  "content_type": $(printf "%s" "$content_type" | jq -Rs '.'),
  "curl_exit_code": $curl_exit_code,
  "timeout_seconds": $timeout,
  "body_preview": $body
}
EOF
)

    create_json_output "true" "$data" "[]"
}

#######################################
# Main function
# Arguments:
#   $@ - URL and optional timeout
# Outputs:
#   JSON result to stdout
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
    # Check if help requested
    if [[ $# -eq 0 ]] || [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        usage
        exit 0
    fi

    # Check required dependencies
    if ! command -v curl &> /dev/null; then
        output_error "DependencyError" "curl is not installed"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        output_error "DependencyError" "python3 is required for millisecond precision"
        exit 1
    fi

    # Parse arguments
    local url="${1:-}"
    local timeout="${2:-$DEFAULT_TIMEOUT}"

    # Validate URL
    if [[ -z "$url" ]]; then
        output_error "ValidationError" "URL is required"
        exit 1
    fi

    if ! validate_url "$url"; then
        output_error "ValidationError" "Invalid URL format: $url (must start with http:// or https://)"
        exit 1
    fi

    # Validate timeout
    if ! validate_timeout "$timeout"; then
        output_error "ValidationError" "Invalid timeout: $timeout (must be numeric, 1-300 seconds)"
        exit 1
    fi

    # Check health
    check_health "$url" "$timeout"
    exit 0
}

# Execute main function
main "$@"
