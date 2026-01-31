#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Claude Code Status Line - Catppuccin Mocha (Modern Minimalist)
# ══════════════════════════════════════════════════════════════════════════════
#
# A clean, unified statusline with consistent badge styling
# All elements use the same visual language for coherence
#

# ─────────────────────────────────────────────────────────────────────────────
# CATPPUCCIN MOCHA PALETTE
# ─────────────────────────────────────────────────────────────────────────────

# Text colors
MAUVE="\033[38;2;203;166;247m"
RED="\033[38;2;243;139;168m"
PEACH="\033[38;2;250;179;135m"
YELLOW="\033[38;2;249;226;175m"
GREEN="\033[38;2;166;227;161m"
TEAL="\033[38;2;148;226;213m"
SAPPHIRE="\033[38;2;116;199;236m"
BLUE="\033[38;2;137;180;250m"
LAVENDER="\033[38;2;180;190;254m"
TEXT="\033[38;2;205;214;244m"
SUBTEXT="\033[38;2;166;173;200m"
OVERLAY="\033[38;2;108;112;134m"
SURFACE="\033[38;2;69;71;90m"
BASE="\033[38;2;30;30;46m"

# Background colors
BG_MAUVE="\033[48;2;203;166;247m"
BG_BLUE="\033[48;2;137;180;250m"
BG_GREEN="\033[48;2;166;227;161m"
BG_TEAL="\033[48;2;148;226;213m"
BG_PEACH="\033[48;2;250;179;135m"
BG_RED="\033[48;2;243;139;168m"
BG_YELLOW="\033[48;2;249;226;175m"
BG_SURFACE="\033[48;2;69;71;90m"
BG_OVERLAY="\033[48;2;88;91;112m"

# Formatting
BOLD="\033[1m"
RESET="\033[0m"
DARK="\033[38;2;30;30;46m"  # Dark text for light backgrounds

# ─────────────────────────────────────────────────────────────────────────────
# ICONS (Nerd Font with Unicode fallbacks)
# ─────────────────────────────────────────────────────────────────────────────

if [[ "$TERM_PROGRAM" == "iTerm.app" ]] || [[ -n "$WEZTERM_PANE" ]] || [[ "$TERM" == *"kitty"* ]] || [[ -n "$GHOSTTY_RESOURCES_DIR" ]]; then
    IC_BRANCH=""
    IC_FOLDER=""
    IC_DB=""
    IC_AGENT="󰚩"
    IC_WARN=""
    IC_MOD="●"
    IC_ADD=""
    IC_NEW="?"
else
    IC_BRANCH="⎇"
    IC_FOLDER="~"
    IC_DB="◉"
    IC_AGENT="λ"
    IC_WARN="!"
    IC_MOD="•"
    IC_ADD="+"
    IC_NEW="?"
fi

# ─────────────────────────────────────────────────────────────────────────────
# BADGE HELPER
# ─────────────────────────────────────────────────────────────────────────────

# Creates a consistent badge: badge "BG_COLOR" "content"
badge() {
    local bg="$1"
    local content="$2"
    echo -e "${bg}${DARK}${BOLD} ${content} ${RESET}"
}

# Creates a subtle badge (surface background)
badge_subtle() {
    local content="$1"
    echo -e "${BG_SURFACE}${TEXT} ${content} ${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# STATUS COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

# Model badge
get_model() {
    local model="${CLAUDE_MODEL:-unknown}"
    case "$model" in
        *opus*)   badge "$BG_MAUVE" "OPUS" ;;
        *sonnet*) badge "$BG_BLUE" "SONNET" ;;
        *haiku*)  badge "$BG_GREEN" "HAIKU" ;;
        *)        badge_subtle "CLAUDE" ;;
    esac
}

# Directory badge
get_directory() {
    local dir="${PWD/#$HOME/~}"
    # Truncate long paths
    if [[ ${#dir} -gt 25 ]]; then
        dir="…${dir: -22}"
    fi
    echo -e "${BG_SURFACE}${SAPPHIRE} ${IC_FOLDER} ${dir} ${RESET}"
}

# Git badge (branch + status combined)
get_git() {
    if ! git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
        return
    fi

    local branch=$(git branch --show-current 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
    local status_icons=""

    # Check states
    if ! git diff --quiet 2>/dev/null; then
        status_icons+="${IC_MOD}"
    fi
    if ! git diff --cached --quiet 2>/dev/null; then
        status_icons+="${IC_ADD}"
    fi
    if [[ -n $(git ls-files --others --exclude-standard 2>/dev/null | head -1) ]]; then
        status_icons+="${IC_NEW}"
    fi

    # Build content
    local content="${IC_BRANCH} ${branch}"
    if [[ -n "$status_icons" ]]; then
        content+=" ${status_icons}"
    fi

    # Color based on state
    if [[ -z "$status_icons" ]]; then
        # Clean - green
        echo -e "${BG_GREEN}${DARK}${BOLD} ${content} ${RESET}"
    else
        # Dirty - peach
        echo -e "${BG_PEACH}${DARK}${BOLD} ${content} ${RESET}"
    fi
}

# Memory system badge
get_memory() {
    local health
    health=$(curl -s --connect-timeout 0.5 http://localhost:8100/health 2>/dev/null)

    if [[ -z "$health" ]]; then
        # Offline
        echo -e "${BG_SURFACE}${OVERLAY} ${IC_DB} OFF ${RESET}"
        return
    fi

    local count=$(echo "$health" | grep -o '"memory_count":[0-9]*' | cut -d: -f2)
    local qdrant=$(echo "$health" | grep -o '"qdrant":"[^"]*"' | cut -d: -f2 | tr -d '"')

    # Check for unresolved errors
    local stats
    stats=$(curl -s --connect-timeout 0.3 http://localhost:8100/stats 2>/dev/null)
    local errors=$(echo "$stats" | grep -o '"unresolved_errors":[0-9]*' | cut -d: -f2)

    if [[ "$qdrant" == "connected" ]]; then
        local content="${IC_DB} ${count:-0}"
        if [[ -n "$errors" && "$errors" -gt 0 ]]; then
            # Has errors - show warning
            echo -e "${BG_YELLOW}${DARK}${BOLD} ${content} ${IC_WARN}${errors} ${RESET}"
        else
            # All good
            echo -e "${BG_TEAL}${DARK}${BOLD} ${content} ${RESET}"
        fi
    else
        # DB not connected
        echo -e "${BG_YELLOW}${DARK}${BOLD} ${IC_DB} ? ${RESET}"
    fi
}

# Agent count badge
get_agents() {
    if [[ -d "$HOME/.claude/agents" ]]; then
        local count=$(find "$HOME/.claude/agents" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
        if [[ $count -gt 0 ]]; then
            echo -e "${BG_SURFACE}${LAVENDER} ${IC_AGENT} ${count} ${RESET}"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# BUILD STATUSLINE
# ─────────────────────────────────────────────────────────────────────────────

main() {
    local parts=()

    # Left: Model
    parts+=("$(get_model)")

    # Center: Directory + Git
    parts+=("$(get_directory)")

    local git_badge=$(get_git)
    [[ -n "$git_badge" ]] && parts+=("$git_badge")

    # Right: Memory + Agents
    parts+=("$(get_memory)")

    local agents_badge=$(get_agents)
    [[ -n "$agents_badge" ]] && parts+=("$agents_badge")

    # Output with single space between badges
    local output=""
    for part in "${parts[@]}"; do
        output+="${part} "
    done

    echo -e "${output}"
}

main
