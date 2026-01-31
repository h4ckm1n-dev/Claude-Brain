#!/bin/bash

# Claude Brain - One-Command Startup Script
# Starts the complete Claude Brain system using Docker Compose

set -e

echo "🧠 Claude Brain - Starting Complete System"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Navigate to memory directory
cd memory

# Start Docker Compose
echo "🐳 Starting Docker Compose stack..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Services are running"
else
    echo "❌ Some services failed to start. Check logs with: docker compose logs"
    exit 1
fi

echo ""
echo "🎉 Claude Brain is ready!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Access Points:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🌐 Dashboard:      http://localhost:8100"
echo "  📖 API Docs:       http://localhost:8100/docs"
echo "  🗄️  Qdrant UI:      http://localhost:6333/dashboard"
echo "  🕸️  Neo4j Browser:  http://localhost:7474"
echo "      └─ Username: neo4j"
echo "      └─ Password: memory_graph_2024"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Running Services:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
docker compose ps
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Useful Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  View logs:     cd memory && docker compose logs -f"
echo "  Stop services: cd memory && docker compose down"
echo "  Restart:       cd memory && docker compose restart"
echo "  Full reset:    cd memory && docker compose down -v"
echo ""
echo "📖 Full documentation: ./memory/README.md"
echo ""
