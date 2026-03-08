#!/bin/bash
# Doc File Sprawl Prevention
# Triggers: PreToolUse (Write|Edit)
# Purpose: Warn when creating non-standard documentation files

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

# Only check .md and .txt files
case "$FILE_PATH" in
    *.md|*.txt) ;;
    *) exit 0 ;;
esac

FILENAME=$(basename "$FILE_PATH")

# Allow standard documentation files
case "$FILENAME" in
    README.md|CLAUDE.md|CHANGELOG.md|CONTRIBUTING.md|LICENSE|LICENSE.md|AGENTS.md|SKILL.md|MEMORY.md|MCP-TOOLS.md|PLAN.md|TODO.md|PROJECT.md|ROADMAP.md)
        exit 0
        ;;
esac

# Allow files in known directories where docs are expected
case "$FILE_PATH" in
    */memory/*|*/docs/*|*/.claude/agents/*|*/.claude/commands/*|*/.claude/skills/*|*/.planning/*|*/.claude/projects/*)
        exit 0
        ;;
esac

echo "Warning: Creating non-standard doc file '$FILENAME'. Consider whether this content belongs in an existing doc (README.md, CLAUDE.md) or a structured memory instead."
exit 0
