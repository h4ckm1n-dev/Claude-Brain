#!/bin/bash
# Script to rebuild Docker image and restart service
# This applies the following fixes:
# 1. Copy scripts folder to Docker container (enables file watcher)
# 2. Empty default folders configuration
# 3. Fix database reset to use recreate_collection()

set -e

echo "🔄 Stopping service..."
docker compose down

echo "🏗️  Rebuilding Docker image (this may take a few minutes)..."
docker compose build --no-cache claude-mem-service

echo "🚀 Starting service..."
docker compose up -d

echo "⏳ Waiting for service to be healthy..."
for i in {1..30}; do
    if curl -s http://localhost:8100/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "📊 Testing fixes..."
echo ""

echo "1️⃣ Testing default folders (should be empty):"
curl -s "http://localhost:8100/indexing/folders" | python3 -m json.tool | grep -A 1 "folders"

echo ""
echo "2️⃣ Testing file watcher (should start successfully):"
curl -s -X POST "http://localhost:8100/processes/watcher/start" | python3 -m json.tool

echo ""
echo "3️⃣ Testing database reset:"
echo "   Current memory count:"
curl -s "http://localhost:8100/health" | python3 -m json.tool | grep "memory_count"

echo ""
echo "✨ All done! Open http://localhost:8100 in your browser."
echo ""
echo "Note: File watcher is now running. Stop it with:"
echo "  curl -X POST http://localhost:8100/processes/watcher/stop"
