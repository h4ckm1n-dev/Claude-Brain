---
description: "Archive dead memories, remove boilerplate, reinforce valuable ones, and pin critical memories"
allowed-tools: ["mcp__memory__get_weak_memories", "mcp__memory__archive_memory", "mcp__memory__forget_memory", "mcp__memory__pin_memory", "mcp__memory__unpin_memory", "mcp__memory__reinforce_memory", "Bash"]
model: sonnet
---

# Memory Cleanup

Find and remove weak, dead, and boilerplate memories. Reinforce valuable ones.

---

## Step 1: Gather Candidates

Run in parallel:

1. `get_weak_memories(strength_threshold=0.3, limit=50)` — fading memories
2. Scroll Qdrant for boilerplate memories:
```bash
curl -s 'http://localhost:6333/collections/memories/points/scroll' \
  -H 'Content-Type: application/json' \
  -d '{"filter":{"must":[{"key":"archived","match":{"value":false}},{"key":"tags","match":{"any":["auto-captured","session-start","session-end"]}}]},"limit":100,"with_payload":true,"with_vector":false}'
```

---

## Step 2: Categorize

From the gathered data, build three lists:

### Dead Memories
Weak memories where ALL of:
- Strength < 0.1
- Access count is 0 or very low
- Created more than 30 days ago (estimate from ID timestamp)

### Boilerplate Memories
Memories tagged `auto-captured` / `session-start` / `session-end` with boilerplate content:
- "session started for project"
- "session closed at"
- "session ended at"
- "session resumed for project"

### Weak-but-Valuable
Weak memories where ANY of:
- Access count > 3 (frequently accessed despite low strength)
- Is pinned
- Has 2+ relationships in `relations` array
- Type is `decision` or `pattern` (higher inherent value)

Display categorization:
```
CLEANUP CANDIDATES
===================
Dead memories:         {N} (strength < 0.1, old, unused)
Boilerplate:           {N} (auto-captured session noise)
Weak-but-valuable:     {N} (worth saving)
Other weak:            {N} (below threshold but not clearly dead)
```

---

## Step 3: Archive Boilerplate

For each boilerplate memory:
- Call `archive_memory(memory_id="{id}")`
- Log: "Archived boilerplate: {content_preview}"

---

## Step 4: Archive Dead Memories

For each dead memory (be conservative — skip if unsure):
- Call `archive_memory(memory_id="{id}")`
- Log: "Archived dead: {content_preview}"

---

## Step 5: Reinforce Valuable Memories

For each weak-but-valuable memory:
- Call `reinforce_memory(memory_id="{id}", boost_amount=0.3)`
- Log: "Reinforced: {content_preview} (strength boosted by 0.3)"

---

## Step 6: Pin Suggestions

If any `decision` or `pattern` memories with high access (>5) are not already pinned, suggest pinning them. List up to 5 candidates and ask the user if they want to pin any.

If the user confirms, call `pin_memory(memory_id="{id}")` for each selected memory.

---

## Step 7: Summary

```
CLEANUP REPORT
===============
Boilerplate archived: {N}
Dead archived:        {N}
Reinforced:           {N}
Pinned:               {N}
Total cleaned:        {N}
Remaining weak:       {N}
```
