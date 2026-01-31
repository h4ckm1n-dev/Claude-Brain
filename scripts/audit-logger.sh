#!/usr/bin/env bash
# Audit logging for agent actions
# Usage: source this file, then call: log_action "agent-name" "action" "files"
#
# Example:
#   source ~/.claude/scripts/audit-logger.sh
#   log_action "backend-architect" "create" "src/api.py"
#   log_action "test-engineer" "modify" "tests/test_api.py"

AUDIT_LOG="${HOME}/.claude/audit.log"

# Ensure audit log exists with restricted permissions
if [ ! -f "$AUDIT_LOG" ]; then
  touch "$AUDIT_LOG"
  chmod 600 "$AUDIT_LOG"
fi

# Verify permissions on existing log
if [ -f "$AUDIT_LOG" ]; then
  # Check permissions (should be 600)
  current_perms=$(stat -f "%OLp" "$AUDIT_LOG" 2>/dev/null || stat -c "%a" "$AUDIT_LOG" 2>/dev/null || echo "unknown")
  if [ "$current_perms" != "600" ] && [ "$current_perms" != "unknown" ]; then
    echo "⚠️  Warning: audit.log has incorrect permissions ($current_perms), fixing to 600" >&2
    chmod 600 "$AUDIT_LOG"
  fi
fi

# Log an agent action
# Args: agent_name, action, files
log_action() {
  local agent="${1:-unknown}"
  local action="${2:-unknown}"
  local files="${3:-none}"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Sanitize inputs (prevent log injection)
  agent=$(echo "$agent" | tr -d '\n\r|')
  action=$(echo "$action" | tr -d '\n\r|')
  files=$(echo "$files" | tr -d '\n\r|')

  echo "${timestamp} | ${agent} | ${action} | ${files}" >> "$AUDIT_LOG"
}

# Rotate log if > 10MB
rotate_audit_log() {
  local max_size=$((10 * 1024 * 1024))  # 10MB in bytes

  if [ -f "$AUDIT_LOG" ]; then
    size=$(wc -c < "$AUDIT_LOG")
    if [ "$size" -gt "$max_size" ]; then
      echo "📦 Rotating audit log (size: $size bytes > $max_size max)" >&2
      mv "$AUDIT_LOG" "${AUDIT_LOG}.$(date +%Y%m%d_%H%M%S)"
      touch "$AUDIT_LOG"
      chmod 600 "$AUDIT_LOG"
      echo "✅ Audit log rotated successfully" >&2
    fi
  fi
}

# Auto-rotate on sourcing if needed
rotate_audit_log
