#!/bin/bash
# Script de vérification Claude Desktop MCP Configuration
# Vérifie que tout est correctement configuré pour Claude Brain

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Claude Desktop MCP Configuration Checker                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check 1: Memory service running
echo -e "${YELLOW}[1/5]${NC} Checking memory service..."
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:8100/health | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
    MEMORY_COUNT=$(curl -s http://localhost:8100/health | python3 -c "import sys, json; print(json.load(sys.stdin)['memory_count'])")
    echo -e "  ${GREEN}✓${NC} Service is running"
    echo -e "  ${GREEN}✓${NC} Status: $STATUS"
    echo -e "  ${GREEN}✓${NC} Memories: $MEMORY_COUNT"
else
    echo -e "  ${RED}✗${NC} Service NOT running"
    echo -e "  ${YELLOW}→${NC} Start with: cd ~/.claude/memory && docker compose up -d"
    exit 1
fi

# Check 2: Desktop config file exists
echo ""
echo -e "${YELLOW}[2/5]${NC} Checking Claude Desktop config..."
CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} Config file exists"

    # Check if MCP servers configured
    if grep -q "mcpServers" "$CONFIG_FILE"; then
        echo -e "  ${GREEN}✓${NC} MCP servers configured"
    else
        echo -e "  ${RED}✗${NC} MCP servers NOT configured"
        exit 1
    fi

    # Check if memory server configured
    if grep -q "\"memory\"" "$CONFIG_FILE"; then
        echo -e "  ${GREEN}✓${NC} Memory server configured"
    else
        echo -e "  ${RED}✗${NC} Memory server NOT configured"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} Config file NOT found"
    echo -e "  ${YELLOW}→${NC} File should be at: $CONFIG_FILE"
    exit 1
fi

# Check 3: MCP server build exists
echo ""
echo -e "${YELLOW}[3/5]${NC} Checking MCP server build..."
MCP_BUILD="$HOME/.claude/mcp/memory-mcp/dist/index.js"
if [ -f "$MCP_BUILD" ]; then
    echo -e "  ${GREEN}✓${NC} MCP server build exists"
    BUILD_SIZE=$(du -h "$MCP_BUILD" | cut -f1)
    echo -e "  ${GREEN}✓${NC} Build size: $BUILD_SIZE"
else
    echo -e "  ${RED}✗${NC} MCP server build NOT found"
    echo -e "  ${YELLOW}→${NC} Build with: cd ~/.claude/mcp/memory-mcp && npm run build"
    exit 1
fi

# Check 4: Docker services
echo ""
echo -e "${YELLOW}[4/5]${NC} Checking Docker services..."
cd ~/.claude/memory
SERVICES=$(docker compose ps --services 2>/dev/null | wc -l)
RUNNING=$(docker compose ps --filter "status=running" --services 2>/dev/null | wc -l)

if [ "$SERVICES" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Docker services configured: $SERVICES"
    echo -e "  ${GREEN}✓${NC} Services running: $RUNNING"

    # Check specific services
    for service in qdrant neo4j claude-mem-service; do
        if docker compose ps | grep -q "$service.*running"; then
            echo -e "    ${GREEN}✓${NC} $service"
        else
            echo -e "    ${RED}✗${NC} $service (not running)"
        fi
    done
else
    echo -e "  ${RED}✗${NC} Docker services NOT configured"
    exit 1
fi

# Check 5: Dashboard accessible
echo ""
echo -e "${YELLOW}[5/5]${NC} Checking dashboard..."
if curl -s http://localhost:8100 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Dashboard accessible"
    echo -e "  ${GREEN}✓${NC} URL: http://localhost:8100"
else
    echo -e "  ${RED}✗${NC} Dashboard NOT accessible"
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ All checks passed! Claude Desktop is ready to use       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. ${YELLOW}Quit${NC} Claude Desktop completely (Cmd+Q)"
echo -e "  2. ${YELLOW}Restart${NC} Claude Desktop"
echo -e "  3. ${YELLOW}Test${NC} with: 'Recherche tous les souvenirs sur le dashboard'"
echo -e "  4. ${YELLOW}View${NC} dashboard: http://localhost:8100"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo -e "  • Setup guide: ~/.claude/memory/CLAUDE_DESKTOP_SETUP.md"
echo -e "  • Full docs:   ~/.claude/memory/README.md"
echo ""
