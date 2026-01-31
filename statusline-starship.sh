#!/bin/bash

# Read JSON input from stdin
input=$(cat)
current_dir=$(echo "$input" | jq -r '.workspace.current_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')
session_id=$(echo "$input" | jq -r '.session_id')

# Change to the current directory
cd "$current_dir" 2>/dev/null || true

# Colors for better visibility and compatibility
BOLD_GREEN=$'\033[1;32m'
BOLD_BLUE=$'\033[1;34m'
BOLD_YELLOW=$'\033[1;33m'
BOLD_RED=$'\033[1;31m'
BRIGHT_CYAN=$'\033[1;96m'
RESET=$'\033[0m'
DIM=$'\033[2m'

# Directory display (no icon)
if [[ "$current_dir" == "$HOME" ]]; then
    printf "${BOLD_GREEN}~ ${RESET}"
else
    dir_name=$(basename "$current_dir")
    if [[ ${#current_dir} -gt 60 ]]; then
        printf "${BOLD_GREEN}.../%s ${RESET}" "$dir_name"
    else
        printf "${BOLD_GREEN}%s ${RESET}" "$dir_name"
    fi
fi

# Git information with reliable symbols
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
    
    # Git branch with simple text prefix
    printf "${DIM}on${RESET} ${BOLD_GREEN}git:${branch}${RESET} "
    
    # Git status with simple, reliable symbols
    git_status=$(git status --porcelain 2>/dev/null)
    
    if [[ -n "$git_status" ]]; then
        status_indicators=""
        
        # Count different types of changes with reliable symbols
        staged=$(echo "$git_status" | grep -c "^[MADRC]" 2>/dev/null || echo "0")
        modified=$(echo "$git_status" | grep -c "^.[MD]" 2>/dev/null || echo "0")
        untracked=$(echo "$git_status" | grep -c "^??" 2>/dev/null || echo "0")
        deleted=$(echo "$git_status" | grep -c "^.D" 2>/dev/null || echo "0")
        
        # Use simple ASCII symbols that work everywhere
        [[ $staged -gt 0 ]] && status_indicators+="${BOLD_GREEN}+${staged}${RESET} "
        [[ $modified -gt 0 ]] && status_indicators+="${BOLD_YELLOW}~${modified}${RESET} "
        [[ $deleted -gt 0 ]] && status_indicators+="${BOLD_RED}-${deleted}${RESET} "
        [[ $untracked -gt 0 ]] && status_indicators+="${DIM}?${untracked}${RESET} "
        
        # Check for stashed changes
        stashed=$(git stash list 2>/dev/null | wc -l | tr -d ' ')
        [[ $stashed -gt 0 ]] && status_indicators+="${BRIGHT_CYAN}S${stashed}${RESET} "
        
        # Ahead/behind check with simple arrows
        upstream=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null)
        if [[ -n "$upstream" ]]; then
            ahead_behind=$(git rev-list --left-right --count HEAD..."$upstream" 2>/dev/null)
            if [[ -n "$ahead_behind" ]]; then
                ahead=$(echo "$ahead_behind" | cut -f1)
                behind=$(echo "$ahead_behind" | cut -f2)
                
                [[ $ahead -gt 0 ]] && status_indicators+="${BOLD_BLUE}ahead${ahead}${RESET} "
                [[ $behind -gt 0 ]] && status_indicators+="${BOLD_BLUE}behind${behind}${RESET} "
            fi
        fi
        
        if [[ -n "$status_indicators" ]]; then
            printf "[%s] " "$status_indicators"
        fi
    else
        # Clean repository
        printf "${BOLD_GREEN}clean${RESET} "
    fi
fi

# Model info with AI icon
printf "${DIM}via${RESET} ${BOLD_BLUE}🤖 %s${RESET}" "$model_name"

# Session info
session_short=$(echo "$session_id" | cut -c1-8)
printf " ${DIM}[${BRIGHT_CYAN}%s${RESET}${DIM}]${RESET}" "$session_short"