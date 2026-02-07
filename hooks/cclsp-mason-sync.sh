#!/bin/bash
# cclsp-mason-sync.sh — SessionStart hook
# Re-syncs Mason→cclsp config only if Mason bin dir changed since last sync.

MASON_BIN="$HOME/.local/share/nvim/mason/bin"
CCLSP_CONFIG="$HOME/.config/cclsp/cclsp.json"
SYNC_SCRIPT="$HOME/.claude/scripts/sync-mason-cclsp.sh"

# Skip if sync script doesn't exist
[[ -x "$SYNC_SCRIPT" ]] || exit 0

# Skip if Mason bin dir doesn't exist
[[ -d "$MASON_BIN" ]] || exit 0

# Compare mtimes: re-sync if Mason bin dir is newer than cclsp.json
if [[ ! -f "$CCLSP_CONFIG" ]] || [[ "$MASON_BIN" -nt "$CCLSP_CONFIG" ]]; then
    /bin/bash "$SYNC_SCRIPT" > /dev/null 2>&1
fi

exit 0
