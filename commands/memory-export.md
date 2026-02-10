---
description: "Export memories for backup — supports JSON, CSV, and Obsidian markdown formats"
allowed-tools: ["mcp__memory__export_memories", "mcp__memory__memory_stats", "Bash"]
model: sonnet
---

# Memory Export & Backup

Export memories to a file for backup or external use.

**Input:** `$ARGUMENTS` — format: `json` (default), `csv`, or `obsidian`. Optionally followed by a project name filter.

Parse `$ARGUMENTS`:
- If empty or unrecognized → default to `json`
- First word = format (`json`, `csv`, `obsidian`)
- Second word (optional) = project filter

---

## Step 1: Pre-export Summary

Call `memory_stats()` to show what will be exported.

Display:
- Total memory count
- By-type breakdown
- By-project breakdown
- Export format selected
- Project filter (if any)

---

## Step 2: Ensure Export Directory

```bash
mkdir -p ~/.claude/memory/exports
```

---

## Step 3: Export

Call `export_memories(format="{format}", project="{project_filter_or_omit}")`.

---

## Step 4: Save to File

Generate a timestamped filename:
```bash
date +%Y%m%d-%H%M%S
```

Save the export output to `~/.claude/memory/exports/{timestamp}.{format_extension}` where:
- `json` → `.json`
- `csv` → `.csv`
- `obsidian` → `.md`

Write the file using Bash.

---

## Step 5: Report

```bash
ls -lh ~/.claude/memory/exports/{filename}
```

Display:
```
Export complete!
  Format:    {format}
  File:      ~/.claude/memory/exports/{filename}
  Size:      {file_size}
  Memories:  {count}
  Project:   {filter or "all"}
```
