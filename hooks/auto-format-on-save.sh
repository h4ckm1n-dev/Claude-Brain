#!/bin/bash
# Auto-format on Save — PostToolUse (Write|Edit) [async]
# Detects Biome or Prettier in the project and formats edited files
# Only runs on JS/TS files to avoid unnecessary processing

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

# Only format JS/TS files
case "$FILE_PATH" in
    *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.mts|*.cts) ;;
    *) exit 0 ;;
esac

# File must exist
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Find project root (look for package.json walking up)
DIR=$(dirname "$FILE_PATH")
PROJECT_ROOT=""
SEARCH_DIR="$DIR"
for _ in $(seq 1 10); do
    if [ -f "$SEARCH_DIR/package.json" ]; then
        PROJECT_ROOT="$SEARCH_DIR"
        break
    fi
    PARENT=$(dirname "$SEARCH_DIR")
    if [ "$PARENT" = "$SEARCH_DIR" ]; then
        break
    fi
    SEARCH_DIR="$PARENT"
done

if [ -z "$PROJECT_ROOT" ]; then
    exit 0
fi

# Try Biome first (faster), then Prettier
if [ -f "$PROJECT_ROOT/biome.json" ] || [ -f "$PROJECT_ROOT/biome.jsonc" ]; then
    # Check for biome binary
    if [ -x "$PROJECT_ROOT/node_modules/.bin/biome" ]; then
        "$PROJECT_ROOT/node_modules/.bin/biome" format --write "$FILE_PATH" 2>/dev/null
    elif command -v biome &>/dev/null; then
        biome format --write "$FILE_PATH" 2>/dev/null
    fi
elif [ -f "$PROJECT_ROOT/.prettierrc" ] || [ -f "$PROJECT_ROOT/.prettierrc.json" ] || \
     [ -f "$PROJECT_ROOT/.prettierrc.js" ] || [ -f "$PROJECT_ROOT/.prettierrc.cjs" ] || \
     [ -f "$PROJECT_ROOT/.prettierrc.yaml" ] || [ -f "$PROJECT_ROOT/.prettierrc.yml" ] || \
     [ -f "$PROJECT_ROOT/prettier.config.js" ] || [ -f "$PROJECT_ROOT/prettier.config.cjs" ]; then
    if [ -x "$PROJECT_ROOT/node_modules/.bin/prettier" ]; then
        "$PROJECT_ROOT/node_modules/.bin/prettier" --write "$FILE_PATH" 2>/dev/null
    elif command -v prettier &>/dev/null; then
        prettier --write "$FILE_PATH" 2>/dev/null
    fi
else
    # Check package.json for prettier as dependency (common to not have config file)
    if grep -q '"prettier"' "$PROJECT_ROOT/package.json" 2>/dev/null; then
        if [ -x "$PROJECT_ROOT/node_modules/.bin/prettier" ]; then
            "$PROJECT_ROOT/node_modules/.bin/prettier" --write "$FILE_PATH" 2>/dev/null
        fi
    fi
fi

exit 0
