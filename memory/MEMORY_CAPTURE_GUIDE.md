# Memory System - What Gets Captured

Automatic capture is now **ENHANCED** - captures MORE valuable information intelligently.

---

## 🎯 What Gets Auto-Captured

### 1. WebFetch - ALL Documentation (100% capture rate)
**When:** Every WebFetch call
**Content:** Up to 1500 chars from fetched page
**Auto-tags:** Detects tech (react, docker, postgresql, supabase, typescript)
**Examples:**
- API documentation
- GitHub READMEs
- Stack Overflow answers
- Medium articles
- Official docs

**Memory Type:** `docs`
**Tags:** `[tech-tags], documentation, webfetch, domain`
**Project:** Auto-detected from current directory

---

### 2. Bash Commands - Valuable Operations Only
**When:** Important commands detected
**Filters for:**
- ✅ `docker`, `docker-compose` - Deployment commands
- ✅ `npm install/run/build/start/test` - Build operations
- ✅ `pip install` - Python dependencies
- ✅ `git clone/pull/checkout` - Git workflows
- ✅ `curl POST/PUT/DELETE` - API testing
- ✅ `systemctl`, `service` - System services
- ✅ `chmod`, `chown`, `mkdir -p`, `ln -s` - Filesystem setup

**Memory Type:** `pattern`
**Tags:** `[detected-type], bash, command, project`
**Content:** Command + first 500 chars of output

**NOT captured:**
- ❌ Read-only commands (ls, cat, grep)
- ❌ Navigation (cd, pwd)
- ❌ Simple queries (echo, which)

---

### 3. Task/Agent Results - Key Insights
**When:** Agent tasks complete successfully
**Content:** First 800 chars of agent findings
**Memory Type:** `learning`
**Tags:** `[agent, agent-type, task, project]`

**Examples:**
- Code review findings
- Security audit results
- Architecture recommendations
- Test results

---

### 4. Read - Configuration Files Only
**When:** Reading important config files
**Triggers on:**
- ✅ `docker-compose.yml`
- ✅ `.env.example`
- ✅ `config.js`, `config.ts`, `config.json`
- ✅ `package.json`
- ✅ `tsconfig.json`

**Memory Type:** `pattern`
**Tags:** `[config, filename, project]`
**Content:** First 1000 chars of config

**NOT captured:**
- ❌ Source code files (.ts, .js, .py)
- ❌ Markdown files
- ❌ Generic text files

---

### 5. Session Summaries - Actual Work
**When:** Session ends (Stop event)
**Requires:** Significance score >= 5

**Score calculation:**
- +5 points: Git commits made
- +3 points: New files created
- +2 points: Files modified
- +3 points: Docker/deployment work
- +2 points: Build/dependency work
- +2 points: API testing

**Memory Type:** `context`
**Tags:** `[work-session, project, branch]`
**Content:**
- Commit summaries
- File change counts
- Work type detected
- Changed files list

**NOT captured:**
- ❌ Sessions with no significant work
- ❌ Browsing/reading only sessions
- ❌ Test/temp directories

---

## 📊 Expected Capture Rates

**High Volume:**
- WebFetch: 100% of calls
- Important configs: ~50% of reads

**Medium Volume:**
- Bash commands: ~20% of commands (filtered)
- Session summaries: ~30% of sessions (only with commits/changes)

**Low Volume:**
- Agent results: 100% of agent tasks (but infrequent)

---

## 🎨 Memory Types & Usage

| Type | What It Stores | When to Use Manual Save |
|------|----------------|------------------------|
| `docs` | Documentation, guides, examples | Never (auto-capture covers it) |
| `pattern` | Commands, configs, code patterns | Complex workflows, multi-step processes |
| `learning` | Agent insights, discoveries | Key architectural insights |
| `error` | Failed commands with solutions | When you solve a tricky bug |
| `decision` | Architectural choices | Technology/design decisions |
| `context` | Project info, work sessions | Project overview, setup notes |

---

## 🔍 Manual Memory Saves (Use MCP Tools)

**When auto-capture isn't enough:**

```typescript
// Store architectural decision
store_memory({
  type: "decision",
  content: "Using PostgreSQL for Compta instead of MongoDB",
  decision: "PostgreSQL",
  rationale: "Need ACID transactions, complex joins, RLS for multi-tenancy",
  alternatives: ["MongoDB", "MySQL"],
  tags: ["architecture", "database", "compta"],
  project: "Enduro"
})

// Store error + solution
store_memory({
  type: "error",
  content: "Docker container networking issue - containers can't communicate",
  error_message: "getaddrinfo EAI_AGAIN enduro-db",
  solution: "Added network: claude-mem-network to all services in docker-compose.yml",
  prevention: "Always use explicit networks in docker-compose",
  tags: ["docker", "networking", "solution"],
  project: "Enduro"
})

// Store important pattern
store_memory({
  type: "pattern",
  content: "Supabase RLS pattern for multi-tenant: (auth.uid() = user_id) OR (partner_id IN (SELECT partner_id FROM partnerships WHERE user_id = auth.uid()))",
  tags: ["supabase", "rls", "security", "multi-tenant"],
  project: "Compta"
})
```

---

## 🚫 What Will NEVER Be Captured

- Sensitive data (.env files, secrets, credentials)
- Source code content (use git for that)
- Read-only browsing (ls, cat without action)
- Test directories (tmp, temp, test, scratch)
- The .claude directory itself

---

## ✅ Best Practices

1. **Let auto-capture work** - It handles 80% of valuable info
2. **Manually save key decisions** - Architecture, tech choices, tradeoffs
3. **Search before working** - `search_memory("docker networking")`
4. **Tag consistently** - Use project names, tech stack names
5. **Review weekly** - Check `/memories` dashboard, archive old stuff

---

## 📈 Monitoring Memory Health

**Dashboard:** http://localhost:5173 (when frontend running)

**Quick stats:**
```bash
curl -s http://localhost:8100/stats | jq
```

**Search test:**
```bash
curl -s http://localhost:8100/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "docker deployment", "limit": 5}' | jq
```

**Recent memories:**
```bash
curl -s http://localhost:8100/memories | jq '[.[] | {type, content: .content[0:100], tags}] | .[0:5]'
```

---

**You now have a comprehensive memory system that captures:**
- ✅ All documentation you fetch
- ✅ Important commands you run
- ✅ Config files you review
- ✅ Work sessions with real progress
- ✅ Agent insights and findings

**But still filters out:**
- ❌ Noise and low-value data
- ❌ Sensitive information
- ❌ Duplicate/repetitive content
