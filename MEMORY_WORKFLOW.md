# MANDATORY MEMORY WORKFLOW

## 🚨 BLOCKING RULES - Claude MUST Follow

### RULE 1: SEARCH FIRST (MANDATORY)
**BEFORE starting ANY technical task, Claude MUST run `search_memory`**

```
User asks: "Fix WhatsApp duplicate messages"
↓
IMMEDIATELY: search_memory("WhatsApp duplicate messages group booking")
↓
THEN: Start working with context from memories
```

**NO EXCEPTIONS** - Even if the task seems simple, search first.

---

### RULE 2: STORE CONTINUOUSLY (MANDATORY)

Claude MUST call `store_memory` **IMMEDIATELY** after:

#### ✅ Trigger Events (Auto-store required):

| Event | Store When | Example |
|-------|-----------|---------|
| **Error Fixed** | Solution found | `store_memory(type="error", content="Trigger excluded group parents", solution="Use parent_booking_id IS NULL")` |
| **Decision Made** | Architecture choice | `store_memory(type="decision", content="Use Above Laos API", rationale="Real-time data")` |
| **Pattern Discovered** | Reusable pattern | `store_memory(type="pattern", content="Parent-child booking model")` |
| **WebFetch/WebSearch** | After fetching docs | `store_memory(type="docs", content="API usage from documentation")` |
| **Workaround Found** | Non-obvious fix | `store_memory(type="learning", content="Docker restart needed after code change")` |

---

### RULE 3: SESSION START CHECKLIST

**Every session MUST start with:**

```markdown
□ search_memory() for relevant context (query based on user's first message)
□ get_context(project="ProjectName") for recent work
□ Review suggested memories from hook
```

**Example:**
```
User: "The chatbot isn't showing availability"
↓
□ search_memory("chatbot availability balloon")
□ get_context(project="Enduro")
□ Then start debugging
```

---

## 📋 WORKFLOW TEMPLATE

### Start of Session:
1. User describes problem/task
2. **IMMEDIATELY** `search_memory(query="[keywords from user message]")`
3. **IMMEDIATELY** `get_context(project="[project]")`
4. Review results
5. Start work **informed by memories**

### During Work:
- Fixed error? → `store_memory(type="error", ...)` RIGHT NOW
- Made decision? → `store_memory(type="decision", ...)` RIGHT NOW
- Found pattern? → `store_memory(type="pattern", ...)` RIGHT NOW

### End of Session:
- Review what was accomplished
- Store any remaining learnings
- Link related memories if needed

---

## ❌ ANTI-PATTERNS (What NOT to do)

**BAD:**
```
User: "Fix WhatsApp issue"
Claude: [Immediately starts debugging without searching]
Claude: [Fixes issue]
Claude: [Doesn't store solution]
User: "Why didn't you use memory?"
Claude: "Oh sorry, let me save it now"
```

**GOOD:**
```
User: "Fix WhatsApp issue"
Claude: [search_memory("WhatsApp issue")]
Claude: [Reviews existing solutions]
Claude: [Fixes issue]
Claude: [store_memory RIGHT AWAY with solution]
```

---

## 🎯 SUCCESS METRICS

Claude is using memory correctly when:
- ✅ Every session starts with `search_memory`
- ✅ Every problem solved has a `store_memory`
- ✅ User NEVER has to ask "why didn't you use memory?"
- ✅ Future sessions benefit from past learnings

---

## 💡 MENTAL MODEL

Think of memory system like Git:
- `search_memory` = `git pull` (get latest knowledge)
- `store_memory` = `git commit` (save your work)
- Not using it = losing all your work

**You would NEVER code without git. Same applies to memory.**
