#!/usr/bin/env bash
# Tool Name: cert-validator.sh
# Purpose: Validate SSL/TLS certificates
# Security: Input validation, safe command execution, proper quoting
#
# Usage:
#   ./cert-validator.sh <cert-file|url>
#
# Example:
#   ./cert-validator.sh /path/to/certificate.crt
#   ./cert-validator.sh https://example.com:443
#
# Output:
#   JSON with structure: {"success": true/false, "data": {}, "errors": [], "metadata": {}}

# Strict mode - exit on error, undefined variables, pipe failures
set -euo pipefail

# Tool metadata
TOOL_NAME="cert-validator"
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
Usage: $(basename "$0") <cert-file|url>

Description:
    Validate SSL/TLS certificates and check expiration.
    Supports both local certificate files and remote URLs.

Arguments:
    cert-file    Path to certificate file (.crt, .pem)
    url          HTTPS URL (e.g., https://example.com:443)

Examples:
    $(basename "$0") /etc/ssl/certs/example.crt
    $(basename "$0") https://example.com:443
    $(basename "$0") example.com:443

Output:
    JSON format: {"success": bool, "data": {}, "errors": [], "metadata": {}}

Requirements:
    - openssl (usually pre-installed on macOS/Linux)
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

    # Ensure it's a regular file
    if [[ -L "$path" ]]; then
        return 1
    fi

    return 0
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

    # Basic URL validation (host:port or https://host:port)
    if [[ "$url" =~ ^https?://[a-zA-Z0-9.-]+:[0-9]+$ ]] || [[ "$url" =~ ^[a-zA-Z0-9.-]+:[0-9]+$ ]]; then
        return 0
    fi

    return 1
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

    # Escape quotes in error message
    error_message="${error_message//\"/\\\"}"

    create_json_output "false" "{}" "[{\"type\": \"$error_type\", \"message\": \"$error_message\"}]"
}

#######################################
# Calculate days until expiration
# Arguments:
#   $1 - expiration date (format: MMM DD HH:MM:SS YYYY GMT)
# Returns:
#   Number of days (can be negative if expired)
#######################################
calculate_days_remaining() {
    local expiry_date="$1"

    # Convert to epoch seconds
    local expiry_epoch
    expiry_epoch=$(date -j -f "%b %d %T %Y %Z" "$expiry_date" +%s 2>/dev/null || echo "0")

    if [[ "$expiry_epoch" == "0" ]]; then
        # Try alternate date parsing (Linux)
        expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
    fi

    local now_epoch
    now_epoch=$(date +%s)

    # Calculate days remaining
    local seconds_remaining=$((expiry_epoch - now_epoch))
    local days_remaining=$((seconds_remaining / 86400))

    echo "$days_remaining"
}

#######################################
# Validate certificate from file
# Arguments:
#   $1 - path to certificate file
# Outputs:
#   JSON certificate information
# Returns:
#   0 on success, 1 on failure
#######################################
validate_cert_file() {
    local cert_file="$1"

    # Check if openssl is available
    if ! command -v openssl &> /dev/null; then
        output_error "DependencyError" "openssl is not installed"
        return 1
    fi

    # Extract certificate information
    local subject
    local issuer
    local not_before
    local not_after
    local serial

    # Parse certificate with openssl
    if ! subject=$(openssl x509 -in "$cert_file" -noout -subject 2>&1); then
        output_error "RuntimeError" "Failed to read certificate: $subject"
        return 1
    fi

    issuer=$(openssl x509 -in "$cert_file" -noout -issuer 2>/dev/null || echo "Unknown")
    not_before=$(openssl x509 -in "$cert_file" -noout -startdate 2>/dev/null | cut -d= -f2)
    not_after=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
    serial=$(openssl x509 -in "$cert_file" -noout -serial 2>/dev/null | cut -d= -f2)

    # Calculate days remaining
    local days_remaining
    days_remaining=$(calculate_days_remaining "$not_after")

    # Determine if expired
    local is_expired="false"
    local status="valid"

    if [[ $days_remaining -lt 0 ]]; then
        is_expired="true"
        status="expired"
    elif [[ $days_remaining -lt 30 ]]; then
        status="expiring_soon"
    fi

    # Clean up subject and issuer (remove prefix)
    subject="${subject#subject=}"
    issuer="${issuer#issuer=}"

    # Escape quotes in strings
    subject="${subject//\"/\\\"}"
    issuer="${issuer//\"/\\\"}"

    # Create data object
    local data
    data=$(cat <<EOF_DATA
{
  "source": "file",
  "file": "$cert_file",
  "subject": "$subject",
  "issuer": "$issuer",
  "serial": "$serial",
  "valid_from": "$not_before",
  "valid_until": "$not_after",
  "days_remaining": $days_remaining,
  "is_expired": $is_expired,
  "status": "$status"
}
EOF_DATA
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Validate certificate from URL
# Arguments:
#   $1 - URL (host:port)
# Outputs:
#   JSON certificate information
# Returns:
#   0 on success, 1 on failure
#######################################
validate_cert_url() {
    local url="$1"

    # Check if openssl is available
    if ! command -v openssl &> /dev/null; then
        output_error "DependencyError" "openssl is not installed"
        return 1
    fi

    # Parse host and port
    local host
    local port

    # Remove https:// prefix if present
    url="${url#https://}"
    url="${url#http://}"

    if [[ "$url" =~ ^([^:]+):([0-9]+)$ ]]; then
        host="${BASH_REMATCH[1]}"
        port="${BASH_REMATCH[2]}"
    else
        output_error "ValidationError" "Invalid URL format. Expected: host:port or https://host:port"
        return 1
    fi

    # Get certificate from remote host
    local cert_info
    if ! cert_info=$(echo | openssl s_client -servername "$host" -connect "$host:$port" 2>/dev/null); then
        output_error "RuntimeError" "Failed to connect to $host:$port"
        return 1
    fi

    # Extract certificate dates and info
    local subject
    local issuer
    local not_before
    local not_after
    local serial

    subject=$(echo "$cert_info" | openssl x509 -noout -subject 2>/dev/null | cut -d= -f2-)
    issuer=$(echo "$cert_info" | openssl x509 -noout -issuer 2>/dev/null | cut -d= -f2-)
    not_before=$(echo "$cert_info" | openssl x509 -noout -startdate 2>/dev/null | cut -d= -f2)
    not_after=$(echo "$cert_info" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    serial=$(echo "$cert_info" | openssl x509 -noout -serial 2>/dev/null | cut -d= -f2)

    # Calculate days remaining
    local days_remaining
    days_remaining=$(calculate_days_remaining "$not_after")

    # Determine if expired
    local is_expired="false"
    local status="valid"

    if [[ $days_remaining -lt 0 ]]; then
        is_expired="true"
        status="expired"
    elif [[ $days_remaining -lt 30 ]]; then
        status="expiring_soon"
    fi

    # Escape quotes in strings
    subject="${subject//\"/\\\"}"
    issuer="${issuer//\"/\\\"}"

    # Create data object
    local data
    data=$(cat <<EOF_DATA
{
  "source": "url",
  "host": "$host",
  "port": $port,
  "subject": "$subject",
  "issuer": "$issuer",
  "serial": "$serial",
  "valid_from": "$not_before",
  "valid_until": "$not_after",
  "days_remaining": $days_remaining,
  "is_expired": $is_expired,
  "status": "$status"
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
    local target="$1"

    # Determine if target is a file or URL
    if [[ -f "$target" ]]; then
        # Validate certificate file
        if validate_cert_file "$target"; then
            exit 0
        else
            exit 1
        fi
    elif validate_url "$target"; then
        # Validate certificate from URL
        if validate_cert_url "$target"; then
            exit 0
        else
            exit 1
        fi
    else
        output_error "ValidationError" "Invalid target. Must be a certificate file or URL (host:port)"
        exit 1
    fi
}

# Execute main function
main "$@"
