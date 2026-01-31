#!/bin/bash

set -e

echo "🚀 Claude Memory Dashboard Setup"
echo "================================="

# Check Node.js version
echo "Checking Node.js version..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version must be 18 or higher. Current: $(node -v)"
    exit 1
fi
echo "✅ Node.js version: $(node -v)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed (skipping)"
fi

# Check if Memory API is running
echo ""
echo "🔍 Checking Memory API..."
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo "✅ Memory API is running on http://localhost:8100"
else
    echo "⚠️  Memory API is not running"
    echo "   Start it with: cd .. && docker compose up"
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    echo "VITE_API_URL=http://localhost:8100" > .env
    echo "✅ Created .env file"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start Memory API: cd .. && docker compose up"
echo "  2. Start dev server: npm run dev"
echo "  3. Open browser: http://localhost:5173"
echo ""
echo "For production build:"
echo "  npm run build"
echo "  # Output will be in dist/ directory"
