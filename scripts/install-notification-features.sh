#!/bin/bash
# Install Enhanced Notification Features for Claude Code
# This installs terminal-notifier which enables:
#   - Action buttons on notifications
#   - Better customization
#   - Notification grouping
#   - Click callbacks

set -euo pipefail

echo "🔔 Claude Code Notification Enhancement Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if already installed
if command -v terminal-notifier &> /dev/null; then
    echo "✅ terminal-notifier is already installed!"
    terminal-notifier -version
    echo ""
    echo "Your notifications are already enhanced. Run the test:"
    echo "  ~/.claude/scripts/test-notifications.sh"
    exit 0
fi

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew is not installed."
    echo ""
    echo "Install Homebrew first:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    echo "Or continue with basic AppleScript notifications (still works, just fewer features)"
    exit 1
fi

echo "📦 Installing terminal-notifier via Homebrew..."
echo ""

brew install terminal-notifier

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation complete!"
echo ""
echo "Enhanced features now available:"
echo "   ✓ Action buttons on notifications"
echo "   ✓ Notification grouping"
echo "   ✓ Better sound control"
echo "   ✓ Click-to-dismiss"
echo ""
echo "Test your new notifications:"
echo "  ~/.claude/scripts/test-notifications.sh"
echo ""
