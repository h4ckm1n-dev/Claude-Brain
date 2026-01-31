#!/usr/bin/env bash
# Enhanced agent usage analytics across all projects
# Usage: ./agent-analytics-enhanced.sh [--json]

set -euo pipefail

CLAUDE_HOME="${HOME}/.claude"
PROJECTS_DIR="${CLAUDE_HOME}/projects"
MAIN_CONTEXT="${CLAUDE_HOME}/PROJECT_CONTEXT.md"
JSON_OUTPUT=false

# Parse args
if [[ "${1:-}" == "--json" ]]; then
  JSON_OUTPUT=true
fi

# Create temp directory for data processing
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

AGENT_DATA="${TEMP_DIR}/agent_data.txt"
CHAIN_DATA="${TEMP_DIR}/chain_data.txt"
ALL_AGENTS="${TEMP_DIR}/all_agents.txt"
USED_AGENTS="${TEMP_DIR}/used_agents.txt"

# Extract all agent names from CLAUDE.md
if [ -f "${CLAUDE_HOME}/CLAUDE.md" ]; then
  grep -E "^\| \*\*[a-z-]+\*\*" "${CLAUDE_HOME}/CLAUDE.md" | \
    sed -E 's/^\| \*\*([a-z-]+)\*\*.*/\1/' | sort > "$ALL_AGENTS" || true
fi

# Function to parse a PROJECT_CONTEXT.md file
parse_context_file() {
  local context_file="$1"

  # Extract agent entries: **YYYY-MM-DD HH:MM** - `agent-name`
  grep -E "^\*\*[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}\*\* - \`[a-z-]+\`" "$context_file" 2>/dev/null | while IFS= read -r line; do
    # Extract timestamp and agent name
    timestamp=$(echo "$line" | sed -E 's/^\*\*([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})\*\*.*/\1/')
    agent=$(echo "$line" | sed -E 's/.*\`([a-z-]+)\`.*/\1/')

    # Store in format: agent|timestamp
    echo "${agent}|${timestamp}" >> "$AGENT_DATA"
  done
}

# Parse main PROJECT_CONTEXT.md
if [ -f "$MAIN_CONTEXT" ]; then
  parse_context_file "$MAIN_CONTEXT"
fi

# Parse all PROJECT_CONTEXT.md files in projects/ directory
if [ -d "$PROJECTS_DIR" ]; then
  find "$PROJECTS_DIR" -name "PROJECT_CONTEXT.md" -type f 2>/dev/null | while read -r context_file; do
    parse_context_file "$context_file"
  done
fi

# Count total invocations
agents_total=$(wc -l < "$AGENT_DATA" 2>/dev/null | tr -d ' ' || echo "0")

# Extract and sort used agents
if [ -s "$AGENT_DATA" ]; then
  cut -d'|' -f1 "$AGENT_DATA" | sort -u > "$USED_AGENTS"
  unique_agents_used=$(wc -l < "$USED_AGENTS" | tr -d ' ')
else
  touch "$USED_AGENTS"
  unique_agents_used=0
fi

# Total agents available
total_agents_available=$(wc -l < "$ALL_AGENTS" 2>/dev/null | tr -d ' ' || echo "0")

# Detect common agent chains
if [ -f "$MAIN_CONTEXT" ]; then
  prev_agent=""
  grep -E "^\*\*[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}\*\* - \`[a-z-]+\`" "$MAIN_CONTEXT" 2>/dev/null | while IFS= read -r line; do
    current_agent=$(echo "$line" | sed -E 's/.*\`([a-z-]+)\`.*/\1/')
    if [ -n "$prev_agent" ] && [ -f "${TEMP_DIR}/prev_agent" ]; then
      prev=$(cat "${TEMP_DIR}/prev_agent")
      echo "${prev} → ${current_agent}" >> "$CHAIN_DATA"
    fi
    echo "$current_agent" > "${TEMP_DIR}/prev_agent"
  done
fi

# JSON output
if [ "$JSON_OUTPUT" = true ]; then
  echo "{"
  echo "  \"total_invocations\": $agents_total,"
  echo "  \"unique_agents_used\": $unique_agents_used,"
  echo "  \"total_agents_available\": $total_agents_available,"
  echo "  \"top_agents\": ["

  # Top 10 agents
  if [ -s "$AGENT_DATA" ]; then
    cut -d'|' -f1 "$AGENT_DATA" | sort | uniq -c | sort -rn | head -10 | while read -r count agent; do
      # Get last seen timestamp for this agent
      last_seen=$(grep "^${agent}|" "$AGENT_DATA" | tail -1 | cut -d'|' -f2)
      # Print JSON (handle trailing comma later)
      printf "    {\"name\": \"%s\", \"uses\": %d, \"last_seen\": \"%s\"},\n" "$agent" "$count" "$last_seen"
    done | sed '$ s/,$//'  # Remove trailing comma from last line
  fi

  echo "  ],"
  echo "  \"unused_agents\": ["

  # Identify unused agents - comm requires sorted input
  if [ -s "$ALL_AGENTS" ] && [ -s "$USED_AGENTS" ]; then
    comm -23 "$ALL_AGENTS" "$USED_AGENTS" | while read -r agent; do
      printf "    \"%s\",\n" "$agent"
    done | sed '$ s/,$//'  # Remove trailing comma from last line
  elif [ -s "$ALL_AGENTS" ]; then
    # All agents are unused
    cat "$ALL_AGENTS" | while read -r agent; do
      printf "    \"%s\",\n" "$agent"
    done | sed '$ s/,$//'
  fi

  echo "  ],"
  echo "  \"common_chains\": ["

  # Common chains (3+ occurrences)
  if [ -s "$CHAIN_DATA" ]; then
    sort "$CHAIN_DATA" | uniq -c | sort -rn | while read -r count chain; do
      if [ "$count" -ge 3 ]; then
        printf "    {\"pattern\": \"%s\", \"occurrences\": %d},\n" "$chain" "$count"
      fi
    done | sed '$ s/,$//'  # Remove trailing comma from last line
  fi

  echo "  ]"
  echo "}"
else
  # Human-readable output
  echo "📊 Agent Usage Report"
  echo "====================================="
  echo ""
  echo "Total Agent Invocations: $agents_total"
  echo "Unique Agents Used: ${unique_agents_used}/${total_agents_available}"
  echo ""

  if [ -s "$AGENT_DATA" ]; then
    echo "Top 10 Most Used Agents:"
    echo ""

    # Top 10 with formatting
    cut -d'|' -f1 "$AGENT_DATA" | sort | uniq -c | sort -rn | head -10 | nl | while read -r rank count agent; do
      # Get last seen timestamp
      last_seen=$(grep "^${agent}|" "$AGENT_DATA" | tail -1 | cut -d'|' -f2)
      printf "%2d. %-30s %3d uses (last: %s)\n" "$rank" "$agent" "$count" "$last_seen"
    done
  else
    echo "No agent activity found yet."
  fi

  echo ""

  # Unused agents
  if [ -s "$ALL_AGENTS" ]; then
    if [ -s "$USED_AGENTS" ]; then
      unused_count=$(comm -23 "$ALL_AGENTS" "$USED_AGENTS" | wc -l | tr -d ' ')
    else
      unused_count=$total_agents_available
    fi

    if [ "$unused_count" -gt 0 ]; then
      echo "Unused Agents (${unused_count}):"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "(Candidates for archiving or documentation improvement)"
      echo ""

      comm -23 "$ALL_AGENTS" "$USED_AGENTS" | head -20 | while read -r agent; do
        echo "  • $agent"
      done

      if [ "$unused_count" -gt 20 ]; then
        echo "  ... and $((unused_count - 20)) more"
      fi
    else
      echo "All agents have been used! 🎉"
    fi
  fi

  echo ""

  # Common chains
  if [ -s "$CHAIN_DATA" ]; then
    echo "Common Agent Chains (3+ occurrences):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    chain_found=false
    sort "$CHAIN_DATA" | uniq -c | sort -rn | while read -r count chain; do
      if [ "$count" -ge 3 ]; then
        printf "  %2d× %s\n" "$count" "$chain"
        chain_found=true
      fi
    done

    if [ "$chain_found" = false ]; then
      echo "  (No patterns with 3+ occurrences yet)"
    fi
  fi

  echo ""
  echo "✅ Analytics complete"
fi

exit 0
