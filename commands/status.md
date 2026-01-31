# Project Status Dashboard

Show current project status and agent activity

---

## Instructions

Display a comprehensive project status overview by gathering information from multiple sources.

### 1. Check PROJECT_CONTEXT.md

```bash
# Read PROJECT_CONTEXT.md if it exists
if [ -f "./PROJECT_CONTEXT.md" ]; then
  Read: ./PROJECT_CONTEXT.md
else
  echo "⚠️  No PROJECT_CONTEXT.md found in current directory"
fi
```

Extract from PROJECT_CONTEXT.md:
- Current Sprint/Feature name
- Start date
- Success criteria and progress
- Active blockers
- Recent agent activity (last 5 entries)

### 2. Run Agent Usage Dashboard

```bash
# Get agent usage statistics
bash ~/.claude/scripts/agent-usage-dashboard.sh 2>/dev/null || echo "Agent dashboard not available"
```

### 3. Check Git Status

```bash
# Get git repository status
git status --short 2>/dev/null || echo "Not a git repository"
git branch --show-current 2>/dev/null || echo "No branch info"
```

### 4. Check Validation Tools

```bash
# Check which validation tools are available
bash ~/.claude/scripts/check-tools.sh 2>/dev/null || echo "Tool check unavailable"
```

---

## Output Format

Present the information in a clean, organized dashboard:

```
📊 PROJECT STATUS DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Current Sprint: [Feature Name or "No active sprint"]
📅 Started: [Date or "N/A"]

✅ Success Criteria Progress: [X/Y completed]
   [List criteria with checkboxes]

🚨 Active Blockers: [Count]
   [List blockers if any, or "None"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 Recent Agent Activity:
   [Timestamp] - agent-name
   └─ [Brief description of what was completed]

   [Repeat for last 5 activities]

   [If no activity: "No agent activity recorded"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Git Status:
   Branch: [branch-name]
   Modified: [count] files
   Untracked: [count] files
   [If not git repo: "Not a git repository"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Validation Tools Available:
   ✅ git
   [✅/❌] ruff
   [✅/❌] mypy
   [✅/❌] pytest
   [✅/❌] tsc
   [✅/❌] eslint

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Quick Actions:
   • Continue work: Review blockers and recent activity
   • Start new feature: Use Claude Code's Plan mode
   • Quick task: /quick-agent [agent]: [task]
   • Run validation: /validate
   • Clean context: /context-clean
```

---

## Error Handling

- If PROJECT_CONTEXT.md doesn't exist: Show minimal status (git + tools only)
- If scripts are missing: Skip those sections gracefully
- If not in project directory: Show warning and basic environment info

---

## Notes

This command provides a quick overview without making changes. Use it to:
- Check project health before starting work
- See what agents recently completed
- Identify blockers that need attention
- Verify validation tools are available
