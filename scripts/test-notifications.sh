#!/bin/bash
# Test Claude Code Fancy Notifications
# Run this script to preview all notification styles

set -euo pipefail

NOTIFY="${HOME}/.claude/hooks/notify.sh"

echo "🔔 Testing Claude Code Fancy Notifications..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if terminal-notifier is available
if command -v terminal-notifier &> /dev/null; then
    echo "✅ terminal-notifier is installed (enhanced features enabled)"
else
    echo "⚠️  terminal-notifier not installed (using basic AppleScript)"
    echo "   Install for enhanced features: brew install terminal-notifier"
fi
echo ""

# Function to show notification with delay
show_notification() {
    local type="$1"
    local title="$2"
    local message="$3"

    echo "📤 Sending: $type notification..."
    "$NOTIFY" "$type" "$title" "$message"
    sleep 2
}

echo "Sending test notifications (2 second intervals)..."
echo ""

# Test all notification types
show_notification "success" "Build Complete" "Your project built successfully in 4.2s"
show_notification "error" "Test Failed" "3 tests failed in src/utils.test.ts"
show_notification "warning" "Deprecation Notice" "React.render() is deprecated"
show_notification "info" "Information" "Claude Code is ready to help"
show_notification "task" "Agent Working" "backend-architect is implementing your feature"
show_notification "agent" "Agent Complete" "test-engineer finished running tests"
show_notification "build" "Building" "Compiling TypeScript with esbuild..."
show_notification "test" "Tests Running" "Running 47 tests with vitest"
show_notification "deploy" "Deployment" "Successfully deployed to production"
show_notification "celebrate" "All Done!" "Feature implementation complete!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All test notifications sent!"
echo ""
echo "📋 Available notification types:"
echo "   • success   - Green checkmark, Glass sound"
echo "   • error     - Red X, Basso sound"
echo "   • warning   - Yellow warning, Purr sound"
echo "   • info      - Lightbulb, Pop sound"
echo "   • task      - Robot, Submarine sound"
echo "   • agent     - Wrench, Pop sound"
echo "   • build     - Construction, Glass sound"
echo "   • test      - Test tube, Pop sound"
echo "   • deploy    - Rocket, Glass sound"
echo "   • celebrate - Party, Glass sound"
echo ""
echo "📖 Usage from terminal:"
echo '   ~/.claude/hooks/notify.sh success "Title" "Message"'
echo ""
echo "📖 Usage from hooks (JSON):"
echo '   echo '\''{"type":"success","title":"Done","message":"Task complete"}'\'' | ~/.claude/hooks/notify.sh'
echo ""
