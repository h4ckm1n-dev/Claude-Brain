# Phase 1.3: Session-based Memory Extraction

**Status:** ✅ Implemented
**Date:** 2026-02-02
**Research Foundation:** Mem0 Conversational Context Extraction

---

## Overview

Phase 1.3 implements session-based memory extraction, enabling the system to understand and preserve conversational context across multi-turn interactions. Unlike isolated memory storage, this approach tracks entire conversation flows and extracts relationships from the natural progression of dialogue.

### Key Research Insight

> "Mem0 processes a pair of messages between either two user participants or a user and an assistant, extracting memories from conversational context rather than isolated facts. This approach preserves the narrative flow and causal relationships inherent in conversations."

---

## Core Concepts

### 1. Conversation Session

A **session** represents a continuous conversation thread. Sessions have:
- **session_id**: Unique identifier
- **timeout**: 2 hours of inactivity (configurable)
- **memories**: Ordered sequence of memories created during conversation
- **context**: Previous messages for contextual understanding

### 2. Session Tracking

Each memory can be associated with a session via three fields:
- **session_id**: Links memory to a conversation
- **conversation_context**: Summary of previous 3 memories
- **session_sequence**: Order within session (0, 1, 2, ...)

### 3. Conversation Context Extraction

When storing a memory with a session_id, the system automatically:
1. Retrieves previous memories in session
2. Extracts last 3 memories as context
3. Creates summary: `"[1] ERROR: content → [2] CONTEXT: content → [3] LEARNING: content"`
4. Stores in `conversation_context` field

### 4. Session Consolidation

After 24 hours, sessions are automatically consolidated:
1. **Infer Relationships**: Create FOLLOWS (sequential) and causal chains (FIXES, SUPPORTS)
2. **Create Summary**: Generate CONTEXT-type memory summarizing entire session
3. **Link Memories**: Connect all session memories to summary with PART_OF relationships

---

## Implementation Details

### 1. Memory Model Extensions

Added three new fields to `Memory` model:

```python
# Session-based memory extraction (Phase 1.3)
session_id: Optional[str] = None           # Conversation session identifier
conversation_context: Optional[str] = None  # Previous messages for context
session_sequence: Optional[int] = None      # Order within session (0, 1, 2, ...)
```

### 2. Session Extraction Module

Created `src/session_extraction.py` with `SessionManager` class:

**Methods:**
- `generate_session_id()` - Create new session ID
- `get_or_create_session()` - Get existing or create new
- `get_session_memories()` - Retrieve all memories in session (ordered)
- `extract_conversation_context()` - Build context from previous memories
- `infer_session_relationships()` - Create FOLLOWS and causal relationships
- `consolidate_session()` - Generate summary and link memories
- `get_sessions_for_consolidation()` - Find sessions ready for consolidation
- `get_session_stats()` - Statistics about sessions

### 3. Integration with Memory Storage

Modified `collections.store_memory()` to support session tracking:

```python
# If session_id provided, get conversation context
if session_id and not conversation_context:
    previous_memories = SessionManager.get_session_memories(client, COLLECTION_NAME, session_id)
    conversation_context = SessionManager.extract_conversation_context(previous_memories)
    session_sequence = len(previous_memories)  # Auto-sequence

memory = Memory(
    # ... other fields ...
    session_id=session_id,
    conversation_context=conversation_context,
    session_sequence=session_sequence
)
```

### 4. Relationship Inference within Sessions

Sessions enable powerful causal chain detection:

**Sequential Relationships (FOLLOWS):**
```
Memory 1 → Memory 2 → Memory 3 → Memory 4
```
Every pair gets a FOLLOWS relationship.

**Causal Chains:**
- ERROR → LEARNING/DECISION → **FIXES** relationship
- PATTERN → LEARNING/DECISION → **SUPPORTS** relationship

**Example Flow:**
```
[0] ERROR: "PostgreSQL connection timeout"
[1] CONTEXT: "Checked logs - connection pool exhausted"
[2] LEARNING: "Fixed by increasing max_connections to 50"
[3] PATTERN: "Always use connection pooler for production"

Relationships Created:
- Memory 1 FOLLOWS Memory 0
- Memory 2 FOLLOWS Memory 1
- Memory 3 FOLLOWS Memory 2
- Memory 2 FIXES Memory 0 (causal chain detected)
- Memory 3 SUPPORTS Memory 2 (pattern supports solution)
```

### 5. Session Consolidation

After 24 hours (configurable), sessions are consolidated:

**Process:**
1. Check if session has ≥2 memories
2. Check if last memory is >24 hours old
3. Check if summary doesn't already exist
4. If eligible:
   - Infer all session relationships
   - Create summary memory (type: CONTEXT)
   - Link all memories to summary (PART_OF)

**Summary Content:**
```
Session summary (4 memories):
Problem-solving session: 1 errors, 2 solutions

Sequence:
- ERROR: PostgreSQL connection timeout error when attempting to...
- CONTEXT: Checked database logs - seeing multiple connection attempts...
- LEARNING: Fixed by increasing max_connections from 20 to 50 and...
- PATTERN: Always use connection pooler (like PgBouncer) for production...
```

### 6. Scheduled Consolidation

Added scheduler job (runs every 12 hours):

```python
@app.add_job(run_session_consolidation, trigger=IntervalTrigger(hours=12))
def run_session_consolidation():
    ready_sessions = SessionManager.get_sessions_for_consolidation(...)
    for session_id in ready_sessions:
        SessionManager.infer_session_relationships(...)
        SessionManager.consolidate_session(...)
```

---

## Architecture

### Files Modified

1. **`src/models.py`**
   - Added `session_id`, `conversation_context`, `session_sequence` to Memory
   - Added same fields to MemoryCreate

2. **`src/collections.py`**
   - Enhanced `store_memory()` with session tracking
   - Auto-extract conversation context when session_id provided

3. **`src/scheduler.py`**
   - Added `run_session_consolidation()` job (12h interval)

### Files Created

1. **`src/session_extraction.py`** (NEW - 380 lines)
   - SessionManager class with all session operations
   - Conversation context extraction
   - Session consolidation logic
   - Relationship inference within sessions

2. **`tests/test_phase_1_3_sessions.sh`** (NEW)
   - Comprehensive test suite (13 tests)
   - Tests session creation, tracking, consolidation

3. **`docs/PHASE_1_3_SESSION_EXTRACTION.md`** (NEW)
   - This documentation file

### API Endpoints Added

Added 5 new endpoints in `src/server.py`:

1. `GET /sessions/stats` - Session statistics
2. `GET /sessions/{session_id}/memories` - Get all memories in session
3. `POST /sessions/{session_id}/consolidate` - Manual consolidation
4. `POST /sessions/consolidate/batch` - Batch consolidation
5. `POST /sessions/new` - Create new session

---

## API Reference

### POST /sessions/new

Create a new conversation session.

**Query Parameters:**
- `project` (optional): Project name to associate with session

**Response:**
```json
{
  "session_id": "session_019c1234-5678-...",
  "project": "my-project",
  "created_at": "2026-02-02T10:30:00Z"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8100/sessions/new?project=my-app"
```

### POST /memories (with session)

Store memory with session tracking.

**Request Body:**
```json
{
  "type": "error",
  "content": "Getting database connection timeout",
  "tags": ["database", "error"],
  "project": "my-app",
  "session_id": "session_019c1234-...",
  "error_message": "connection timeout"
}
```

**Automatic Behavior:**
- Retrieves previous memories in session
- Extracts conversation context from last 3
- Sets `session_sequence` automatically
- Stores `conversation_context` in memory

### GET /sessions/{session_id}/memories

Get all memories in a session, ordered by sequence.

**Response:**
```json
[
  {
    "id": "019c1234-...",
    "type": "error",
    "content": "...",
    "session_sequence": 0,
    "conversation_context": null
  },
  {
    "id": "019c5678-...",
    "type": "learning",
    "content": "...",
    "session_sequence": 1,
    "conversation_context": "[1] ERROR: Getting database..."
  }
]
```

### POST /sessions/{session_id}/consolidate

Manually trigger consolidation for a session.

**Response:**
```json
{
  "status": "consolidated",
  "session_id": "session_019c1234-...",
  "summary_id": "019c9abc-...",
  "relationships_created": 5
}
```

**What It Does:**
1. Creates FOLLOWS relationships between sequential memories
2. Identifies causal chains (ERROR → LEARNING → FIXES)
3. Creates summary memory (type: CONTEXT)
4. Links all memories to summary (PART_OF)

### POST /sessions/consolidate/batch

Batch consolidate all eligible sessions.

**Query Parameters:**
- `older_than_hours` (default: 24): Consolidate sessions older than N hours

**Response:**
```json
{
  "total_ready": 5,
  "consolidated": 4,
  "failed": 1,
  "results": [
    {
      "session_id": "session_...",
      "summary_id": "019c...",
      "status": "success",
      "links_created": 3
    }
  ]
}
```

### GET /sessions/stats

Get statistics about conversation sessions.

**Response:**
```json
{
  "total_sessions": 42,
  "total_memories_in_sessions": 156,
  "avg_memories_per_session": 3.71,
  "sessions_with_summary": 35,
  "sessions_without_summary": 7,
  "config": {
    "session_timeout_hours": 2,
    "consolidation_delay_hours": 24,
    "max_context_chars": 500
  }
}
```

---

## Configuration

### Environment Variables

```bash
# Session timeout (hours of inactivity)
SESSION_TIMEOUT_HOURS=2

# Consolidation delay (wait before consolidating)
SESSION_CONSOLIDATION_DELAY_HOURS=24

# Enable scheduler for automatic consolidation
SCHEDULER_ENABLED=true
```

### Constants in Code

```python
# session_extraction.py

SESSION_TIMEOUT_HOURS = 2  # Session considered inactive after 2h
SESSION_CONSOLIDATION_DELAY_HOURS = 24  # Wait 24h before consolidating
MAX_CONVERSATION_CONTEXT_CHARS = 500  # Limit context length
```

---

## Usage Examples

### Example 1: Basic Session Tracking

```bash
# Create session
SESSION_ID=$(curl -X POST "http://localhost:8100/sessions/new?project=my-app" | jq -r '.session_id')

# Store memories in session
curl -X POST http://localhost:8100/memories \
  -d "{
    \"type\": \"error\",
    \"content\": \"API returning 500 error\",
    \"tags\": [\"api\", \"error\"],
    \"project\": \"my-app\",
    \"session_id\": \"$SESSION_ID\"
  }"

curl -X POST http://localhost:8100/memories \
  -d "{
    \"type\": \"learning\",
    \"content\": \"Fixed by updating dependency version\",
    \"tags\": [\"api\", \"solution\"],
    \"project\": \"my-app\",
    \"session_id\": \"$SESSION_ID\"
  }"

# View session
curl "http://localhost:8100/sessions/$SESSION_ID/memories" | jq '.'
```

### Example 2: Conversation Context

```python
# Memory 1 (no context yet)
{
  "content": "Database slow",
  "session_id": "session_123",
  "conversation_context": null,  # First in session
  "session_sequence": 0
}

# Memory 2 (has context from Memory 1)
{
  "content": "Checked query - missing index",
  "session_id": "session_123",
  "conversation_context": "[1] ERROR: Database slow",
  "session_sequence": 1
}

# Memory 3 (has context from Memory 1 & 2)
{
  "content": "Added index on user_id column",
  "session_id": "session_123",
  "conversation_context": "[1] ERROR: Database slow → [2] CONTEXT: Checked query...",
  "session_sequence": 2
}
```

### Example 3: Manual Consolidation

```bash
# Consolidate session after conversation ends
curl -X POST "http://localhost:8100/sessions/$SESSION_ID/consolidate"

# Result:
# - Creates summary memory
# - Links all 3 memories to summary
# - Creates FOLLOWS relationships (1→2→3)
# - Creates FIXES relationship (3→1)
```

---

## Testing

Run the test suite:

```bash
cd /Users/h4ckm1n/.claude/memory
./tests/test_phase_1_3_sessions.sh
```

**Test Coverage:**
- ✓ Session creation
- ✓ Memory storage with session_id
- ✓ Conversation context extraction
- ✓ Session sequence ordering
- ✓ Session memory retrieval
- ✓ Manual consolidation
- ✓ Summary memory generation
- ✓ FOLLOWS relationships (sequential)
- ✓ FIXES relationships (causal chains)
- ✓ PART_OF relationships (to summary)
- ✓ Batch consolidation
- ✓ Session statistics

---

## Expected Outcomes

### 1. Conversational Understanding

**Target:** Preserve narrative flow across multi-turn interactions
**Mechanism:** conversation_context field captures previous messages

**Example:**
```
Without sessions: 3 isolated memories
With sessions: 3 connected memories with flow context
→ LLM can understand "it" refers to error from 2 steps ago
```

### 2. Causal Chain Detection

**Target:** Automatically identify cause→effect→solution patterns
**Mechanism:** Session-aware relationship inference

**Patterns Detected:**
- ERROR → LEARNING → FIXES relationship
- PATTERN → DECISION → SUPPORTS relationship
- Sequential FOLLOWS relationships

### 3. Session Summaries

**Target:** Consolidate conversations into searchable summaries
**Mechanism:** Automatic consolidation after 24 hours

**Benefit:** Search for "database timeout solution" → finds session summary → traverses to individual memories

### 4. Reduced Fragmentation

**Target:** Group related memories together
**Current:** Memories scattered across timeline
**After Phase 1.3:** Memories grouped by conversation session

---

## Monitoring

### Key Metrics

```bash
# Session statistics
curl http://localhost:8100/sessions/stats | jq '{
  total_sessions,
  avg_memories_per_session,
  sessions_without_summary
}'

# Check specific session
curl http://localhost:8100/sessions/{id}/memories | jq 'length'

# Monitor consolidation
curl http://localhost:8100/scheduler/status | jq '.jobs[] | select(.id == "session_consolidation_job")'

# Check graph for session relationships
curl http://localhost:8100/graph/stats | jq '.relationships_by_type.FOLLOWS'
```

### Dashboard Queries

```bash
# Find sessions ready for consolidation
curl "http://localhost:8100/sessions/consolidate/batch?older_than_hours=24" | jq '.total_ready'

# Get recent sessions
curl "http://localhost:8100/memories?limit=100" | jq '[.[] | select(.session_id != null)] | group_by(.session_id) | length'
```

---

## Performance Considerations

### Context Extraction Cost

- **Operation:** Retrieve previous memories + format context
- **Cost:** 1 scroll query per session memory store
- **Optimization:** Cache recent session memories in memory

### Consolidation Cost

- **Operation:** Infer relationships + create summary + link memories
- **Cost:** O(n) where n = memories in session
- **Optimization:** Run as scheduled job during low-usage hours

### Storage Impact

- 3 additional fields per memory: ~100 bytes average
- Total overhead: ~100 KB per 1000 memories
- Benefit: Rich contextual information outweighs cost

---

## Limitations & Trade-offs

### 1. Session Timeout

**Limitation:** 2-hour timeout may split long conversations
**Mitigation:** User can manually specify same session_id

### 2. Context Length

**Limitation:** Limited to last 3 memories (500 chars)
**Mitigation:** Full conversation preserved in memory sequence

### 3. Consolidation Delay

**Limitation:** 24-hour wait before automatic consolidation
**Mitigation:** Manual consolidation available anytime

### 4. Memory Overhead

**Limitation:** conversation_context duplicates some data
**Mitigation:** Context is lossy summary, not full duplication

---

## Future Enhancements

### 1. Advanced Context Window

- Sliding window vs. last-N
- Importance-weighted context (prioritize errors/solutions)
- Semantic compression (summarize long contexts)

### 2. Multi-user Sessions

- Track which user contributed each memory
- Support group conversations
- User-specific context views

### 3. Session Branching

- Fork sessions when topics diverge
- Merge related sessions
- Session hierarchy (parent/child)

### 4. Smart Consolidation

- Consolidate based on topic closure (not just time)
- Detect when problem is solved → consolidate immediately
- Learn optimal consolidation timing

### 5. Context Persistence

- Store conversation context in separate collection
- Query historical conversation flows
- Time-travel through conversation history

---

## Research References

1. **Mem0: Conversation Memory** (mem0.ai)
   - "Processes a pair of messages between user and assistant"
   - Extracts memories from conversational context
   - Preserves narrative flow and causal relationships

2. **Building Production-Ready AI Agents** (mem0.ai/research)
   - Context-aware memory extraction
   - Multi-turn conversation understanding

3. **Memory in the Age of AI Agents** (arXiv:2512.13564)
   - Episodic memory for conversation threads
   - Temporal context in agent memory systems

---

## Changelog

### 2026-02-02 - Phase 1.3 Initial Implementation
- ✅ Added session_id, conversation_context, session_sequence fields
- ✅ Created session_extraction.py module (380 lines)
- ✅ Implemented SessionManager class
- ✅ Hooked session tracking into store_memory()
- ✅ Added 5 new API endpoints
- ✅ Implemented scheduled consolidation job
- ✅ Created comprehensive test suite
- ✅ Documented all features

---

## Status & Next Steps

**Current Status:** Implementation complete, ready for service restart and testing

**Next Steps:**
1. Restart memory service to load new code
2. Run test suite: `./tests/test_phase_1_3_sessions.sh`
3. Monitor session statistics over 7 days
4. Measure context extraction effectiveness
5. Tune consolidation timing based on usage patterns
6. Begin Phase 2.1: Graph-based Search Expansion
