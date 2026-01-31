#!/bin/bash
# Checks if validation tools are installed
# Usage: ./check-tools.sh

set -euo pipefail

echo "🔍 Checking Validation Tools..."
echo ""

tools_available=()
tools_missing=()
warnings=0

# Check for common validation tools

# Python tools
if command -v ruff &> /dev/null; then
  version=$(ruff --version 2>/dev/null | head -n1 || echo "unknown")
  tools_available+=("ruff ($version)")
else
  tools_missing+=("ruff")
fi

if command -v mypy &> /dev/null; then
  version=$(mypy --version 2>/dev/null | head -n1 || echo "unknown")
  tools_available+=("mypy ($version)")
else
  tools_missing+=("mypy")
fi

if command -v pytest &> /dev/null; then
  version=$(pytest --version 2>/dev/null | head -n1 || echo "unknown")
  tools_available+=("pytest ($version)")
else
  tools_missing+=("pytest")
fi

if command -v black &> /dev/null; then
  version=$(black --version 2>/dev/null | head -n1 || echo "unknown")
  tools_available+=("black ($version)")
else
  tools_missing+=("black")
fi

# JavaScript/TypeScript tools
if command -v tsc &> /dev/null; then
  version=$(tsc --version 2>/dev/null || echo "unknown")
  tools_available+=("tsc ($version)")
else
  # Not critical, only needed for TS projects
  warnings=$((warnings + 1))
fi

if command -v eslint &> /dev/null; then
  version=$(eslint --version 2>/dev/null || echo "unknown")
  tools_available+=("eslint ($version)")
else
  # Not critical, only needed for JS/TS projects
  warnings=$((warnings + 1))
fi

if command -v prettier &> /dev/null; then
  version=$(prettier --version 2>/dev/null || echo "unknown")
  tools_available+=("prettier ($version)")
else
  # Not critical, only needed for JS/TS projects
  warnings=$((warnings + 1))
fi

# Shell tools
if command -v shellcheck &> /dev/null; then
  version=$(shellcheck --version 2>/dev/null | grep "version:" | cut -d' ' -f2 || echo "unknown")
  tools_available+=("shellcheck ($version)")
else
  tools_missing+=("shellcheck")
fi

# Git (essential)
if command -v git &> /dev/null; then
  version=$(git --version 2>/dev/null || echo "unknown")
  tools_available+=("git ($version)")
else
  echo "❌ git is not installed (CRITICAL - required for version control)"
  exit 1
fi

# Print results
if [ ${#tools_available[@]} -gt 0 ]; then
  echo "✅ Available tools:"
  for tool in "${tools_available[@]}"; do
    echo "   • $tool"
  done
  echo ""
fi

if [ ${#tools_missing[@]} -gt 0 ]; then
  echo "⚠️  Missing tools (recommended):"
  for tool in "${tools_missing[@]}"; do
    echo "   • $tool"
  done
  echo ""
  echo "📦 Install missing tools:"
  echo ""
  echo "   Python tools:"
  echo "   pip install ruff mypy pytest black"
  echo ""
  echo "   Shell tools (macOS):"
  echo "   brew install shellcheck"
  echo ""
  echo "   Shell tools (Linux):"
  echo "   apt-get install shellcheck  # Debian/Ubuntu"
  echo "   yum install shellcheck       # RHEL/CentOS"
  echo ""
fi

# Summary
total_critical=${#tools_missing[@]}
total_available=${#tools_available[@]}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $total_critical -eq 0 ]; then
  echo "✅ All essential validation tools available"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo "⚠️  $total_critical tools missing (validation may be limited)"
  echo "   $total_available tools available"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "ℹ️  You can still proceed, but validation coverage will be reduced."
  echo "   Install missing tools for comprehensive validation."
  exit 0  # Non-critical - don't fail workflow
fi
