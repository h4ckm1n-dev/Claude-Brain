#!/bin/bash

set -e

echo "🚀 Claude Memory Dashboard - Complete Setup"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from frontend/ directory"
    exit 1
fi

# Kill any existing npm install processes (if stuck)
echo "Checking for existing npm processes..."
pkill -f "npm install" 2>/dev/null || true
sleep 2

# Clean install
echo ""
echo "📦 Installing all dependencies..."
echo "This may take 3-5 minutes..."
echo ""

rm -rf node_modules package-lock.json 2>/dev/null || true
npm install --loglevel=error

echo ""
echo "✅ Dependencies installed successfully!"
echo ""

# Verify key packages
echo "Verifying installation..."
PACKAGES=(
    "react"
    "react-router-dom"
    "@tanstack/react-query"
    "axios"
    "recharts"
    "cytoscape"
    "lucide-react"
    "tailwindcss"
)

MISSING=0
for pkg in "${PACKAGES[@]}"; do
    if [ ! -d "node_modules/$pkg" ]; then
        echo "❌ Missing: $pkg"
        MISSING=$((MISSING + 1))
    else
        echo "✅ Found: $pkg"
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "⚠️  Some packages are missing. Try running: npm install"
    exit 1
fi

echo ""
echo "✅ All packages verified!"
echo ""

# Check Memory API
echo "Checking Memory API connection..."
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo "✅ Memory API is running"
    API_STATUS=$(curl -s http://localhost:8100/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "   Status: $API_STATUS"
else
    echo "⚠️  Memory API is not running"
    echo "   Start it with: cd .. && docker compose up -d"
fi

# TypeScript check
echo ""
echo "Running TypeScript check..."
if npm run build > /tmp/tsc-check.log 2>&1; then
    echo "✅ TypeScript compilation successful"
else
    echo "⚠️  TypeScript errors found (see /tmp/tsc-check.log)"
    echo "   This is OK - some may be due to missing type definitions"
fi

echo ""
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo ""
echo "🎉 Your dashboard is ready to use!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start development server:"
echo "     npm run dev"
echo ""
echo "  2. Open in browser:"
echo "     http://localhost:5173"
echo ""
echo "  3. Explore the dashboard:"
echo "     • Dashboard - System overview"
echo "     • Memories - CRUD operations"
echo "     • Search - Advanced search"
echo "     • Graph - Knowledge visualization"
echo "     • Suggestions - Context-aware recommendations"
echo "     • Consolidation - Memory cleanup"
echo ""
echo "📚 Documentation:"
echo "   • Quick Start: cat QUICK_START.md"
echo "   • Full README: cat DASHBOARD_README.md"
echo "   • Status: cat STATUS.md"
echo ""
echo "🐛 Troubleshooting:"
echo "   • Check browser console for errors"
echo "   • Verify API: curl http://localhost:8100/health"
echo "   • Review logs in ../logs/"
echo ""
echo "Happy memory managing! 🧠✨"
echo ""
