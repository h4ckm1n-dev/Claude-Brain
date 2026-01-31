#!/usr/bin/env bash
# Real-time agent usage dashboard
# Usage: ./agent-usage-dashboard.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS_SCRIPT="${SCRIPT_DIR}/agent-analytics-enhanced.sh"

# Check if analytics script exists
if [ ! -f "$ANALYTICS_SCRIPT" ]; then
  echo "❌ Error: agent-analytics-enhanced.sh not found at: $ANALYTICS_SCRIPT"
  exit 1
fi

echo "🚀 Starting Agent Usage Dashboard..."
echo "   Press Ctrl+C to exit"
sleep 2

# Main loop
while true; do
  # Clear screen
  clear

  # Header
  echo "╔════════════════════════════════════════════════════════════════════╗"
  echo "║              Agent Usage Dashboard (Live)                          ║"
  echo "║                Updated: $(date +"%Y-%m-%d %H:%M:%S")                          ║"
  echo "╚════════════════════════════════════════════════════════════════════╝"
  echo ""

  # Call analytics
  "$ANALYTICS_SCRIPT"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Refreshing in 10 seconds... (Ctrl+C to exit)"

  # Sleep 10 seconds
  sleep 10
done
