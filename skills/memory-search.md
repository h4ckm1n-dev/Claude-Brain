---
name: memory-search
shortcut: /memory search
description: Search memories using natural language
---

# Memory Search Skill

Search the memory system using semantic similarity.

## Usage
```
/memory search <query>
```

## Examples
```
/memory search typescript import errors
/memory search how to fix CORS issues
/memory search authentication patterns
/memory search decisions about state management
```

## Implementation

When this skill is invoked:

1. Extract the search query from the user's input
2. Call the `search_memory` MCP tool with the query
3. Display results in a readable format

```
Use the search_memory tool with:
- query: "{user's search query}"
- limit: 10
- min_score: 0.5

Format results showing:
- Memory type and score
- Content summary
- Solution if available
- Tags
```

## Notes
- Requires memory service running (`docker compose up -d` in ~/.claude/memory)
- Results are ranked by semantic similarity, not keyword matching
- Use specific terms for better results
