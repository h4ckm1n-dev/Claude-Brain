#!/bin/bash
# Quick restart of just the service (no rebuild needed)
# This applies the database reset fix

echo "🔄 Restarting service to apply code changes..."
docker compose restart claude-mem-service

echo "⏳ Waiting for service to be healthy..."
for i in {1..15}; do
    if curl -s http://localhost:8100/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        echo ""
        echo "📊 Service info:"
        curl -s "http://localhost:8100/health" | python3 -m json.tool | head -5
        echo ""
        echo "✨ Database reset should now work!"
        echo ""
        echo "Note: File watcher will still fail until you run:"
        echo "  ./restart-and-rebuild.sh"
        exit 0
    fi
    echo "   Waiting... ($i/15)"
    sleep 2
done

echo "❌ Service didn't become healthy in time"
echo "Check logs with: docker compose logs claude-mem-service"
