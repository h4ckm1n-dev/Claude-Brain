#!/bin/bash
# Claude Code Status Line - Inspired by Starship configuration

# Read JSON input from stdin
input=$(cat)

# Extract data from JSON
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')
context_remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')

# Directory display (truncated like Starship)
if [[ "$cwd" == "$HOME"* ]]; then
    display_dir="~${cwd#$HOME}"
else
    display_dir="$cwd"
fi

output=""

# Git repo-relative path
if git -C "$cwd" rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    repo_root=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null)
    if [[ -n "$repo_root" ]]; then
        repo_name=$(basename "$repo_root")
        relative_path="${cwd#$repo_root}"
        if [[ -z "$relative_path" ]]; then
            display_dir="$repo_name"
        else
            display_dir="$repo_name$relative_path"
        fi
    fi
fi

output+=$(printf "\033[1;34m%s\033[0m " "$display_dir")

# Git branch and status
if git -C "$cwd" rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    branch=$(git -C "$cwd" branch --show-current 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
    if [[ -n "$branch" ]]; then
        output+=$(printf "on \033[1;32m %s\033[0m " "$branch")

        git_status=$(git -C "$cwd" --no-optional-locks status --porcelain 2>/dev/null)
        status_icons=""
        echo "$git_status" | grep -q "^??" && status_icons+=""
        echo "$git_status" | grep -q "^ M" && status_icons+=""
        echo "$git_status" | grep -q "^M " && status_icons+="++"
        echo "$git_status" | grep -q "^D " && status_icons+=""

        if [[ -n "$status_icons" ]]; then
            output+=$(printf "\033[1;32m(%s)\033[0m " "$status_icons")
        fi
    fi
fi

# Python
if [[ -f "$cwd/requirements.txt" ]] || [[ -f "$cwd/pyproject.toml" ]] || [[ -f "$cwd/setup.py" ]]; then
    py_version=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    [[ -n "$py_version" ]] && output+=$(printf "via \033[1;33m %s\033[0m " "$py_version")
fi

# Node.js
if [[ -f "$cwd/package.json" ]]; then
    node_version=$(node --version 2>/dev/null | sed 's/v//')
    [[ -n "$node_version" ]] && output+=$(printf "via \033[1;32m󰎙 %s\033[0m " "$node_version")
fi

# Docker
if [[ -f "$cwd/Dockerfile" ]] || [[ -f "$cwd/docker-compose.yml" ]] || [[ -f "$cwd/compose.yml" ]]; then
    output+=$(printf "via \033[1;34m󰡨 docker\033[0m ")
fi

# Model + context
if [[ -n "$context_remaining" ]]; then
    output+=$(printf "| \033[1;36m%s\033[0m " "$model_name")
    output+=$(printf "\033[1;33m(%s%% ctx)\033[0m" "$context_remaining")
fi

echo "$output"
