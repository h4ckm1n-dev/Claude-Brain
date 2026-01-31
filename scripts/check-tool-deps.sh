#!/usr/bin/env bash
# Purpose: Check both required and optional dependencies for all tools
# Usage: ./check-tool-deps.sh [--help]
# Exit codes: 0=all required deps present, 1=required deps missing

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat << 'EOF'
check-tool-deps.sh - Check tool dependencies

SYNOPSIS:
    check-tool-deps.sh [--help]

DESCRIPTION:
    Checks both required and optional dependencies for all Claude Code tools.
    Required dependencies are essential for basic operation.
    Optional dependencies enable specific tools and features.

EXIT CODES:
    0  - All required dependencies present (optional missing = warnings only)
    1  - One or more required dependencies missing

EXAMPLES:
    # Check all dependencies
    ./check-tool-deps.sh

    # Output:
    # Checking tool dependencies...
    #
    # ✅ Python 3.11.5
    #   ✅ psutil (resource-monitor.py)
    #   ⚠️  radon missing (pip install radon)
    #
    # ✅ Bash 3.2
    # ✅ Git 2.42
    #
    # Summary: 2 optional dependencies missing
    # Install: pip install radon && npm install -g jscpd

EOF
    exit 0
}

# Parse arguments
if [ $# -gt 0 ]; then
    case "$1" in
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
fi

# Track missing dependencies
required_missing=()
optional_missing=()
pip_install_cmds=()
npm_install_cmds=()

echo "Checking tool dependencies..."
echo ""

# Check command exists
check_command() {
    local cmd="$1"
    command -v "$cmd" &> /dev/null
}

# Check Python package
check_python_package() {
    local package="$1"
    python3 -c "import ${package}" 2>/dev/null
}

# ============================================================================
# REQUIRED DEPENDENCIES
# ============================================================================

echo "Required Dependencies:"
echo ""

# Python 3
if check_command python3; then
    python_version=$(python3 --version 2>&1 | sed 's/Python //')
    echo -e "${GREEN}✅${NC} Python $python_version"

    # Check Python optional packages
    if check_python_package psutil; then
        echo "  ✅ psutil (resource-monitor.py)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  psutil missing (pip install psutil)"
        optional_missing+=("psutil")
        pip_install_cmds+=("psutil")
    fi

    if check_python_package radon; then
        echo "  ✅ radon (complexity-check.py)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  radon missing (pip install radon)"
        optional_missing+=("radon")
        pip_install_cmds+=("radon")
    fi

    if check_python_package safety; then
        echo "  ✅ safety (vuln-checker.sh)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  safety missing (pip install safety)"
        optional_missing+=("safety")
        pip_install_cmds+=("safety")
    fi

    echo ""
else
    echo -e "${RED}❌${NC} Python 3 not found (REQUIRED)"
    required_missing+=("python3 (>=3.8)")
    echo ""
fi

# Bash
if check_command bash; then
    bash_version=$(bash --version | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo -e "${GREEN}✅${NC} Bash $bash_version"
    echo ""
else
    echo -e "${RED}❌${NC} Bash not found (REQUIRED)"
    required_missing+=("bash")
    echo ""
fi

# Git
if check_command git; then
    git_version=$(git --version | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?')
    echo -e "${GREEN}✅${NC} Git $git_version"
    echo ""
else
    echo -e "${RED}❌${NC} Git not found (REQUIRED)"
    required_missing+=("git")
    echo ""
fi

# ============================================================================
# OPTIONAL DEPENDENCIES
# ============================================================================

echo "Optional Dependencies:"
echo ""

# Node.js/npm tools
if check_command node && check_command npm; then
    node_version=$(node --version | tr -d 'v')
    echo -e "${GREEN}✅${NC} Node.js $node_version"

    if check_command jscpd; then
        echo "  ✅ jscpd (duplication-detector.py)"
    else
        echo -e "  ${YELLOW}⚠️${NC}  jscpd missing (npm install -g jscpd)"
        optional_missing+=("jscpd")
        npm_install_cmds+=("jscpd")
    fi

    echo ""
else
    echo -e "${YELLOW}⚠️${NC}  Node.js/npm not found"
    echo "  ⚠️  jscpd unavailable (npm install -g jscpd)"
    optional_missing+=("node/npm")
    npm_install_cmds+=("jscpd")
    echo ""
fi

# Mutation testing tools
if check_command mutmut; then
    echo -e "${GREEN}✅${NC} mutmut (mutation-score.sh)"
else
    echo -e "${YELLOW}⚠️${NC}  mutmut missing (pip install mutmut)"
    optional_missing+=("mutmut")
    pip_install_cmds+=("mutmut")
fi

if check_command stryker; then
    echo -e "${GREEN}✅${NC} stryker (mutation-score.sh)"
else
    echo -e "${YELLOW}⚠️${NC}  stryker missing (npm install -g stryker-cli)"
    optional_missing+=("stryker")
    npm_install_cmds+=("stryker-cli")
fi

echo ""

# ShellCheck
if check_command shellcheck; then
    shellcheck_version=$(shellcheck --version | grep "^version:" | awk '{print $2}')
    echo -e "${GREEN}✅${NC} shellcheck $shellcheck_version (bash validation)"
else
    echo -e "${YELLOW}⚠️${NC}  shellcheck missing (brew install shellcheck)"
    optional_missing+=("shellcheck")
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#required_missing[@]} -gt 0 ]; then
    echo -e "${RED}❌ ${#required_missing[@]} required dependencies missing${NC}"
    echo ""
    echo "Missing required:"
    for dep in "${required_missing[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Install required dependencies before proceeding."
    exit 1
fi

if [ ${#optional_missing[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Summary: ${#optional_missing[@]} optional dependencies missing${NC}"
    echo ""

    # Build install commands
    install_cmds=()

    if [ ${#pip_install_cmds[@]} -gt 0 ]; then
        pip_cmd="pip install ${pip_install_cmds[*]}"
        install_cmds+=("$pip_cmd")
    fi

    if [ ${#npm_install_cmds[@]} -gt 0 ]; then
        npm_cmd="npm install -g ${npm_install_cmds[*]}"
        install_cmds+=("$npm_cmd")
    fi

    # Add shellcheck if missing
    if [[ " ${optional_missing[*]} " =~ " shellcheck " ]]; then
        install_cmds+=("brew install shellcheck")
    fi

    if [ ${#install_cmds[@]} -gt 0 ]; then
        echo "Install commands:"
        for cmd in "${install_cmds[@]}"; do
            echo "  $cmd"
        done
    fi

    echo ""
    echo "ℹ️  Tools will work with reduced functionality."
    echo "   Install optional dependencies for full feature set."
else
    echo -e "${GREEN}✅ All dependencies available (required + optional)${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
