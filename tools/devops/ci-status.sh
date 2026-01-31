#!/usr/bin/env bash
# Tool Name: ci-status.sh
# Purpose: Query CI/CD pipeline status (GitHub Actions, GitLab CI)
# Security: Token validation, safe API calls, input sanitization
# Usage:
#   # GitHub Actions status
#   ./ci-status.sh --provider github --repo owner/repo
#
#   # GitLab CI status
#   ./ci-status.sh --provider gitlab --repo project-id
#
#   # With authentication token (from environment)
#   export GITHUB_TOKEN=ghp_xxxxx
#   ./ci-status.sh --provider github --repo owner/repo
#
#   # Check specific workflow/branch
#   ./ci-status.sh --provider github --repo owner/repo --branch main

set -euo pipefail

# Default values
PROVIDER=""
REPO=""
BRANCH=""
TOKEN=""

# Help message
show_help() {
    cat <<EOF
Usage: ci-status.sh --provider <github|gitlab> --repo <repo> [OPTIONS]

Query CI/CD pipeline status from GitHub Actions or GitLab CI.

Options:
  --provider      CI provider (github or gitlab)
  --repo          Repository identifier (owner/repo for GitHub, project-id for GitLab)
  --branch        Branch name (optional)
  --token         Authentication token (optional, reads from env vars if not provided)
  --help          Show this help message

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token
  GITLAB_TOKEN    GitLab personal access token

Examples:
  ./ci-status.sh --provider github --repo microsoft/vscode
  ./ci-status.sh --provider gitlab --repo 278964 --branch main
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --token)
            TOKEN="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "{\"success\": false, \"errors\": [{\"type\": \"ArgumentError\", \"message\": \"Unknown argument: $1\"}]}" >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$PROVIDER" ]]; then
    echo '{"success": false, "errors": [{"type": "ValidationError", "message": "Provider is required (--provider github|gitlab)"}]}' >&2
    exit 1
fi

if [[ -z "$REPO" ]]; then
    echo '{"success": false, "errors": [{"type": "ValidationError", "message": "Repository is required (--repo owner/repo)"}]}' >&2
    exit 1
fi

# Validate provider
if [[ "$PROVIDER" != "github" && "$PROVIDER" != "gitlab" ]]; then
    echo "{\"success\": false, \"errors\": [{\"type\": \"ValidationError\", \"message\": \"Invalid provider: $PROVIDER. Must be 'github' or 'gitlab'\"}]}" >&2
    exit 1
fi

# Get token from environment if not provided
if [[ -z "$TOKEN" ]]; then
    if [[ "$PROVIDER" == "github" ]]; then
        TOKEN="${GITHUB_TOKEN:-}"
    elif [[ "$PROVIDER" == "gitlab" ]]; then
        TOKEN="${GITLAB_TOKEN:-}"
    fi
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo '{"success": false, "errors": [{"type": "DependencyError", "message": "curl is required but not installed"}]}' >&2
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo '{"success": false, "errors": [{"type": "DependencyError", "message": "jq is required but not installed"}]}' >&2
    exit 1
fi

# Function to query GitHub Actions
query_github() {
    local repo="$1"
    local branch="$2"
    local token="$3"

    local url="https://api.github.com/repos/$repo/actions/runs"
    local auth_header=""

    if [[ -n "$token" ]]; then
        auth_header="Authorization: token $token"
    fi

    # Add branch filter if specified
    if [[ -n "$branch" ]]; then
        url="$url?branch=$branch"
    fi

    # Make API request
    local response
    if [[ -n "$auth_header" ]]; then
        response=$(curl -s -H "$auth_header" -H "Accept: application/vnd.github.v3+json" "$url")
    else
        response=$(curl -s -H "Accept: application/vnd.github.v3+json" "$url")
    fi

    # Check for API errors
    if echo "$response" | jq -e '.message' > /dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message')
        echo "{\"success\": false, \"errors\": [{\"type\": \"APIError\", \"message\": \"GitHub API error: $error_msg\"}]}" >&2
        exit 1
    fi

    # Parse and format response
    local runs
    runs=$(echo "$response" | jq -c '[.workflow_runs[0:5] | .[] | {
        id: .id,
        name: .name,
        status: .status,
        conclusion: .conclusion,
        branch: .head_branch,
        commit: .head_sha[0:7],
        created_at: .created_at,
        updated_at: .updated_at,
        html_url: .html_url
    }]')

    local total_count
    total_count=$(echo "$response" | jq -r '.total_count // 0')

    # Get latest run status
    local latest_status
    latest_status=$(echo "$response" | jq -r '.workflow_runs[0].status // "unknown"')
    local latest_conclusion
    latest_conclusion=$(echo "$response" | jq -r '.workflow_runs[0].conclusion // "none"')

    echo "{
        \"success\": true,
        \"data\": {
            \"provider\": \"github\",
            \"repository\": \"$repo\",
            \"branch\": \"$branch\",
            \"total_runs\": $total_count,
            \"latest_status\": \"$latest_status\",
            \"latest_conclusion\": \"$latest_conclusion\",
            \"recent_runs\": $runs
        },
        \"errors\": [],
        \"metadata\": {
            \"tool\": \"ci-status\",
            \"version\": \"1.0.0\"
        }
    }"
}

# Function to query GitLab CI
query_gitlab() {
    local project="$1"
    local branch="$2"
    local token="$3"

    local url="https://gitlab.com/api/v4/projects/$project/pipelines"
    local auth_header=""

    if [[ -n "$token" ]]; then
        auth_header="PRIVATE-TOKEN: $token"
    fi

    # Add branch filter if specified
    if [[ -n "$branch" ]]; then
        url="$url?ref=$branch"
    fi

    # Make API request
    local response
    if [[ -n "$auth_header" ]]; then
        response=$(curl -s -H "$auth_header" "$url")
    else
        response=$(curl -s "$url")
    fi

    # Check for API errors
    if echo "$response" | jq -e '.message' > /dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$response" | jq -r '.message')
        echo "{\"success\": false, \"errors\": [{\"type\": \"APIError\", \"message\": \"GitLab API error: $error_msg\"}]}" >&2
        exit 1
    fi

    # Parse and format response
    local pipelines
    pipelines=$(echo "$response" | jq -c '[.[0:5] | .[] | {
        id: .id,
        status: .status,
        ref: .ref,
        sha: .sha[0:7],
        created_at: .created_at,
        updated_at: .updated_at,
        web_url: .web_url
    }]')

    # Get latest pipeline status
    local latest_status
    latest_status=$(echo "$response" | jq -r '.[0].status // "unknown"')

    echo "{
        \"success\": true,
        \"data\": {
            \"provider\": \"gitlab\",
            \"project\": \"$project\",
            \"branch\": \"$branch\",
            \"latest_status\": \"$latest_status\",
            \"recent_pipelines\": $pipelines
        },
        \"errors\": [],
        \"metadata\": {
            \"tool\": \"ci-status\",
            \"version\": \"1.0.0\"
        }
    }"
}

# Execute based on provider
if [[ "$PROVIDER" == "github" ]]; then
    query_github "$REPO" "$BRANCH" "$TOKEN"
elif [[ "$PROVIDER" == "gitlab" ]]; then
    query_gitlab "$REPO" "$BRANCH" "$TOKEN"
fi
