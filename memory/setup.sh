#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Claude Brain Memory System — One-Command Installer
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   bash ~/.claude/memory/setup.sh          # if repo already cloned
#   curl -fsSL <raw-url> | bash             # fresh install (clones repo)
#
# Idempotent: safe to re-run at any time.
# Supports: macOS (arm64/x86_64) + Linux (x86_64/arm64)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Constants ─────────────────────────────────────────────────────────────────

REPO_URL="https://github.com/h4ckm1n-dev/Claude-Brain.git"
CLAUDE_DIR="$HOME/.claude"
MEMORY_DIR="$CLAUDE_DIR/memory"
MCP_DIR="$CLAUDE_DIR/mcp/memory-mcp"
CLAUDE_JSON="$HOME/.claude.json"
COMPOSE_FILE="docker-compose.yml"
HEALTH_URL="http://localhost:8100"
HEALTH_TIMEOUT=180   # seconds — embedding service needs 60s+ for ML models
HEALTH_INTERVAL=5

# ── Colors & helpers ──────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No color

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
err()   { printf "${RED}[ERR]${NC}   %s\n" "$*" >&2; }
step()  { printf "\n${BOLD}${CYAN}── Step %s ──${NC}\n" "$*"; }

die() {
    err "$@"
    exit 1
}

# ── Detect OS ─────────────────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Darwin) OS="macos" ;;
        Linux)  OS="linux" ;;
        *)      die "Unsupported OS: $(uname -s). Only macOS and Linux are supported." ;;
    esac
    ARCH="$(uname -m)"
    info "Detected: $OS ($ARCH)"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Prerequisites
# ═══════════════════════════════════════════════════════════════════════════════

check_prerequisites() {
    step "1: Checking prerequisites"
    local missing=0

    # git
    if command -v git &>/dev/null; then
        ok "git $(git --version | awk '{print $3}')"
    else
        err "git is not installed"
        if [[ "$OS" == "macos" ]]; then
            info "  Install: xcode-select --install"
        else
            info "  Install: sudo apt install git  (or your package manager)"
        fi
        missing=1
    fi

    # curl
    if command -v curl &>/dev/null; then
        ok "curl found"
    else
        err "curl is not installed"
        info "  Install: sudo apt install curl  (or your package manager)"
        missing=1
    fi

    # node (18+)
    if command -v node &>/dev/null; then
        local node_version
        node_version=$(node -v | sed 's/v//' | cut -d. -f1)
        if [[ "$node_version" -ge 18 ]]; then
            ok "node $(node -v)"
        else
            err "Node.js $(node -v) is too old — need v18+"
            info "  Install: https://nodejs.org/ or use nvm/fnm"
            missing=1
        fi
    else
        err "Node.js is not installed (needed for MCP server)"
        info "  Install: https://nodejs.org/ or use nvm/fnm"
        missing=1
    fi

    # Docker
    if command -v docker &>/dev/null; then
        ok "docker $(docker --version | awk '{print $3}' | tr -d ',')"
    else
        err "Docker is not installed"
        if [[ "$OS" == "macos" ]]; then
            info "  Recommended: brew install --cask orbstack"
            info "  Alternative: brew install --cask docker"
        else
            info "  Auto-install available — run with: curl -fsSL https://get.docker.com | sh"
            if [[ -t 0 ]]; then
                # Interactive mode — ask
                printf "  ${YELLOW}Install Docker now? [y/N]:${NC} "
                read -r install_docker
            else
                # Non-interactive (piped from curl) — auto-install
                info "  Non-interactive mode — auto-installing Docker..."
                install_docker="y"
            fi
            if [[ "$install_docker" =~ ^[Yy]$ ]]; then
                info "Installing Docker via get.docker.com..."
                curl -fsSL https://get.docker.com | sh
                sudo usermod -aG docker "$USER" 2>/dev/null || true
                info "You may need to log out and back in for group changes."
            else
                missing=1
            fi
        fi
        # Re-check after potential install
        if ! command -v docker &>/dev/null; then
            missing=1
        fi
    fi

    # Docker Compose v2
    if docker compose version &>/dev/null; then
        local compose_version
        compose_version=$(docker compose version --short 2>/dev/null || docker compose version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        if [[ -z "$compose_version" ]]; then
            err "Could not parse Docker Compose version"
            missing=1
        else
            local compose_major
            compose_major=$(echo "$compose_version" | cut -d. -f1)
            if [[ "$compose_major" -ge 2 ]]; then
                ok "docker compose v$compose_version"
            else
                err "Docker Compose v$compose_version is too old — need v2.0+"
                missing=1
            fi
        fi
    else
        err "Docker Compose v2 not available"
        info "  It should come bundled with Docker Desktop / OrbStack"
        missing=1
    fi

    # Verify Docker daemon is running
    if command -v docker &>/dev/null; then
        if docker info &>/dev/null; then
            ok "Docker daemon is running"
        else
            err "Docker is installed but the daemon is not running"
            if [[ "$OS" == "macos" ]]; then
                info "  Start OrbStack or Docker Desktop first"
            else
                info "  Run: sudo systemctl start docker"
            fi
            missing=1
        fi
    fi

    if [[ "$missing" -ne 0 ]]; then
        die "Missing prerequisites. Install them and re-run this script."
    fi

    ok "All prerequisites satisfied"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Clone or update repo
# ═══════════════════════════════════════════════════════════════════════════════

setup_repo() {
    step "2: Setting up repository"

    if [[ -d "$CLAUDE_DIR/.git" ]]; then
        # Existing repo — pull latest
        info "Existing repo found at $CLAUDE_DIR — pulling latest..."
        cd "$CLAUDE_DIR"
        # Stash any local changes
        if { ! git diff --quiet || ! git diff --cached --quiet; } 2>/dev/null; then
            warn "Stashing local changes..."
            git stash push -m "setup.sh auto-stash $(date +%Y%m%d-%H%M%S)" || true
        fi
        git pull --rebase origin main || {
            warn "git pull failed — continuing with current version"
        }
        ok "Repository updated"
    elif [[ ! -d "$CLAUDE_DIR" ]]; then
        # Fresh install — clone
        info "Cloning Claude Brain into $CLAUDE_DIR..."
        git clone "$REPO_URL" "$CLAUDE_DIR"
        ok "Repository cloned"
    elif [[ -d "$MEMORY_DIR" ]]; then
        # ~/.claude exists but isn't a git repo — memory dir already present
        warn "$CLAUDE_DIR exists but is not a git repo"
        info "Memory directory already at $MEMORY_DIR — skipping clone"
    else
        # ~/.claude exists without .git or memory — clone into subdirectory
        warn "$CLAUDE_DIR exists but has no .git — installing memory system only"
        info "Cloning into $MEMORY_DIR..."
        local tmpdir
        tmpdir=$(mktemp -d) || die "Failed to create temp directory"
        trap "rm -rf '$tmpdir'" EXIT
        git clone "$REPO_URL" "$tmpdir"
        cp -r "$tmpdir/memory" "$MEMORY_DIR"
        cp -r "$tmpdir/mcp" "$CLAUDE_DIR/mcp" 2>/dev/null || true
        rm -rf "$tmpdir"
        trap - EXIT
        ok "Memory system installed to $MEMORY_DIR"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Environment setup
# ═══════════════════════════════════════════════════════════════════════════════

setup_environment() {
    step "3: Setting up environment"
    cd "$MEMORY_DIR"

    # .env from template
    if [[ -f .env ]]; then
        ok ".env already exists — keeping current config"
    elif [[ -f .env.example ]]; then
        cp .env.example .env
        ok "Created .env from .env.example"
    else
        warn "No .env.example found — containers will use defaults from docker-compose.yml"
    fi

    # Runtime directories
    local dirs=("qdrant-storage" "neo4j-data" "neo4j-logs" "logs" "data")
    for d in "${dirs[@]}"; do
        mkdir -p "$d"
    done
    ok "Runtime directories ready: ${dirs[*]}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Build Docker images
# ═══════════════════════════════════════════════════════════════════════════════

build_images() {
    step "4: Building Docker images"
    cd "$MEMORY_DIR"

    warn "First build downloads ~650MB of ML models (nomic, BM42, cross-encoder)"
    warn "This may take 5-10 minutes on first run"
    echo ""

    docker compose -f "$COMPOSE_FILE" build || die "Docker build failed"

    ok "All images built successfully"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Start containers
# ═══════════════════════════════════════════════════════════════════════════════

start_containers() {
    step "5: Starting containers"
    cd "$MEMORY_DIR"

    # Remove orphan containers from old service names (monolith era)
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans || die "Failed to start containers"

    info "Waiting for all services to become healthy (timeout: ${HEALTH_TIMEOUT}s)..."
    echo ""

    # Phase-based health checking
    local elapsed=0

    # Phase 1: Data stores
    printf "  %-30s" "Data stores (qdrant, neo4j)..."
    while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
        local qdrant_ok neo4j_ok
        qdrant_ok=$(docker inspect --format='{{.State.Health.Status}}' claude-mem-qdrant 2>/dev/null || echo "missing")
        neo4j_ok=$(docker inspect --format='{{.State.Health.Status}}' claude-mem-neo4j 2>/dev/null || echo "missing")
        if [[ "$qdrant_ok" == "healthy" && "$neo4j_ok" == "healthy" ]]; then
            printf "${GREEN}healthy${NC}\n"
            break
        fi
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done
    if [[ $elapsed -ge $HEALTH_TIMEOUT ]]; then
        printf "${RED}timeout${NC}\n"
        die "Data stores did not become healthy within ${HEALTH_TIMEOUT}s"
    fi

    # Phase 2: Embedding service (slowest — ML model loading)
    printf "  %-30s" "Embedding service (ML models)..."
    while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
        local embed_ok
        embed_ok=$(docker inspect --format='{{.State.Health.Status}}' claude-mem-embeddings 2>/dev/null || echo "missing")
        if [[ "$embed_ok" == "healthy" ]]; then
            printf "${GREEN}healthy${NC}\n"
            break
        fi
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done
    if [[ $elapsed -ge $HEALTH_TIMEOUT ]]; then
        printf "${RED}timeout${NC}\n"
        warn "Embedding service is still loading — it needs 60s+ for ML models"
        warn "Other services will wait for it via depends_on. Continuing..."
    fi

    # Phase 3: Backend microservices
    local backend_services=("claude-mem-core" "claude-mem-search" "claude-mem-graph" "claude-mem-brain" "claude-mem-quality" "claude-mem-analytics" "claude-mem-admin")
    for svc in "${backend_services[@]}"; do
        local short_name="${svc#claude-mem-}"
        printf "  %-30s" "$short_name..."
        local svc_waited=0
        while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
            local status
            status=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "missing")
            if [[ "$status" == "healthy" ]]; then
                printf "${GREEN}healthy${NC}\n"
                break
            fi
            sleep 3
            elapsed=$((elapsed + 3))
            svc_waited=$((svc_waited + 3))
            if [[ $svc_waited -ge 60 ]]; then
                printf "${YELLOW}waiting${NC}\n"
                break
            fi
        done
    done

    # Phase 4: Worker + Frontend
    printf "  %-30s" "worker (scheduler)..."
    local worker_waited=0
    while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
        local wstatus
        wstatus=$(docker inspect --format='{{.State.Health.Status}}' claude-mem-worker 2>/dev/null || echo "missing")
        if [[ "$wstatus" == "healthy" ]]; then
            printf "${GREEN}healthy${NC}\n"
            break
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        worker_waited=$((worker_waited + 3))
        if [[ $worker_waited -ge 60 ]]; then
            printf "${YELLOW}waiting${NC}\n"
            break
        fi
    done

    printf "  %-30s" "frontend (nginx)..."
    # Frontend doesn't have a health check, just check it's running
    local fstatus
    fstatus=$(docker inspect --format='{{.State.Status}}' claude-mem-frontend 2>/dev/null || echo "missing")
    if [[ "$fstatus" == "running" ]]; then
        printf "${GREEN}running${NC}\n"
    else
        printf "${RED}$fstatus${NC}\n"
    fi

    echo ""

    # Final gateway health check
    info "Checking gateway health endpoint..."
    local retries=0
    while [[ $retries -lt 20 ]]; do
        if curl -sf "$HEALTH_URL/health" &>/dev/null; then
            ok "Gateway responding at $HEALTH_URL"
            return 0
        fi
        sleep 3
        retries=$((retries + 1))
    done

    warn "Gateway not responding yet — services may still be starting"
    warn "Check logs: cd $MEMORY_DIR && docker compose logs -f"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Set up MCP server
# ═══════════════════════════════════════════════════════════════════════════════

setup_mcp_server() {
    step "6: Setting up MCP server"

    if [[ ! -d "$MCP_DIR" ]]; then
        die "MCP server directory not found at $MCP_DIR"
    fi

    cd "$MCP_DIR"

    # Install Node dependencies
    if [[ -d "node_modules" ]]; then
        ok "Node modules already installed"
    else
        info "Installing MCP server dependencies..."
        npm install --no-fund --no-audit 2>&1 | tail -1
        ok "Dependencies installed"
    fi

    # Verify compiled output exists
    if [[ -f "dist/index.js" ]]; then
        local size
        size=$(wc -c < "dist/index.js" | tr -d ' ')
        ok "MCP server binary ready (dist/index.js, ${size} bytes)"
    else
        warn "dist/index.js not found — attempting to compile..."
        if npx tsc 2>/dev/null; then
            ok "MCP server compiled"
        else
            die "Failed to compile MCP server. Ensure TypeScript is installed."
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 7: Register MCP with Claude Code
# ═══════════════════════════════════════════════════════════════════════════════

register_mcp() {
    step "7: Registering MCP server with Claude Code"

    local mcp_script_path="$HOME/.claude/mcp/memory-mcp/dist/index.js"

    if [[ ! -f "$CLAUDE_JSON" ]]; then
        info "Creating $CLAUDE_JSON..."
        echo '{"mcpServers":{}}' > "$CLAUDE_JSON"
    fi

    # Check if memory MCP is already registered
    if CLAUDE_JSON="$CLAUDE_JSON" MCP_SCRIPT_PATH="$mcp_script_path" python3 -c "
import json, sys, os
with open(os.environ['CLAUDE_JSON']) as f:
    data = json.load(f)
servers = data.get('mcpServers', {})
if 'memory' in servers:
    args = servers['memory'].get('args', [])
    if args and os.environ['MCP_SCRIPT_PATH'] in args[0]:
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
        ok "Memory MCP already registered with correct path"
        return 0
    fi

    # Merge memory MCP server into config, preserving all existing entries
    info "Adding memory MCP server to $CLAUDE_JSON..."
    CLAUDE_JSON="$CLAUDE_JSON" MCP_SCRIPT_PATH="$mcp_script_path" python3 -c "
import json, os

config_path = os.environ['CLAUDE_JSON']
mcp_path = os.environ['MCP_SCRIPT_PATH']

with open(config_path) as f:
    data = json.load(f)

if 'mcpServers' not in data:
    data['mcpServers'] = {}

data['mcpServers']['memory'] = {
    'type': 'stdio',
    'command': 'node',
    'args': [mcp_path],
    'env': {
        'MEMORY_SERVICE_URL': 'http://localhost:8100'
    }
}

with open(config_path, 'w') as f:
    json.dump(data, f, indent=2)

print('done')
" || die "Failed to update $CLAUDE_JSON"

    ok "Memory MCP server registered in $CLAUDE_JSON"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 8: Verify installation
# ═══════════════════════════════════════════════════════════════════════════════

verify_installation() {
    step "8: Verifying installation"
    local issues=0

    # Health endpoint
    printf "  %-35s" "Health endpoint..."
    local health_resp
    health_resp=$(curl -sf "$HEALTH_URL/health" 2>/dev/null || echo "FAIL")
    if echo "$health_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='healthy'" 2>/dev/null; then
        printf "${GREEN}healthy${NC}\n"
    else
        printf "${RED}failed${NC}\n"
        issues=$((issues + 1))
    fi

    # CRUD test — store, search, delete
    printf "  %-35s" "Memory CRUD..."
    local test_id=""
    test_id=$(curl -sf -X POST "$HEALTH_URL/memories" \
        -H "Content-Type: application/json" \
        -d '{
            "type": "learning",
            "content": "Setup verification test memory — safe to delete. This is a temporary memory created by the setup script to verify the API works correctly.",
            "tags": ["setup-test", "verification", "temporary"],
            "project": "claude-brain",
            "context": "Created by setup.sh to verify memory CRUD operations work end-to-end"
        }' 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

    if [[ -n "$test_id" && "$test_id" != "None" ]]; then
        # Cleanup — delete the test memory
        curl -sf -X DELETE "$HEALTH_URL/memories/$test_id" &>/dev/null || true
        printf "${GREEN}ok (store + delete)${NC}\n"
    else
        printf "${RED}failed${NC}\n"
        issues=$((issues + 1))
    fi

    # Scheduler
    printf "  %-35s" "Scheduler (worker)..."
    local sched_resp
    sched_resp=$(curl -sf "$HEALTH_URL/scheduler/status" 2>/dev/null || echo "FAIL")
    local job_count
    job_count=$(echo "$sched_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('jobs',[])))" 2>/dev/null || echo "0")
    if [[ "$job_count" -gt 0 ]]; then
        printf "${GREEN}$job_count jobs active${NC}\n"
    else
        printf "${YELLOW}no jobs detected${NC}\n"
    fi

    # Dashboard
    printf "  %-35s" "Dashboard..."
    local dash_code
    dash_code=$(curl -sf -o /dev/null -w "%{http_code}" "$HEALTH_URL/" 2>/dev/null || echo "000")
    if [[ "$dash_code" == "200" ]]; then
        printf "${GREEN}ok (HTTP 200)${NC}\n"
    else
        printf "${YELLOW}HTTP $dash_code${NC}\n"
    fi

    # Container count
    printf "  %-35s" "Containers..."
    local running_count
    running_count=$(cd "$MEMORY_DIR" && docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
count = 0
for line in lines:
    if line.strip():
        try:
            c = json.loads(line)
            if c.get('State') == 'running':
                count += 1
        except:
            pass
print(count)
" 2>/dev/null || echo "?")
    printf "${GREEN}${running_count}/12 running${NC}\n"

    # MCP registration
    printf "  %-35s" "MCP registration..."
    if CLAUDE_JSON="$CLAUDE_JSON" python3 -c "
import json, os
with open(os.environ['CLAUDE_JSON']) as f:
    data = json.load(f)
assert 'memory' in data.get('mcpServers', {})
" 2>/dev/null; then
        printf "${GREEN}registered${NC}\n"
    else
        printf "${RED}not found${NC}\n"
        issues=$((issues + 1))
    fi

    echo ""
    if [[ $issues -gt 0 ]]; then
        warn "$issues issue(s) detected — check logs: cd $MEMORY_DIR && docker compose logs"
    fi

    return $issues
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 9: Print summary
# ═══════════════════════════════════════════════════════════════════════════════

print_summary() {
    local has_issues=${1:-0}

    echo ""
    echo -e "${BOLD}${CYAN}"
    cat << 'BANNER'
 ═══════════════════════════════════════════════════
   Claude Brain Memory System — Setup Complete
 ═══════════════════════════════════════════════════
BANNER
    echo -e "${NC}"

    echo -e "  ${BOLD}Dashboard:${NC}   http://localhost:8100"

    # Container status
    local running
    running=$(cd "$MEMORY_DIR" && docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | grep -c '"running"' || echo "?")
    echo -e "  ${BOLD}Containers:${NC}  ${running}/12 running"

    # MCP status
    if CLAUDE_JSON="$CLAUDE_JSON" python3 -c "import json,os; d=json.load(open(os.environ['CLAUDE_JSON'])); assert 'memory' in d.get('mcpServers',{})" 2>/dev/null; then
        echo -e "  ${BOLD}MCP Server:${NC}  Registered"
    else
        echo -e "  ${BOLD}MCP Server:${NC}  ${RED}Not registered${NC}"
    fi

    # Scheduler
    local jobs
    jobs=$(curl -sf "$HEALTH_URL/scheduler/status" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('jobs',[])))" 2>/dev/null || echo "?")
    echo -e "  ${BOLD}Scheduler:${NC}   ${jobs} jobs active"

    echo ""
    echo -e "  ${BOLD}Next steps:${NC}"
    echo "    1. Restart Claude Code to enable memory tools"
    echo "    2. Use /memory-health to verify in-session"
    echo "    3. Visit http://localhost:8100 for the dashboard"

    if [[ "$has_issues" -gt 0 ]]; then
        echo ""
        echo -e "  ${YELLOW}Some checks had issues. Review the output above.${NC}"
        echo -e "  ${YELLOW}Logs: cd ~/.claude/memory && docker compose logs${NC}"
    fi

    echo ""
    echo -e "${BOLD}${CYAN} ═══════════════════════════════════════════════════${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    echo ""
    echo -e "${BOLD}${CYAN}Claude Brain Memory System — Setup${NC}"
    echo -e "───────────────────────────────────"
    echo ""

    detect_os
    check_prerequisites
    setup_repo
    setup_environment
    build_images
    start_containers
    setup_mcp_server
    register_mcp

    local issues=0
    verify_installation || issues=$?
    print_summary "$issues"

    if [[ $issues -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
