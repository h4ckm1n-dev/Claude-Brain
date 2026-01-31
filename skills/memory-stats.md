---
name: memory-stats
shortcut: /memory stats
description: View memory system statistics
---

# Memory Stats Skill

Display statistics about the memory system.

## Usage
```
/memory stats
```

## Implementation

When this skill is invoked:

1. Call the `memory_stats` MCP tool
2. Display formatted statistics

```
Use the memory_stats tool to get:
- Total memory count
- Breakdown by type
- Unresolved errors count
- Average usefulness score

Format as:
## Memory Statistics

Total: {count} memories
Unresolved Errors: {count}

By Type:
- errors: {count}
- docs: {count}
- decisions: {count}
- patterns: {count}
- learnings: {count}

Health: {status based on metrics}
```

## Additional Commands

```
/memory context          - Get recent relevant context
/memory resolve <id>     - Mark an error as resolved
/memory link <id1> <id2> - Link two related memories
```

## Notes
- Run weekly to monitor memory health
- High unresolved error count suggests cleanup needed
- Low usefulness scores trigger curation
