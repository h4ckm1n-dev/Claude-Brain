#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Claude Brain Memory System — Bootstrap Installer
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/h4ckm1n-dev/Claude-Brain/main/memory/install.sh | bash
#
# This script:
#   1. Checks for git, curl, node, docker
#   2. Clones the repo into ~/.claude (or updates if it exists)
#   3. Runs the full setup.sh from the cloned repo
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

REPO_URL="https://github.com/h4ckm1n-dev/Claude-Brain.git"
CLAUDE_DIR="$HOME/.claude"
SETUP_SCRIPT="$CLAUDE_DIR/memory/setup.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
die()   { printf "${RED}[ERR]${NC}   %s\n" "$*" >&2; exit 1; }

# ── Minimal prereqs (just enough to clone) ────────────────────────────────────

command -v git  &>/dev/null || die "git is not installed. Install it first."
command -v curl &>/dev/null || die "curl is not installed. Install it first."

# ── Clone or update ───────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${CYAN}Claude Brain Memory System${NC}"
echo -e "──────────────────────────"
echo ""

if [[ -d "$CLAUDE_DIR/.git" ]]; then
    info "Existing repo at $CLAUDE_DIR — pulling latest..."
    cd "$CLAUDE_DIR"
    if { ! git diff --quiet || ! git diff --cached --quiet; } 2>/dev/null; then
        info "Stashing local changes..."
        git stash push -m "install.sh auto-stash $(date +%Y%m%d-%H%M%S)" || true
    fi
    git pull --rebase origin main 2>/dev/null || {
        info "Pull failed — continuing with current version"
    }
    ok "Repository updated"
elif [[ ! -d "$CLAUDE_DIR" ]]; then
    info "Cloning Claude Brain into $CLAUDE_DIR..."
    git clone "$REPO_URL" "$CLAUDE_DIR"
    ok "Repository cloned"
elif [[ -d "$CLAUDE_DIR/memory" ]]; then
    info "$CLAUDE_DIR exists (not a git repo) — updating memory directory..."
    local_tmpdir=$(mktemp -d) || die "Failed to create temp directory"
    trap "rm -rf '$local_tmpdir'" EXIT
    git clone "$REPO_URL" "$local_tmpdir"
    # Sync memory and mcp directories
    rsync -a --delete "$local_tmpdir/memory/" "$CLAUDE_DIR/memory/" 2>/dev/null \
        || cp -r "$local_tmpdir/memory/"* "$CLAUDE_DIR/memory/"
    mkdir -p "$CLAUDE_DIR/mcp"
    rsync -a "$local_tmpdir/mcp/" "$CLAUDE_DIR/mcp/" 2>/dev/null \
        || cp -r "$local_tmpdir/mcp/"* "$CLAUDE_DIR/mcp/"
    rm -rf "$local_tmpdir"
    trap - EXIT
    ok "Memory system updated"
else
    info "$CLAUDE_DIR exists but has no memory dir — cloning into it..."
    local_tmpdir=$(mktemp -d) || die "Failed to create temp directory"
    trap "rm -rf '$local_tmpdir'" EXIT
    git clone "$REPO_URL" "$local_tmpdir"
    cp -r "$local_tmpdir/memory" "$CLAUDE_DIR/memory"
    mkdir -p "$CLAUDE_DIR/mcp"
    cp -r "$local_tmpdir/mcp/"* "$CLAUDE_DIR/mcp/" 2>/dev/null || true
    rm -rf "$local_tmpdir"
    trap - EXIT
    ok "Memory system installed"
fi

# ── Hand off to full setup ────────────────────────────────────────────────────

if [[ ! -f "$SETUP_SCRIPT" ]]; then
    die "setup.sh not found at $SETUP_SCRIPT — clone may have failed"
fi

chmod +x "$SETUP_SCRIPT"
info "Running full setup..."
echo ""

# Execute setup.sh in a new bash process (not from stdin pipe)
exec bash "$SETUP_SCRIPT"
