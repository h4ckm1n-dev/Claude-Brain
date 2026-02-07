#!/bin/bash
# Claude Code Status Line - Inspired by Starship configuration

# Read JSON input from stdin
input=$(cat)

# Extract data from JSON
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')


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
        output+=$(printf "on \033[1;32m %s\033[0m " "$branch")

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
    [[ -n "$py_version" ]] && output+=$(printf "via \033[1;33m %s\033[0m " "$py_version")
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

# Memory system stats (cached, refreshes every 60s)
mem_cache="/tmp/.claude-mem-stats"
mem_age=999
[[ -f "$mem_cache" ]] && mem_age=$(( $(date +%s) - $(stat -f%m "$mem_cache" 2>/dev/null || echo 0) ))
if [[ $mem_age -gt 60 ]]; then
    mem_json=$(curl -sf --max-time 1 "http://localhost:8100/stats" 2>/dev/null)
    graph_json=$(curl -sf --max-time 1 "http://localhost:8100/graph/stats" 2>/dev/null)
    if [[ -n "$mem_json" ]]; then
        mem_total=$(echo "$mem_json" | jq -r '.total_memories // 0')
        mem_errors=$(echo "$mem_json" | jq -r '.unresolved_errors // 0')
        mem_graph=$(echo "$graph_json" | jq -r '.relationships // 0' 2>/dev/null)
        echo "${mem_total}|${mem_graph:-0}|${mem_errors}" > "$mem_cache"
    fi
fi
if [[ -f "$mem_cache" ]]; then
    IFS='|' read -r m_total m_graph m_errors < "$mem_cache"
    mem_segment=$(printf "\033[1;35m󰍉 %s\033[0m " "$m_total")
    mem_segment+=$(printf "\033[1;34m󰛡 %s\033[0m" "$m_graph")
    if [[ "$m_errors" -gt 0 ]] 2>/dev/null; then
        mem_segment+=$(printf " \033[1;31m %s\033[0m" "$m_errors")
    fi
    output+=$(printf "| %s " "$mem_segment")
fi

# Model + context
# Calculate context tokens from current_usage (most accurate)
ctx_input=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
ctx_cache_create=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
ctx_cache_read=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
ctx_window=$(echo "$input" | jq -r '.context_window.context_window_size // 0')

if [[ "$ctx_window" -gt 0 ]] 2>/dev/null; then
    ctx_used_tokens=$((ctx_input + ctx_cache_create + ctx_cache_read))
    # Auto-compact triggers at ~80% of context window
    compact_threshold=$((ctx_window * 80 / 100))
    ctx_left=$((compact_threshold - ctx_used_tokens))
    [[ $ctx_left -lt 0 ]] && ctx_left=0
    ctx_left_pct=$((ctx_left * 100 / compact_threshold))

    # Human-readable token count (K)
    ctx_used_k=$((ctx_used_tokens / 1000))
    ctx_window_k=$((ctx_window / 1000))

    # Color code: green >50%, yellow 20-50%, red <20%
    if [[ "$ctx_left_pct" -lt 20 ]] 2>/dev/null; then
        ctx_color="\033[1;31m"
    elif [[ "$ctx_left_pct" -lt 50 ]] 2>/dev/null; then
        ctx_color="\033[1;33m"
    else
        ctx_color="\033[1;32m"
    fi
    output+=$(printf "| \033[1;36m󰧑 %s\033[0m " "$model_name")
    output+=$(printf "| ${ctx_color}󰋊 %sK/%sK | 󰓅 %s%%\033[0m" "$ctx_used_k" "$ctx_window_k" "$ctx_left_pct")
elif [[ -n "$model_name" ]]; then
    output+=$(printf "| \033[1;36m󰧑 %s\033[0m" "$model_name")
fi

echo "$output"
