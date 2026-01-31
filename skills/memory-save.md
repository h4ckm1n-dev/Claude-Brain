---
name: memory-save
shortcut: /memory save
description: Manually save a memory
---

# Memory Save Skill

Manually store a memory in the vector database.

## Usage
```
/memory save <type> <content>
```

## Types
- `error` - An error you encountered
- `docs` - Useful documentation snippet
- `decision` - Architecture or design decision
- `pattern` - Reusable code pattern
- `learning` - Lesson learned

## Examples
```
/memory save error "Cannot find module '@/utils'" - need to configure path aliases in tsconfig.json
/memory save learning Always run 'npm run build' before deploying to catch TypeScript errors
/memory save decision Chose Zustand over Redux for state management due to simpler API
/memory save pattern Error boundary component with retry logic for async operations
/memory save docs React Query v5 requires explicit 'enabled' flag for conditional queries
```

## Implementation

When this skill is invoked:

1. Parse the type and content from user input
2. Extract any tags from the content (words after #)
3. Call the `store_memory` MCP tool

```
Use the store_memory tool with:
- type: "{parsed type}"
- content: "{parsed content}"
- tags: [extracted hashtags or inferred from content]
- project: "{current directory name}"
```

## Notes
- Memories are automatically embedded for semantic search
- Add hashtags to improve discoverability
- Error memories can later be marked as resolved
