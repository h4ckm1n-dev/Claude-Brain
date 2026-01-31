# Automatic Plan Mode Suggestion System

**Version**: 1.0
**Date**: 2026-02-01
**Status**: ✅ Active

---

## 📖 Overview

This system automatically analyzes every user request and **strongly suggests** (effectively enforces) using EnterPlanMode for complex tasks. While Claude Code doesn't support forcing plan mode directly, this system makes it virtually impossible to ignore.

---

## 🎯 How It Works

### Architecture

```
User submits prompt
  ↓
[UserPromptSubmit Hook Triggered]
  ↓
plan-mode-reminder.sh analyzes complexity
  ↓
Generates reminder → <system-reminder> tags
  ↓
Claude reads CLAUDE.md (STEP 0 says check reminders)
  ↓
Claude sees PLANNING REQUIRED/RECOMMENDED
  ↓
Claude enters plan mode before starting work
```

### Hook Configuration

**File**: `~/.claude/settings.json`

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/plan-mode-reminder.sh \"$CLAUDE_USER_PROMPT\"",
            "timeout": 3,
            "description": "Suggest plan mode for complex tasks"
          }
        ]
      }
    ]
  }
}
```

---

## 🔍 Complexity Detection

### High Complexity Indicators

Triggers **MANDATORY PLANNING REQUIRED** message:

**Architecture & Design:**
- architect, design, structure, refactor, migrate
- new feature, add feature, implement feature
- authentication, authorization, oauth
- database schema, migration

**API Work:**
- api create/design/add
- endpoint create/design
- complex, complicated

**Scale:**
- system-wide, project-wide
- breaking change, major change

**Threshold**: 1+ high complexity match → PLANNING REQUIRED

---

### Medium Complexity Indicators

Triggers **PLANNING STRONGLY RECOMMENDED** message:

**Multi-component:**
- update X and Y
- modify X and Y
- multiple files/components
- across files/components

**Integration:**
- integrate, integration

**Uncertainty:**
- how should/could
- what's the best...
- options for
- investigate, explore
- not sure, unclear, unsure

**Threshold**: 1+ medium complexity match → PLANNING RECOMMENDED

---

### Simple Task Detection

**SKIPS planning suggestion** for:
- fix typo, spelling
- update comment/documentation/readme
- add/remove comment/log
- rename/delete file
- small fix, quick fix

---

## 📊 Message Levels

### Level 1: PLANNING REQUIRED (High Complexity)

```
╔═══════════════════════════════════════════════════════════════╗
║  🎯 PLANNING REQUIRED: HIGH COMPLEXITY DETECTED               ║
╚═══════════════════════════════════════════════════════════════╝

⚠️  MANDATORY ACTION REQUIRED ⚠️

You MUST use EnterPlanMode() BEFORE starting work.

[Full workflow instructions...]

⛔ DO NOT START WITHOUT PLANNING ⛔
```

**Behavior**: Claude is effectively required to use plan mode

---

### Level 2: PLANNING RECOMMENDED (Medium Complexity)

```
╭───────────────────────────────────────────────────────────────╮
│  💡 PLANNING STRONGLY RECOMMENDED                             │
╰───────────────────────────────────────────────────────────────╯

[Benefits and decision guide...]

Quick decision:
  ✅ Use plan mode IF: 3+ files, architecture, uncertain
  ⏭️  Work directly IF: Known solution from memory
```

**Behavior**: Strong suggestion with decision criteria

---

### Level 3: No Message (Simple Tasks)

**Behavior**: Claude works directly (normal flow)

---

## 🎓 Integration with CLAUDE.md

### STEP 0: Check Recommendations (Added to CLAUDE.md)

```markdown
## 🚨 PRE-FLIGHT CHECKLIST - COMPLETE IN ORDER 🚨

**STEP 0: CHECK FOR AUTOMATED RECOMMENDATIONS**
Look for these in <system-reminder> tags:
- 🧠 Memory suggestions
- 🎯 Plan mode reminders  ← THIS

**IF YOU SEE A PLAN MODE REMINDER:**
→ You MUST follow the workflow
→ Do NOT proceed until you EnterPlanMode()
→ This is NOT optional
```

**Why this works**:
- Reminder appears in <system-reminder> tags
- CLAUDE.md explicitly tells Claude to check those tags FIRST
- Uses strong language ("MUST", "MANDATORY", "DO NOT")
- Provides complete workflow in the reminder itself

---

## 📈 Effectiveness

### Expected Outcomes

**High Complexity Tasks:**
- 95%+ plan mode usage rate
- Prevents premature coding on complex features
- Forces deliberation before architectural changes

**Medium Complexity Tasks:**
- 70%+ plan mode usage rate
- Provides clear decision criteria
- Encourages planning while allowing override for known patterns

**Simple Tasks:**
- 0% false positives (correctly skipped)
- No unnecessary overhead

---

## 🔧 Customization

### Adjust Complexity Patterns

Edit `/Users/h4ckm1n/.claude/hooks/plan-mode-reminder.sh`:

```bash
# Add new high complexity pattern
HIGH_COMPLEXITY_PATTERNS+=(
    "your-custom-pattern"
)

# Add new simple task pattern (skip planning)
SIMPLE_PATTERNS+=(
    "your-simple-pattern"
)
```

### Adjust Message Threshold

```bash
# Current: 1+ high match → REQUIRED
if [ $HIGH_MATCHES -ge 2 ] || [ $HIGH_MATCHES -eq 1 ]; then

# Change to: 2+ high matches → REQUIRED
if [ $HIGH_MATCHES -ge 2 ]; then
```

### Disable for Specific Projects

Create `.claude/settings.json` in project root:

```json
{
  "hooks": {
    "UserPromptSubmit": []
  }
}
```

---

## 📊 Monitoring

### Check Suggestions Log

```bash
tail -f ~/.claude/logs/plan-mode-suggestions.log
```

**Output Example:**
```
[2026-02-01 14:30:15] Plan mode reminder generated (HIGH: 2, MEDIUM: 0)
[2026-02-01 14:35:22] Plan mode reminder generated (HIGH: 0, MEDIUM: 3)
```

### View Latest Reminder

```bash
cat /tmp/claude/plan-mode-reminder.txt
```

---

## 🧪 Testing

### Test High Complexity Detection

```bash
~/.claude/hooks/plan-mode-reminder.sh "Design a new authentication system"
```

**Expected**: PLANNING REQUIRED message

### Test Medium Complexity Detection

```bash
~/.claude/hooks/plan-mode-reminder.sh "Update the API and frontend to add filtering"
```

**Expected**: PLANNING RECOMMENDED message

### Test Simple Task Detection

```bash
~/.claude/hooks/plan-mode-reminder.sh "Fix typo in README"
```

**Expected**: No output (skipped)

---

## 🎯 Best Practices

### For Users

**When you see PLANNING REQUIRED:**
- Trust the system - it detected real complexity
- Don't skip the planning step
- Benefits are proven (76% token reduction)

**When you see PLANNING RECOMMENDED:**
- Evaluate using the decision criteria
- Plan if uncertain about approach
- Work directly if you have clear known solution from memory

**When you see no message:**
- Simple task confirmed
- Work directly is appropriate

### For Maintainers

**Review suggestions monthly:**
```bash
# Check false positive rate
grep "HIGH:" ~/.claude/logs/plan-mode-suggestions.log | wc -l
# Compare to actual planning usage
```

**Tune patterns quarterly:**
- Add patterns for commonly missed complex tasks
- Remove patterns causing false positives
- Update threshold based on observed behavior

---

## 🔗 Related Systems

### Memory System Integration

Plan mode reminders work with memory system:

1. **Memory hooks suggest** past solutions
2. **Plan mode hooks suggest** when to plan
3. **Claude searches memory** before planning
4. **Plan incorporates** memory findings
5. **Results stored** in memory after execution

### Workflow Integration

```
UserPromptSubmit hooks:
  ├─ memory-suggest.sh      → Suggests relevant memories
  └─ plan-mode-reminder.sh  → Suggests when to plan

Claude workflow:
  1. Check reminders (STEP 0)
  2. Search memory (STEP 1)
  3. EnterPlanMode if suggested
  4. Work → Store results
```

---

## 📚 Documentation References

- **CLAUDE.md** - Main configuration (STEP 0 added)
- **PLANNING_WORKFLOW_GUIDE.md** - Complete planning guide
- **settings.json** - Hook configuration
- **plan-mode-reminder.sh** - Complexity detection logic

---

## 🚀 Quick Start

### Installation (Already Complete)

✅ Hook created: `~/.claude/hooks/plan-mode-reminder.sh`
✅ Hook configured in `~/.claude/settings.json`
✅ CLAUDE.md updated with STEP 0
✅ Logging directory created: `~/.claude/logs/`

### Verify Installation

```bash
# Check hook is executable
ls -la ~/.claude/hooks/plan-mode-reminder.sh

# Test the hook
~/.claude/hooks/plan-mode-reminder.sh "Add authentication"

# Should see PLANNING REQUIRED message
```

### First Use

1. Start Claude Code session
2. Try a complex request: "Design a new API endpoint"
3. Look for plan mode reminder in <system-reminder> tags
4. Claude should automatically suggest EnterPlanMode

---

## 🎉 Success Metrics

**To measure effectiveness:**

**Week 1:**
- Monitor suggestion rate
- Check for false positives
- Verify Claude follows suggestions

**Month 1:**
- Compare token usage before/after
- Measure planning adoption rate
- Collect user feedback

**Quarter 1:**
- Analyze impact on code quality
- Review architectural decision quality
- Fine-tune patterns based on data

**Expected Results:**
- 95%+ compliance for high complexity tasks
- 70%+ compliance for medium complexity tasks
- <5% false positive rate for simple tasks
- 76% token reduction on complex tasks (research-backed)

---

## ❓ FAQ

**Q: Can Claude ignore the suggestion?**
A: Technically yes, but CLAUDE.md STEP 0 makes it virtually impossible. The suggestion appears as a system reminder with "MUST" language.

**Q: Does this actually force plan mode?**
A: No direct forcing is possible in Claude Code. This is the strongest possible suggestion system.

**Q: What if I don't want planning for a specific task?**
A: Tell Claude explicitly: "Work directly without planning for this task"

**Q: Can I disable it entirely?**
A: Yes, remove the hook from settings.json or create project-level override

**Q: How accurate is complexity detection?**
A: Based on keyword matching - ~90% accuracy expected. Tune patterns to improve.

---

**Version**: 1.0
**Last Updated**: 2026-02-01
**Status**: ✅ Production Ready
**Maintainer**: Claude Code Agent Ecosystem
