#!/usr/bin/env bash
# tool-stats.sh - Analyze tool usage statistics from .tool-usage.log
#
# PURPOSE: Show which custom tools are most frequently used
# PRIVACY: Only tracks tool name and timestamp (no user data or file paths)
#
# USAGE:
#   tool-stats.sh [--days=N] [--help]
#
# OPTIONS:
#   --days=N    Show stats for last N days (default: 7)
#   --help      Show this help message
#
# OUTPUT FORMAT:
#   Tool Usage Statistics
#
#   Most Used (last 7 days):
#     1. secret-scanner.py     (15 times)
#     2. service-health.sh     (12 times)
#
#   By Category:
#     Security: 25 uses
#     DevOps:   18 uses

set -euo pipefail

# Configuration
LOG_FILE="${HOME}/.claude/.tool-usage.log"
DAYS=7

# Usage function
usage() {
  cat <<EOF
Tool Usage Statistics

Analyzes custom tool usage from ~/.claude/.tool-usage.log

USAGE:
  tool-stats.sh [OPTIONS]

OPTIONS:
  --days=N    Show stats for last N days (default: 7)
  --help      Show this help message

EXAMPLES:
  tool-stats.sh              # Last 7 days
  tool-stats.sh --days=30    # Last 30 days
  tool-stats.sh --days=0     # All time

LOG FORMAT:
  timestamp,tool-name,exit-code
  2025-11-06T12:00:00,secret-scanner,0
EOF
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      ;;
    --days=*)
      DAYS="${1#*=}"
      if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
        echo "Error: --days must be a number" >&2
        exit 1
      fi
      shift
      ;;
    *)
      echo "Error: Unknown option '$1'" >&2
      echo "Use --help for usage information" >&2
      exit 1
      ;;
  esac
done

# Check if log file exists
if [[ ! -f "$LOG_FILE" ]]; then
  echo "Tool Usage Statistics"
  echo ""
  echo "No data available (log file does not exist)"
  echo ""
  echo "Tools will start logging usage to: $LOG_FILE"
  exit 0
fi

# Check if log file is empty
if [[ ! -s "$LOG_FILE" ]]; then
  echo "Tool Usage Statistics"
  echo ""
  echo "No data available (log file is empty)"
  echo ""
  echo "Run some custom tools to see usage statistics here."
  exit 0
fi

# Calculate cutoff date if filtering by days
if [[ "$DAYS" -gt 0 ]]; then
  # Use GNU date or BSD date depending on platform
  if date --version >/dev/null 2>&1; then
    # GNU date
    CUTOFF_DATE=$(date -u -d "$DAYS days ago" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "")
  else
    # BSD date (macOS)
    CUTOFF_DATE=$(date -u -v-"${DAYS}"d +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "")
  fi
fi

# Create temporary files for processing
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

FILTERED_LOG="$TEMP_DIR/filtered.log"
TOOL_COUNTS="$TEMP_DIR/tool_counts.txt"
CATEGORY_COUNTS="$TEMP_DIR/category_counts.txt"

# Filter log by date if needed
if [[ "$DAYS" -gt 0 && -n "$CUTOFF_DATE" ]]; then
  awk -F',' -v cutoff="$CUTOFF_DATE" '$1 >= cutoff' "$LOG_FILE" > "$FILTERED_LOG" 2>/dev/null || cp "$LOG_FILE" "$FILTERED_LOG"
else
  cp "$LOG_FILE" "$FILTERED_LOG"
fi

# Check if we have any data after filtering
if [[ ! -s "$FILTERED_LOG" ]]; then
  echo "Tool Usage Statistics"
  echo ""
  if [[ "$DAYS" -gt 0 ]]; then
    echo "No data available (last $DAYS days)"
  else
    echo "No data available (all time)"
  fi
  exit 0
fi

# Count total entries
TOTAL_COUNT=$(wc -l < "$FILTERED_LOG" | tr -d ' ')

# Extract tool names and count usage
# Format: timestamp,tool-name,exit-code
# Extract just the filename without path and extension for display
cut -d',' -f2 "$FILTERED_LOG" | while IFS= read -r tool_path; do
  # Remove path prefix (e.g., security/secret-scanner.py -> secret-scanner.py)
  basename "$tool_path"
done | sort | uniq -c | sort -rn > "$TOOL_COUNTS"

# Extract categories and count usage
# Category is the directory name before the tool (e.g., security/tool.py -> security)
cut -d',' -f2 "$FILTERED_LOG" | while IFS= read -r tool_path; do
  if [[ "$tool_path" == *"/"* ]]; then
    # Extract directory name as category
    dirname "$tool_path" | sed 's|^.*/||'
  else
    # No category, use "uncategorized"
    echo "uncategorized"
  fi
done | sort | uniq -c | sort -rn > "$CATEGORY_COUNTS"

# Display results
echo "Tool Usage Statistics"
echo ""

if [[ "$DAYS" -gt 0 ]]; then
  echo "Most Used (last $DAYS days):"
else
  echo "Most Used (all time):"
fi

# Show top 10 tools
HEAD_COUNT=1
while IFS= read -r line && [[ $HEAD_COUNT -le 10 ]]; do
  # Parse count and tool name
  COUNT=$(echo "$line" | awk '{print $1}')
  TOOL=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')

  # Format output with padding
  printf "  %2d. %-30s (%d times)\n" "$HEAD_COUNT" "$TOOL" "$COUNT"

  HEAD_COUNT=$((HEAD_COUNT + 1))
done < "$TOOL_COUNTS"

# Check if we displayed any tools
if [[ $HEAD_COUNT -eq 1 ]]; then
  echo "  (no tools recorded)"
fi

echo ""
echo "By Category:"

# Show category breakdown
CATEGORY_FOUND=0
while IFS= read -r line; do
  # Parse count and category
  COUNT=$(echo "$line" | awk '{print $1}')
  CATEGORY=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')

  # Capitalize first letter
  CATEGORY_DISPLAY=$(echo "$CATEGORY" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')

  printf "  %-15s %d uses\n" "$CATEGORY_DISPLAY:" "$COUNT"
  CATEGORY_FOUND=1
done < "$CATEGORY_COUNTS"

if [[ $CATEGORY_FOUND -eq 0 ]]; then
  echo "  (no categories recorded)"
fi

echo ""
echo "Total tool invocations: $TOTAL_COUNT"

exit 0
