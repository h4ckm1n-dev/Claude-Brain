---
description: "Check memory system health and statistics"
---

# Memory Health Check

Run a comprehensive health check on the Claude Brain memory system:

1. Check service health: `curl -s http://localhost:8100/health`
2. Get memory stats using `memory_stats` MCP tool
3. Get graph stats using `graph_stats` MCP tool
4. Check for weak/fading memories using `get_weak_memories` MCP tool (limit 5)
5. Run `docker ps --filter name=claude-mem --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"` to check container status

Summarize as a dashboard:
- Service: UP/DOWN
- Total memories count
- Graph nodes & relationships
- Weak memories (at risk of being lost)
- Container status & uptime
- Any issues or recommendations
