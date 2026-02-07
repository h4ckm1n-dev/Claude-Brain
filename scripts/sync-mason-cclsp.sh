#!/bin/bash
# sync-mason-cclsp.sh — Auto-sync Mason LSP binaries to cclsp.json
# Scans Mason bin dir for known LSP servers, validates symlinks, generates cclsp config.
# Usage: bash sync-mason-cclsp.sh [--dry-run]

set -euo pipefail

MASON_BIN="$HOME/.local/share/nvim/mason/bin"
CCLSP_CONFIG="$HOME/.config/cclsp/cclsp.json"
OVERRIDES_FILE="$HOME/.config/cclsp/rootdir-overrides.json"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Validate a symlink: exists, resolves, and target is executable
valid_bin() {
    local bin="$1"
    [[ -L "$bin" || -f "$bin" ]] && [[ -x "$(readlink -f "$bin" 2>/dev/null || echo "$bin")" ]]
}

# Read rootDir override for a server binary name, default to "."
get_rootdir() {
    local server_name="$1"
    if [[ -f "$OVERRIDES_FILE" ]]; then
        local override
        override=$(python3 -c "
import json, sys
with open('$OVERRIDES_FILE') as f:
    d = json.load(f)
print(d.get('$server_name', ''))
" 2>/dev/null)
        if [[ -n "$override" ]]; then
            echo "$override"
            return
        fi
    fi
    echo "."
}

# Build a JSON server entry
# Args: extensions_csv command_json rootDir [initOptions_json]
build_entry() {
    local extensions_csv="$1"
    local command_json="$2"
    local root_dir="$3"
    local init_options="${4:-}"

    local ext_array
    ext_array=$(echo "$extensions_csv" | python3 -c "
import sys, json
print(json.dumps(sys.stdin.read().strip().split(',')))
")

    if [[ -n "$init_options" ]]; then
        python3 -c "
import json
entry = {
    'extensions': json.loads('$ext_array'),
    'command': json.loads('$command_json'),
    'rootDir': '$root_dir',
    'initializationOptions': json.loads('''$init_options''')
}
print(json.dumps(entry))
"
    else
        python3 -c "
import json
entry = {
    'extensions': json.loads('$ext_array'),
    'command': json.loads('$command_json'),
    'rootDir': '$root_dir'
}
print(json.dumps(entry))
"
    fi
}

# ── Server definitions ──────────────────────────────────────────────────────
# Each entry: binary_name | extensions | command_args | initOptions (optional)

servers=()
skipped=()

add_server() {
    local name="$1" extensions="$2" bin_path="$3" cmd_json="$4" init_opts="${5:-}"

    if ! valid_bin "$bin_path"; then
        skipped+=("$name (broken or missing: $bin_path)")
        return
    fi

    local root_dir
    root_dir=$(get_rootdir "$name")
    local entry
    entry=$(build_entry "$extensions" "$cmd_json" "$root_dir" "$init_opts")
    servers+=("$entry")
    echo "  + $name -> $extensions (rootDir: $root_dir)"
}

echo "Scanning Mason binaries at $MASON_BIN ..."
echo ""

# Python — pylsp (Jedi-based, fast cold start, no timeout issues)
PYLSP_INIT='{
    "pylsp": {
        "plugins": {
            "jedi_completion": {"enabled": true},
            "jedi_definition": {"enabled": true},
            "jedi_hover": {"enabled": true},
            "jedi_references": {"enabled": true},
            "jedi_symbols": {"enabled": true},
            "rope_completion": {"enabled": false},
            "yapf": {"enabled": false},
            "autopep8": {"enabled": false},
            "pyflakes": {"enabled": false},
            "pycodestyle": {"enabled": false},
            "mccabe": {"enabled": false},
            "pylint": {"enabled": false}
        }
    }
}'
add_server "pylsp" "py,pyi" \
    "$MASON_BIN/pylsp" \
    "[\"$MASON_BIN/pylsp\"]" \
    "$PYLSP_INIT"

# Go
add_server "gopls" "go,mod,sum" \
    "$MASON_BIN/gopls" \
    "[\"$MASON_BIN/gopls\"]"

# TypeScript/JavaScript
add_server "typescript-language-server" "js,ts,jsx,tsx,mjs,cjs" \
    "$MASON_BIN/typescript-language-server" \
    "[\"$MASON_BIN/typescript-language-server\", \"--stdio\"]"

# Rust — prefer cargo/rustup version, fall back to Mason
RUST_BIN="$HOME/.cargo/bin/rust-analyzer"
if ! valid_bin "$RUST_BIN"; then
    RUST_BIN="$MASON_BIN/rust-analyzer"
fi
add_server "rust-analyzer" "rs" \
    "$RUST_BIN" \
    "[\"$RUST_BIN\"]"

# YAML
add_server "yaml-language-server" "yaml,yml" \
    "$MASON_BIN/yaml-language-server" \
    "[\"$MASON_BIN/yaml-language-server\", \"--stdio\"]"

# Lua
add_server "lua-language-server" "lua" \
    "$MASON_BIN/lua-language-server" \
    "[\"$MASON_BIN/lua-language-server\"]"

# Bash
add_server "bash-language-server" "sh,bash" \
    "$MASON_BIN/bash-language-server" \
    "[\"$MASON_BIN/bash-language-server\", \"start\"]"

# Terraform
add_server "terraform-ls" "tf,tfvars" \
    "$MASON_BIN/terraform-ls" \
    "[\"$MASON_BIN/terraform-ls\", \"serve\"]"

# HTML
add_server "vscode-html-language-server" "html" \
    "$MASON_BIN/vscode-html-language-server" \
    "[\"$MASON_BIN/vscode-html-language-server\", \"--stdio\"]"

# CSS
add_server "vscode-css-language-server" "css,scss,less" \
    "$MASON_BIN/vscode-css-language-server" \
    "[\"$MASON_BIN/vscode-css-language-server\", \"--stdio\"]"

# JSON — previously caused cclsp crash, extra validation
add_server "vscode-json-language-server" "json,jsonc" \
    "$MASON_BIN/vscode-json-language-server" \
    "[\"$MASON_BIN/vscode-json-language-server\", \"--stdio\"]"

# Dockerfile
add_server "docker-langserver" "dockerfile" \
    "$MASON_BIN/docker-langserver" \
    "[\"$MASON_BIN/docker-langserver\", \"--stdio\"]"

# PHP
add_server "intelephense" "php" \
    "$MASON_BIN/intelephense" \
    "[\"$MASON_BIN/intelephense\", \"--stdio\"]"

# Kotlin
add_server "kotlin-language-server" "kt,kts" \
    "$MASON_BIN/kotlin-language-server" \
    "[\"$MASON_BIN/kotlin-language-server\"]"

# Zig
add_server "zls" "zig" \
    "$MASON_BIN/zls" \
    "[\"$MASON_BIN/zls\"]"

# TOML — taplo uses subcommand
add_server "taplo" "toml" \
    "$MASON_BIN/taplo" \
    "[\"$MASON_BIN/taplo\", \"lsp\", \"stdio\"]"

# ── Assemble final config ───────────────────────────────────────────────────

echo ""
if [[ ${#skipped[@]} -gt 0 ]]; then
    echo "Skipped (broken/missing):"
    for s in "${skipped[@]}"; do
        echo "  - $s"
    done
    echo ""
fi

echo "Total: ${#servers[@]} servers"

# Build the JSON array
SERVERS_JSON=$(python3 -c "
import json, sys
entries = []
for line in sys.stdin:
    line = line.strip()
    if line:
        entries.append(json.loads(line))
print(json.dumps({'servers': entries}, indent=2))
" <<< "$(printf '%s\n' "${servers[@]}")")

if $DRY_RUN; then
    echo ""
    echo "=== DRY RUN — would write to $CCLSP_CONFIG ==="
    echo "$SERVERS_JSON"
else
    mkdir -p "$(dirname "$CCLSP_CONFIG")"
    echo "$SERVERS_JSON" > "$CCLSP_CONFIG"
    echo ""
    echo "Written to $CCLSP_CONFIG"
fi
