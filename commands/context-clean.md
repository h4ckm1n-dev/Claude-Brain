# Clean Project Context

Archive old context and clean up PROJECT_CONTEXT.md for better performance

**Usage:** `/context-clean`

---

## Instructions

Clean and archive PROJECT_CONTEXT.md to maintain optimal performance and organization.

### 1. Check PROJECT_CONTEXT.md Exists

```bash
if [ ! -f "./PROJECT_CONTEXT.md" ]; then
  echo "ℹ️  No PROJECT_CONTEXT.md found in current directory"
  echo ""
  echo "💡 PROJECT_CONTEXT.md is created automatically when you:"
  echo "   • Use agents for multi-step tasks"
  echo "   • Or create it manually: cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md"
  exit 0
fi
```

### 2. Analyze Current State

```bash
# Get file statistics
file_size=$(wc -c < PROJECT_CONTEXT.md)
line_count=$(wc -l < PROJECT_CONTEXT.md)
last_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" PROJECT_CONTEXT.md 2>/dev/null || stat -c "%y" PROJECT_CONTEXT.md 2>/dev/null)

# Check for active sprint
has_active_sprint=$(grep -c "Status.*In Progress" PROJECT_CONTEXT.md || echo "0")

# Count agent entries
agent_entries=$(grep -c "^\*\*.*\*\* - \`.*\`" PROJECT_CONTEXT.md || echo "0")

# Count blockers
blocker_count=$(grep -c "^\- \[.*\].*blocker" PROJECT_CONTEXT.md -i || echo "0")
```

Show current state:
```
📊 PROJECT_CONTEXT.md Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File Size: [X]KB ([Y] lines)
Last Modified: [date/time]
Agent Activity Entries: [count]
Active Sprint: [Yes/No]
Active Blockers: [count]

[If file is large:]
⚠️  File is getting large ([X]KB)
    Consider archiving old activity

[If no recent activity:]
ℹ️  Last modified [X] days ago
    May contain stale information
```

### 3. Ask User for Confirmation

```
This will:
   1. Archive current PROJECT_CONTEXT.md to PROJECT_ARCHIVE_[date].md
   2. Clean up completed sprints and old agent logs
   3. Preserve active sprint and blockers
   4. Reduce file size for better performance

Proceed with cleanup? (y/n)
```

### 4. Perform Archival (If User Confirms)

```bash
# Create archive with timestamp
archive_file="PROJECT_ARCHIVE_$(date +%Y%m%d_%H%M%S).md"

# Copy current content to archive
cp PROJECT_CONTEXT.md "$archive_file"

echo "✅ Archived to: $archive_file"
```

### 5. Run Cleanup Script

```bash
# Run the cleanup script
bash ~/.claude/scripts/cleanup-context.sh . 2>/dev/null

if [ $? -eq 0 ]; then
  echo "✅ Cleanup completed successfully"
else
  echo "⚠️  Cleanup script not available, performing manual cleanup"
  # Manual cleanup fallback
fi
```

### 6. Show Cleanup Results

```bash
# Get new file statistics
new_file_size=$(wc -c < PROJECT_CONTEXT.md)
new_line_count=$(wc -l < PROJECT_CONTEXT.md)

# Calculate reductions
size_reduction=$((file_size - new_file_size))
line_reduction=$((line_count - new_line_count))
```

Report results:
```
🧹 CLEANUP COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before: [X]KB ([Y] lines)
After:  [A]KB ([B] lines)

Reduced: [reduction]KB ([line_reduction] lines)
Percentage: [percentage]% smaller

📦 Archive Created:
   [archive_file]
   [X]KB preserved

✅ Retained:
   • Active sprint information
   • Current blockers
   • Recent agent activity (last 10 entries)
   • Important decisions

🗑️  Removed:
   • Completed sprints
   • Old agent logs (>30 days)
   • Resolved blockers
   • Archived decisions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Your PROJECT_CONTEXT.md is now optimized!

📁 Archive available at: [archive_file]
   (Can be deleted after reviewing if not needed)

🔍 View current status: /status
```

### 7. Optional: Initialize Fresh Context

If file was extremely large or user wants clean slate:

```
Would you like to initialize a fresh PROJECT_CONTEXT.md?
This will:
   • Keep the archive
   • Create new PROJECT_CONTEXT.md from template
   • You'll start with clean slate

Initialize fresh context? (y/n)
```

If yes:
```bash
# Backup current (already archived) and copy template
cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md

echo "✅ Fresh PROJECT_CONTEXT.md initialized"
echo ""
echo "📝 Edit PROJECT_CONTEXT.md to add your project info"
echo "   Or start working and it will be populated automatically"
```

---

## Cleanup Strategy

The cleanup process preserves:
- ✅ Active sprint/feature information
- ✅ Current success criteria and progress
- ✅ Active blockers (unresolved)
- ✅ Recent agent activity (last 10-20 entries)
- ✅ Important shared decisions
- ✅ Artifacts created in last 30 days

The cleanup process removes:
- 🗑️ Completed sprints (moved to archive)
- 🗑️ Old agent activity logs (>30 days)
- 🗑️ Resolved blockers
- 🗑️ Archived decisions (no longer relevant)
- 🗑️ Duplicate or redundant entries

---

## When to Clean Context

**Recommended cleanup triggers:**
- File size > 100KB
- More than 1000 lines
- Completed major sprint/feature
- Context feels cluttered
- Performance degradation
- Starting new project phase

**Frequency:**
- Monthly for active projects
- After completing major features
- When switching project focus
- Before archiving project

---

## Archive Management

Archives are saved as:
```
PROJECT_ARCHIVE_YYYYMMDD_HHMMSS.md
```

**Archive retention:**
- Keep recent archives (last 3-6 months)
- Delete old archives after project completion
- Store in git if important for history
- Compress if storing long-term

**Finding old archives:**
```bash
ls -lt PROJECT_ARCHIVE_*.md
```

---

## Error Handling

**If PROJECT_CONTEXT.md doesn't exist:**
```
ℹ️  No PROJECT_CONTEXT.md found

Would you like to create one? (y/n)

[If yes, copy from template]
```

**If cleanup script fails:**
```
⚠️  Cleanup script failed or unavailable

Options:
   1. Manual review: Open PROJECT_CONTEXT.md and remove old content
   2. Fresh start: Archive current and initialize new from template
   3. Leave as-is: Continue with current file

What would you like to do?
```

**If file is small (<50KB):**
```
✅ PROJECT_CONTEXT.md is already optimal

File: [X]KB ([Y] lines)
Status: No cleanup needed

💡 Run cleanup when file grows >100KB
```

---

## Notes

- Always creates archive before cleaning (safe operation)
- Archives are timestamped for easy identification
- Cleanup is conservative - preserves recent and active information
- Can be run multiple times safely
- Does not affect .claude/ global configuration
- Only affects PROJECT_CONTEXT.md in current directory
