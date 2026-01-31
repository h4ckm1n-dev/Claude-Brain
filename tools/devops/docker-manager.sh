#!/usr/bin/env bash
# Tool Name: docker-manager.sh
# Purpose: Safe Docker operations (list, inspect, prune with confirmation)
# Security: Input validation, safe command execution, proper quoting
#
# Usage:
#   ./docker-manager.sh <command> [args]
#
# Commands:
#   list-containers     List all containers with details
#   list-images         List all images with details
#   inspect <id>        Inspect container or image
#   prune-images        Remove unused images (requires --confirm)
#   prune-containers    Remove stopped containers (requires --confirm)
#
# Example:
#   ./docker-manager.sh list-containers
#   ./docker-manager.sh inspect my-container
#   ./docker-manager.sh prune-images --confirm
#
# Output:
#   JSON with structure: {"success": true/false, "data": {}, "errors": [], "metadata": {}}

# Strict mode - exit on error, undefined variables, pipe failures
set -euo pipefail

# Tool metadata
TOOL_NAME="docker-manager"
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
Usage: $(basename "$0") <command> [args]

Description:
    Safe Docker operations for container and image management.
    Destructive operations require --confirm flag.

Commands:
    list-containers     List all containers (running and stopped)
    list-images         List all images with sizes
    inspect <id>        Inspect container or image by ID/name
    prune-images        Remove unused images (requires --confirm)
    prune-containers    Remove stopped containers (requires --confirm)

Examples:
    $(basename "$0") list-containers
    $(basename "$0") list-images
    $(basename "$0") inspect my-container
    $(basename "$0") prune-images --confirm
    $(basename "$0") prune-containers --confirm

Output:
    JSON format: {"success": bool, "data": {}, "errors": [], "metadata": {}}

Requirements:
    - Docker daemon running
    - docker CLI installed
    - jq (for JSON formatting)
EOF
}

#######################################
# Check if Docker is available
# Returns:
#   0 if Docker available, 1 otherwise
#######################################
check_docker() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        return 1
    fi

    return 0
}

#######################################
# Validate container/image ID or name
# Arguments:
#   $1 - ID or name to validate
# Returns:
#   0 if valid, 1 if invalid
#######################################
validate_identifier() {
    local identifier="$1"

    # Allow alphanumeric, hyphens, underscores, dots
    if [[ "$identifier" =~ ^[a-zA-Z0-9._-]+$ ]]; then
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
# List all containers
# Outputs:
#   JSON array of containers
#######################################
list_containers() {
    local containers
    local container_count

    # Get containers in JSON format
    if ! containers=$(docker ps -a --format '{{json .}}' 2>&1); then
        output_error "DockerError" "Failed to list containers: $containers"
        return 1
    fi

    # Convert to JSON array
    if [[ -z "$containers" ]]; then
        containers="[]"
        container_count=0
    else
        # Use jq to create proper JSON array
        if command -v jq &> /dev/null; then
            containers=$(echo "$containers" | jq -s '.')
            container_count=$(echo "$containers" | jq 'length')
        else
            # Fallback without jq
            containers="[$containers]"
            container_count=$(echo "$containers" | grep -c "ID" || echo "0")
        fi
    fi

    local data
    data=$(cat <<EOF
{
  "containers": $containers,
  "count": $container_count
}
EOF
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# List all images
# Outputs:
#   JSON array of images
#######################################
list_images() {
    local images
    local image_count

    # Get images in JSON format
    if ! images=$(docker images --format '{{json .}}' 2>&1); then
        output_error "DockerError" "Failed to list images: $images"
        return 1
    fi

    # Convert to JSON array
    if [[ -z "$images" ]]; then
        images="[]"
        image_count=0
    else
        # Use jq to create proper JSON array
        if command -v jq &> /dev/null; then
            images=$(echo "$images" | jq -s '.')
            image_count=$(echo "$images" | jq 'length')
        else
            # Fallback without jq
            images="[$images]"
            image_count=$(echo "$images" | grep -c "Repository" || echo "0")
        fi
    fi

    local data
    data=$(cat <<EOF
{
  "images": $images,
  "count": $image_count
}
EOF
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Inspect container or image
# Arguments:
#   $1 - Container/image ID or name
# Outputs:
#   JSON inspection data
#######################################
inspect_resource() {
    local identifier="$1"

    # Validate identifier
    if ! validate_identifier "$identifier"; then
        output_error "ValidationError" "Invalid container/image identifier: $identifier"
        return 1
    fi

    local inspect_data
    if ! inspect_data=$(docker inspect "$identifier" 2>&1); then
        output_error "DockerError" "Failed to inspect $identifier: $inspect_data"
        return 1
    fi

    create_json_output "true" "$inspect_data" "[]"
    return 0
}

#######################################
# Prune unused images
# Arguments:
#   $1 - confirmation flag (--confirm)
# Outputs:
#   JSON with prune results
#######################################
prune_images() {
    local confirm="${1:-}"

    if [[ "$confirm" != "--confirm" ]]; then
        output_error "ValidationError" "Destructive operation requires --confirm flag"
        return 1
    fi

    local prune_output
    if ! prune_output=$(docker image prune -f 2>&1); then
        output_error "DockerError" "Failed to prune images: $prune_output"
        return 1
    fi

    # Extract space reclaimed
    local space_reclaimed
    space_reclaimed=$(echo "$prune_output" | grep -oE "[0-9]+(\.[0-9]+)?[KMGT]?B" || echo "0B")

    local data
    data=$(cat <<EOF
{
  "operation": "prune-images",
  "space_reclaimed": "$space_reclaimed",
  "output": $(echo "$prune_output" | jq -Rs '.')
}
EOF
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Prune stopped containers
# Arguments:
#   $1 - confirmation flag (--confirm)
# Outputs:
#   JSON with prune results
#######################################
prune_containers() {
    local confirm="${1:-}"

    if [[ "$confirm" != "--confirm" ]]; then
        output_error "ValidationError" "Destructive operation requires --confirm flag"
        return 1
    fi

    local prune_output
    if ! prune_output=$(docker container prune -f 2>&1); then
        output_error "DockerError" "Failed to prune containers: $prune_output"
        return 1
    fi

    # Extract space reclaimed
    local space_reclaimed
    space_reclaimed=$(echo "$prune_output" | grep -oE "[0-9]+(\.[0-9]+)?[KMGT]?B" || echo "0B")

    local data
    data=$(cat <<EOF
{
  "operation": "prune-containers",
  "space_reclaimed": "$space_reclaimed",
  "output": $(echo "$prune_output" | jq -Rs '.')
}
EOF
)

    create_json_output "true" "$data" "[]"
    return 0
}

#######################################
# Main function
# Arguments:
#   $@ - Command and arguments
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

    # Check Docker availability
    if ! check_docker; then
        output_error "DependencyError" "Docker is not available or daemon is not running"
        exit 1
    fi

    local command="${1:-}"
    shift || true

    case "$command" in
        list-containers)
            list_containers
            exit $?
            ;;
        list-images)
            list_images
            exit $?
            ;;
        inspect)
            if [[ $# -lt 1 ]]; then
                output_error "ValidationError" "inspect command requires container/image ID"
                exit 1
            fi
            inspect_resource "$1"
            exit $?
            ;;
        prune-images)
            prune_images "${1:-}"
            exit $?
            ;;
        prune-containers)
            prune_containers "${1:-}"
            exit $?
            ;;
        *)
            output_error "ValidationError" "Unknown command: $command (use list-containers, list-images, inspect, prune-images, prune-containers)"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"
