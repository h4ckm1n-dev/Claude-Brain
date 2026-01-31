# Agent Analytics Dashboard

View agent usage statistics and performance metrics

**Usage:** `/agent-metrics [period]`

**Input:** $ARGUMENTS (optional: 7d, 30d, 90d, all)

---

## Instructions

Display comprehensive analytics about agent usage, success rates, and performance patterns.

### 1. Determine Time Period

Parse $ARGUMENTS for time period:
- `7d` or `week` → Last 7 days
- `30d` or `month` → Last 30 days (default)
- `90d` or `quarter` → Last 90 days
- `all` or `lifetime` → All time

Default to 30 days if not specified.

### 2. Run Analytics Script

```bash
# Run the enhanced analytics script
bash ~/.claude/scripts/agent-analytics-enhanced.sh "$PERIOD" 2>/dev/null

# If not available, fall back to basic script
if [ $? -ne 0 ]; then
  bash ~/.claude/scripts/agent-analytics.sh "$PERIOD" 2>/dev/null
fi

# If both unavailable, perform manual analysis
if [ $? -ne 0 ]; then
  echo "⚠️  Analytics scripts unavailable, performing manual analysis"
fi
```

### 3. Parse PROJECT_CONTEXT.md

If scripts unavailable, manually parse:

```bash
# Find all PROJECT_CONTEXT.md files
find . -name "PROJECT_CONTEXT.md" 2>/dev/null

# Extract agent activity entries
grep -E "^\*\*.*\*\* - \`.*\`" PROJECT_CONTEXT.md 2>/dev/null

# Count by agent name
# Track success/failure markers
# Calculate time periods
```

### 4. Generate Analytics Report

Present comprehensive analytics:

```
📈 AGENT ANALYTICS DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Period: [Last 30 days / Last 7 days / etc.]
Data Source: [PROJECT_CONTEXT.md + logs]
Last Updated: [timestamp]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 USAGE STATISTICS

Top 10 Most Used Agents:
   1. backend-architect        23 runs  (92% success)  ⭐⭐⭐⭐⭐
   2. frontend-developer       18 runs  (89% success)  ⭐⭐⭐⭐⭐
   3. test-engineer            15 runs  (100% success) ⭐⭐⭐⭐⭐
   4. code-reviewer            12 runs  (95% success)  ⭐⭐⭐⭐⭐
   5. debugger                 10 runs  (80% success)  ⭐⭐⭐⭐
   6. api-designer              8 runs  (88% success)  ⭐⭐⭐⭐
   7. security-practice-reviewer 7 runs (100% success) ⭐⭐⭐⭐⭐
   8. database-optimizer        6 runs  (83% success)  ⭐⭐⭐⭐
   9. code-architect            5 runs  (100% success) ⭐⭐⭐⭐⭐
  10. refactoring-specialist    4 runs  (75% success)  ⭐⭐⭐⭐

Total Agent Invocations: 108
Unique Agents Used: 10 of 43 available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 SUCCESS RATES

Highest Success Rate (≥5 runs):
   • test-engineer              100% (15/15)
   • code-architect             100% (5/5)
   • security-practice-reviewer 100% (7/7)
   • code-reviewer               95% (12/12)

Needs Improvement (<80% success):
   • refactoring-specialist      75% (3/4)
   • debugger                    80% (8/10)

   💡 Low success may indicate:
      - Insufficient context provided
      - Complex tasks beyond agent scope
      - Tool/dependency issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 AGENT CHAINS

Most Common Agent Sequences:

1. api-designer → backend-architect → test-engineer
   Used: 8 times
   Success: 100%
   Use Case: API feature development

2. code-architect → database-optimizer → backend-architect
   Used: 5 times
   Success: 80%
   Use Case: Full-stack features with DB

3. frontend-developer → test-engineer
   Used: 6 times
   Success: 100%
   Use Case: UI component development

4. debugger → test-engineer
   Used: 4 times
   Success: 75%
   Use Case: Bug fixing with test coverage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱️  PERFORMANCE METRICS

Average Execution Time by Agent:
   • frontend-developer         ~8 min
   • backend-architect         ~12 min
   • test-engineer             ~10 min
   • code-reviewer              ~5 min
   • debugger                  ~15 min

Fastest Agents (Efficiency):
   1. code-reviewer             ~5 min
   2. api-designer              ~6 min
   3. frontend-developer        ~8 min

Slowest Agents (Complexity):
   1. debugger                 ~15 min (complex investigation)
   2. backend-architect        ~12 min (implementation)
   3. database-optimizer       ~11 min (schema design)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 USAGE TRENDS

Weekly Activity:
   Week 1: ████████████████████ 45 invocations
   Week 2: ███████████████ 35 invocations
   Week 3: █████████████████ 38 invocations
   Week 4: ██████████████ 30 invocations

Peak Activity Days:
   • Monday:    28 invocations
   • Tuesday:   24 invocations
   • Wednesday: 22 invocations

Agent Category Distribution:
   Full-Stack:     35% ███████████████
   Testing:        22% ███████████
   Code Quality:   18% █████████
   Performance:    12% ██████
   Security:       10% █████
   Other:           3% ██

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 FAILURE ANALYSIS

Total Failures: 12 (11% of invocations)

Top Failure Reasons:
   1. Missing dependencies        5 failures
   2. Insufficient context        3 failures
   3. Tool unavailable            2 failures
   4. Validation loop failure     2 failures

Agents with Most Failures:
   • debugger                     3 failures
   • refactoring-specialist       2 failures
   • deployment-engineer          2 failures

💡 Recommendations:
   • Provide more context for debugger tasks
   • Check tool availability before refactoring
   • Improve deployment environment setup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 LEARNING INSIGHTS

Underutilized Agents (0-2 uses):
   • ai-engineer (0 uses)
   • blockchain-developer (0 uses)
   • mobile-app-developer (1 use)
   • game-developer (0 uses)
   • trading-bot-strategist (0 uses)

   💡 Consider if these agents could help with:
      - Adding AI features
      - Mobile app development
      - Specialized domains

Optimal Agent Combinations:
   ✅ api-designer before backend-architect (100% success)
   ✅ test-engineer after any implementation agent (98% success)
   ✅ code-reviewer as final step (100% success)
   ⚠️  debugger alone has lower success (80%)
      → Better with test-engineer follow-up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 COST EFFICIENCY (Tokens)

Average Token Usage by Agent:
   • backend-architect     ~45K tokens
   • frontend-developer    ~38K tokens
   • test-engineer         ~32K tokens
   • code-reviewer         ~18K tokens

Total Token Usage: ~4.2M tokens this period
Average per Invocation: ~39K tokens

Most Efficient Agents (tokens/success):
   1. code-reviewer        ~18K tokens
   2. api-designer         ~22K tokens
   3. test-engineer        ~32K tokens

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 RECOMMENDATIONS

Based on your usage patterns:

✅ Keep Doing:
   • Using test-engineer after implementations (100% success)
   • api-designer → backend-architect chain works great
   • code-reviewer as quality gate is effective

🔧 Improvements:
   • Add more context to debugger tasks (80% → target 90%+)
   • Consider refactoring-specialist earlier in dev cycle
   • Pre-check dependencies for deployment-engineer

💡 Explore:
   • Try performance-profiler for optimization tasks
   • Use security-practice-reviewer proactively
   • Consider ai-engineer for intelligent features

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 DETAILED BREAKDOWN

View detailed agent info:
   /list-agents [category]

Get agent suggestions for task:
   /agent-select [task description]

View project status:
   /status
```

---

## Data Sources

Metrics collected from:
1. **PROJECT_CONTEXT.md** - Agent activity logs
2. **Agent logs** (if available) - Execution details
3. **Git history** - Commit correlation
4. **Validation results** - Success/failure tracking

---

## Metric Definitions

**Success Rate:**
- Percentage of agent invocations that completed without errors
- Validation loops passed
- No retry required

**Execution Time:**
- Time from agent launch to completion
- Includes all retries and validation

**Agent Chain:**
- Sequence of agents used in order
- Extracted from PROJECT_CONTEXT.md workflow

**Failure:**
- Agent reported error/blocker
- Validation loops failed
- Required manual intervention

---

## Examples

**Default (last 30 days):**
```
/agent-metrics
/agent-metrics 30d
```

**Weekly report:**
```
/agent-metrics 7d
/agent-metrics week
```

**Quarterly analysis:**
```
/agent-metrics 90d
/agent-metrics quarter
```

**All-time stats:**
```
/agent-metrics all
/agent-metrics lifetime
```

---

## Export Options

**Export to CSV:**
```bash
# Generate CSV report
bash ~/.claude/scripts/agent-analytics-enhanced.sh 30d --format=csv > agent-metrics.csv
```

**Export to JSON:**
```bash
# Generate JSON report
bash ~/.claude/scripts/agent-analytics-enhanced.sh 30d --format=json > agent-metrics.json
```

---

## Notes

- Metrics help optimize agent usage and task quality
- Success rates indicate context completeness
- Agent chains reveal common workflows
- Failure analysis guides improvement areas
- Use insights to improve future task descriptions
- Underutilized agents may indicate untapped capabilities
