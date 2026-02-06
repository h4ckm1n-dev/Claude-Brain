# Agent Catalog Browser

Browse and search the 43 specialized agents

**Usage:** `/list-agents [search-term or category]`

**Input:** $ARGUMENTS (optional)

---

## Instructions

Display a searchable, filterable catalog of all available agents with their capabilities, tools, and use cases.

### 1. Parse Input

Determine display mode from $ARGUMENTS:
- **Empty** → Show all agents by category
- **Category name** → Show agents in that category
- **Search term** → Search agent names and descriptions
- **"tools:[tool]"** → Filter by tool availability
- **"unused"** → Show agents never used (if metrics available)

### 2. Load Agent Information

```bash
# Read all agent files
agent_dir="$HOME/.claude/agents"

if [ ! -d "$agent_dir" ]; then
  echo "❌ Agent directory not found: $agent_dir"
  exit 1
fi

# Get agent count
agent_count=$(ls -1 "$agent_dir"/*.md 2>/dev/null | wc -l)
```

### 3. Display Agent Catalog

#### Mode A: Show All (Categorized)

```
🤖 AGENT CATALOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Agents: 43 specialized agents

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 FULL-STACK DEVELOPMENT (4 agents)

code-architect
   📝 System design, architecture planning, folder structure
   🔧 All tools
   💡 Use for: New features, architecture decisions, system design
   📄 File: ~/.claude/agents/code-architect.md

backend-architect
   📝 Server-side logic, APIs, databases
   🔧 Write, Read, MultiEdit, Bash, Grep
   💡 Use for: API implementation, business logic, integrations
   📄 File: ~/.claude/agents/backend-architect.md

frontend-developer
   📝 UI components, state management, React/Vue/Angular
   🔧 Write, Read, MultiEdit, Bash, Grep, Glob
   💡 Use for: UI development, components, responsive design
   📄 File: ~/.claude/agents/frontend-developer.md

api-designer
   📝 REST/GraphQL API design, OpenAPI specs
   🔧 Write, Read, MultiEdit, Bash, Grep
   💡 Use for: API specifications, endpoint design, documentation
   📄 File: ~/.claude/agents/api-designer.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 LANGUAGE & PLATFORM SPECIALISTS (6 agents)

python-expert
   📝 Advanced Python, async/await, type safety, optimization
   🔧 Bash, Read, Write, Grep, MultiEdit
   💡 Use for: Python refactoring, async code, type annotations
   📄 File: ~/.claude/agents/python-expert.md

typescript-expert
   📝 Advanced TypeScript, type system, strict types
   🔧 Bash, Read, Write, Grep, MultiEdit
   💡 Use for: Type safety, generics, production TypeScript
   📄 File: ~/.claude/agents/typescript-expert.md

mobile-app-developer
   📝 Native iOS (Swift) and Android (Kotlin)
   🔧 Write, Read, Bash
   💡 Use for: Mobile apps, platform-specific features
   📄 File: ~/.claude/agents/mobile-app-developer.md

desktop-app-developer
   📝 Cross-platform desktop with Electron, Tauri
   🔧 Write, Read, Bash
   💡 Use for: Desktop applications, system integration
   📄 File: ~/.claude/agents/desktop-app-developer.md

game-developer
   📝 Game mechanics, physics, graphics
   🔧 Write, Read, Bash
   💡 Use for: Games, game engines, physics simulation
   📄 File: ~/.claude/agents/game-developer.md

blockchain-developer
   📝 Web3, smart contracts, DeFi, NFTs
   🔧 Write, Read, Bash, Grep
   💡 Use for: Blockchain, Solidity, Web3 integration
   📄 File: ~/.claude/agents/blockchain-developer.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Continue with all categories...]

🔬 DEVOPS & INFRASTRUCTURE (3 agents)
🧪 TESTING & QUALITY (4 agents)
🤖 AI & MACHINE LEARNING (2 agents)
📊 DATA & ANALYTICS (4 agents)
⚡ PERFORMANCE & SECURITY (3 agents)
🎨 DESIGN & UX (4 agents)
📝 CONTENT & MARKETING (4 agents)
🔧 CODE MANAGEMENT (3 agents)
💼 BUSINESS INTELLIGENCE (4 agents)
📚 DOCUMENTATION & SUPPORT (2 agents)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 USAGE:
   View category: /list-agents [category]
   Search agents: /list-agents [search-term]
   Filter by tool: /list-agents tools:Bash
   Find for task: /agent-select [task description]
   Launch agent: /quick-agent [agent-name]: [task]
```

#### Mode B: Show Category

```
🤖 [CATEGORY NAME] AGENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[For each agent in category:]

[agent-name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description:
   [Full description from agent file]

When to Use:
   • [Use case 1]
   • [Use case 2]
   • [Use case 3]

Key Capabilities:
   • [Capability 1]
   • [Capability 2]
   • [Capability 3]

Tools Available:
   [List of tools: Write, Read, MultiEdit, Bash, etc.]

Common Agent Chains:
   → [agent-1] → [agent-2] → [this-agent]
   → [this-agent] → [agent-3]

Example Tasks:
   • [Example 1]
   • [Example 2]

Usage:
   Quick: /quick-agent [agent-name]: [your task]
   Multi-agent: Use Claude Code Plan mode for complex tasks

File: ~/.claude/agents/[agent-name].md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Next agent in category...]
```

#### Mode C: Search Results

```
🔍 SEARCH RESULTS for "[search-term]"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found [X] agents matching "[search-term]":

1. [agent-name] ([category])
   📝 [One-line description]
   ✨ Match: [Where term was found: name/description/capabilities]
   💡 Use for: [Primary use case]
   🚀 Quick: /quick-agent [agent-name]: [suggested task]

2. [agent-name] ([category])
   [Same format...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View agent details: /list-agents [agent-name]
Get recommendations: /agent-select [task description]

[If no results:]
❌ No agents found matching "[search-term]"

💡 Suggestions:
   • Try broader search terms
   • Browse by category: /list-agents [category]
   • See all agents: /list-agents
   • Get recommendations: /agent-select [what you want to do]
```

#### Mode D: Single Agent Details

```
🤖 [AGENT-NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Category: [Category Name]
File: ~/.claude/agents/[agent-name].md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 DESCRIPTION

[Full description from agent file]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 WHEN TO USE

Use this agent when:
   • [Scenario 1]
   • [Scenario 2]
   • [Scenario 3]

Do NOT use for:
   • [Anti-pattern 1]
   • [Anti-pattern 2]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 TOOLS & CAPABILITIES

Available Tools:
   [List: Write, Read, Edit, MultiEdit, Bash, Grep, Glob, etc.]

Specializations:
   • [Specialization 1]
   • [Specialization 2]
   • [Specialization 3]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 COMMON AGENT CHAINS

Typical Sequences:
   1. [preceding-agent] → THIS-AGENT → [following-agent]
      Use case: [When this sequence is used]

   2. THIS-AGENT → [following-agent]
      Use case: [When this sequence is used]

Parallel Execution:
   • THIS-AGENT + [other-agent] (can run simultaneously)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 EXAMPLE TASKS

Task 1: [Example task description]
   Command: /quick-agent [agent-name]: [specific task]

Task 2: [Example task description]
   Command: /quick-agent [agent-name]: [specific task]

Task 3: [Complex task requiring multiple agents]
   Approach: Use Claude Code's Plan mode for orchestration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 USAGE STATISTICS [If available]

Total Invocations: [count]
Success Rate: [percentage]%
Average Duration: [time]
Last Used: [date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 QUICK ACTIONS

Launch for quick task:
   /quick-agent [agent-name]: [describe your task]

Multi-agent workflow:
   Use Claude Code Plan mode for orchestration

Find similar agents:
   /list-agents [category]

Get task recommendations:
   /agent-select [what you want to do]
```

---

## Search Examples

**By category:**
```
/list-agents backend
/list-agents testing
/list-agents frontend
```

**By keyword:**
```
/list-agents API
/list-agents security
/list-agents optimization
```

**By tool:**
```
/list-agents tools:Bash
/list-agents tools:WebSearch
```

**Specific agent:**
```
/list-agents backend-architect
/list-agents debugger
```

**Unused agents:**
```
/list-agents unused
# Shows agents you haven't used yet
```

---

## Categories Reference

```yaml
Full-Stack Development:
  - code-architect
  - backend-architect
  - frontend-developer
  - api-designer

Language & Platform:
  - python-expert
  - typescript-expert
  - mobile-app-developer
  - desktop-app-developer
  - game-developer
  - blockchain-developer

DevOps & Infrastructure:
  - deployment-engineer
  - infrastructure-architect
  - observability-engineer

Testing & Quality:
  - test-engineer
  - api-tester
  - code-reviewer
  - debugger

AI & Machine Learning:
  - ai-engineer
  - ai-prompt-engineer

Data & Analytics:
  - data-scientist
  - database-optimizer
  - analytics-engineer
  - visualization-dashboard-builder

Performance & Security:
  - performance-profiler
  - security-practice-reviewer
  - math-checker

Design & UX:
  - ui-designer
  - ux-researcher
  - mobile-ux-optimizer
  - accessibility-specialist

Content & Marketing:
  - content-marketing-specialist
  - visual-storyteller
  - technical-writer
  - seo-specialist

Code Management:
  - refactoring-specialist
  - migration-specialist
  - localization-specialist

Business Intelligence:
  - finance-tracker
  - growth-hacker
  - trend-researcher
  - trading-bot-strategist

Documentation & Support:
  - codebase-documenter
  - context7-docs-fetcher
```

---

## Advanced Filters

**Combine filters:**
```bash
# Backend agents with Bash tool
/list-agents backend tools:Bash

# Testing agents, unused
/list-agents testing unused
```

---

## Integration Tips

**Discovery workflow:**
```
1. Browse categories: /list-agents
2. Search by domain: /list-agents [keyword]
3. View agent details: /list-agents [agent-name]
4. Launch agent: /quick-agent [agent-name]: [task]
```

**Before launching agent:**
```
1. Check agent capabilities: /list-agents [agent-name]
2. Verify tools available
3. See example tasks
4. Launch with appropriate context
```

---

## Notes

- All agents stored in ~/.claude/agents/
- Each agent has markdown file with metadata
- Agents are categorized by domain/specialty
- Search is case-insensitive
- Can search name, description, capabilities
- Statistics shown if agent-analytics data available
- Use /agent-select for task-based recommendations
