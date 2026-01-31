# Quick Agent Invocation

Launch a specialized agent for a quick, focused task

**Usage:** `/quick-agent agent-name: task description`

**Input:** $ARGUMENTS

---

## Instructions

This command allows rapid agent invocation for simple, focused tasks.

### 1. Parse Input

Expected format: `agent-name: task description`

Examples:
- `backend-architect: add error logging to user authentication`
- `frontend-developer: fix button alignment on mobile`
- `test-engineer: add unit tests for calculateTotal function`
- `code-reviewer: review src/api/users.py for security issues`

Extract:
- **agent_name**: Text before the colon
- **task_description**: Text after the colon

### 2. Validate Agent Exists

```bash
# Check if agent definition exists
agent_file="$HOME/.claude/agents/${agent_name}.md"

if [ ! -f "$agent_file" ]; then
  echo "❌ Agent '${agent_name}' not found"
  echo ""
  echo "💡 Use /list-agents to see available agents"
  echo "💡 Or /agent-select to find the right agent"
  exit 1
fi
```

### 3. Launch Agent with Task Tool

Use the Task tool to launch the agent:

```yaml
subagent_type: [agent_name]
description: [First 3-5 words of task]
prompt: |
  You have been invoked for a quick, focused task.

  **TASK**: [task_description]

  **CONTEXT**:
  - Working directory: [current directory]
  - This is a focused, single-purpose task
  - Complete the task efficiently
  - Follow existing code patterns in the codebase

  **INSTRUCTIONS**:
  1. Read relevant files needed for this task
  2. Implement the requested changes
  3. Validate your changes (run tests, linters, etc. if applicable)
  4. Report what you completed

  **VALIDATION** (if applicable):
  - Run relevant linters/formatters
  - Run relevant tests
  - Ensure no errors introduced

  **COMPLETION**:
  When done, provide a brief summary:
  - What was changed
  - Files modified
  - Any validation results
  - Any issues or considerations

  Note: This is a quick task, so skip PROJECT_CONTEXT.md updates and artifact documentation.
```

### 4. Report Completion

After the agent completes, summarize the results:

```
✅ Quick Task Completed: [agent_name]

📋 Task: [task_description]

📁 Files Modified:
   [List files from agent report]

✅ Validation:
   [Validation results if any]

💡 Notes:
   [Any important notes or considerations from agent]

---

💭 This was a quick task. For complex features, use Claude Code's Plan mode.
```

---

## When to Use Quick Agent vs Plan Mode

**Use /quick-agent for:**
- ✅ Single file modifications
- ✅ Simple additions (< 50 lines)
- ✅ Bug fixes with clear scope
- ✅ Code reviews of specific files
- ✅ Documentation updates
- ✅ Quick refactoring of single functions
- ✅ Adding simple tests

**Use Claude Code's Plan mode for:**
- ❌ Multi-file features
- ❌ Architecture changes
- ❌ Database migrations
- ❌ API design and implementation
- ❌ Integration with external services
- ❌ Complex state management
- ❌ Anything requiring multiple agents

---

## Error Handling

If user provides incorrect format:
```
❌ Invalid format. Expected: agent-name: task description

Examples:
  /quick-agent backend-architect: add logging to auth service
  /quick-agent test-engineer: write tests for User model
  /quick-agent code-reviewer: review src/api/handlers.py

Available agents: /list-agents
Find right agent: /agent-select [task description]
```

If agent name has typos, suggest closest match:
```
❌ Agent 'backend-arch' not found

💡 Did you mean: backend-architect?

Available backend agents:
  - backend-architect
  - api-designer
  - database-optimizer
```

---

## Examples

**Example 1: Add logging**
```
/quick-agent backend-architect: add debug logging to the login endpoint
```

**Example 2: Fix UI bug**
```
/quick-agent frontend-developer: fix navbar overlap on mobile screens
```

**Example 3: Security review**
```
/quick-agent security-practice-reviewer: check authentication middleware for vulnerabilities
```

**Example 4: Quick test**
```
/quick-agent test-engineer: add edge case tests for email validator
```

---

## Notes

- Quick tasks skip PROJECT_CONTEXT.md coordination
- No artifact documentation required
- Agent works autonomously with minimal context
- Best for tasks that take < 15 minutes
- For tasks requiring coordination between agents, use Claude Code's Plan mode
