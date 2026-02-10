---
description: "Smart memory search with query enhancement, semantic + document search, and graph exploration"
allowed-tools: ["mcp__memory__query_enhance", "mcp__memory__search_memory", "mcp__memory__search_documents", "mcp__memory__find_related", "mcp__memory__graph_recommendations"]
model: sonnet
---

# Smart Memory Search

Search the memory system using enhanced queries, semantic search, document search, and graph exploration.

**Input:** `$ARGUMENTS` (required — the search query)

If `$ARGUMENTS` is empty, ask the user what they want to search for and stop.

---

## Step 1: Enhance the Query

Call `query_enhance(query="$ARGUMENTS")` to expand synonyms and fix typos.

Log the enhanced query: "Enhanced: {original} → {enhanced_query}"

If the enhancement suggests corrections, note them.

---

## Step 2: Parallel Search

Run both searches in parallel using the **enhanced** query:

1. `search_memory(query="{enhanced_query}", limit=10)` — semantic + keyword memory search
2. `search_documents(query="$ARGUMENTS", limit=10)` — indexed file/code search

---

## Step 3: Display Results

Format results as two sections:

### Memory Results
For each memory result, show:
- Type badge, score, and ID
- Content preview (first 100 chars)
- Tags
- Project (if set)

### Document Results
For each document result, show:
- File path
- Relevance score
- Content snippet

If no results in either section, say so explicitly.

---

## Step 4: Graph Exploration (if results found)

If memory results were found, pick the top 2 most relevant memory IDs and run in parallel:

1. `find_related(memory_id="{top_result_id}", max_hops=2, limit=5)`
2. `graph_recommendations(memory_id="{top_result_id}", limit=5)`

Display any additional related or recommended memories that weren't in the original results.

If no memory results were found, skip this step.

---

## Output Summary

```
Search: "$ARGUMENTS"
Enhanced: "{enhanced_query}"
Memory hits: {N} | Document hits: {N} | Related: {N}
```
