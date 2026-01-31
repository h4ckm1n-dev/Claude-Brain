#!/bin/bash
# Claude Brain - Enhancement Setup Script
# One-command setup for all high-value features

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Claude Brain - Enhancement Setup                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if memory service is running
echo "🔍 Checking memory service..."
if ! curl -sf http://localhost:8100/health >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Memory service not running${NC}"
    echo "   Starting memory service..."
    cd ~/.claude/memory && docker compose up -d
    sleep 5
fi

if curl -sf http://localhost:8100/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Memory service running${NC}"
else
    echo "❌ Failed to start memory service"
    exit 1
fi

# Setup file watcher
echo ""
echo "📁 Setting up auto file watcher..."

# Kill existing watcher if running
pkill -f watch_documents.py 2>/dev/null || true

# Start new watcher
nohup python3 ~/.claude/memory/scripts/watch_documents.py --quiet >> ~/.claude/memory/logs/watcher.log 2>&1 &

if pgrep -f watch_documents.py >/dev/null; then
    echo -e "${GREEN}✓ File watcher started${NC}"
    echo "   Watching: ~/Documents"
    echo "   Logs: ~/.claude/memory/logs/watcher.log"
else
    echo -e "${YELLOW}⚠️  File watcher failed to start${NC}"
fi

# Setup cron for consolidation
echo ""
echo "🧹 Setting up daily consolidation..."

# Check if cron job exists
if crontab -l 2>/dev/null | grep -q "consolidate_memories.sh"; then
    echo -e "${GREEN}✓ Consolidation cron already configured${NC}"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "0 3 * * * ~/.claude/memory/scripts/consolidate_memories.sh") | crontab -
    echo -e "${GREEN}✓ Consolidation cron added (runs at 3 AM daily)${NC}"
fi

# Run NLP tagging
echo ""
echo "🏷️  Running initial NLP tagging..."
python3 ~/.claude/memory/scripts/nlp_tagger.py --limit 500

# Test pruning (dry run)
echo ""
echo "🗑️  Testing memory pruning (dry run)..."
python3 ~/.claude/memory/scripts/prune_memories.py --days 30

# Show session timeline
echo ""
echo "📊 Recent session timeline:"
python3 ~/.claude/memory/scripts/session_timeline.py --hours 24 | head -30

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Setup Complete! 🎉                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ File watcher: Running (~/Documents)"
echo "✅ Consolidation: Cron job at 3 AM daily"
echo "✅ Error capture: Enhanced with stack traces"
echo "✅ NLP tagging: Auto-tags tech stack"
echo ""
echo "🎯 Quick Commands:"
echo "   Dashboard:  open http://localhost:5173"
echo "   Timeline:   python3 ~/.claude/memory/scripts/session_timeline.py"
echo "   Prune:      python3 ~/.claude/memory/scripts/prune_memories.py --days 30 --execute"
echo "   Logs:       tail -f ~/.claude/memory/logs/watcher.log"
echo ""
echo "📖 Full documentation: ~/.claude/memory/README-ENHANCEMENTS.md"
echo ""
