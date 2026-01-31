#!/usr/bin/env bash
set -euo pipefail

# Quick workflow launcher with tool suggestions
# Usage: workflow-macros.sh <workflow-name>
# Based on CLAUDE.md "Common Agent Chains" section

usage() {
  cat <<EOF
Usage: $(basename "$0") [WORKFLOW|--list|--help]

Quick reference for common multi-agent workflows with tool suggestions.

Workflows:
    new-feature       Complete feature implementation (6 steps)
    bug-fix          Debug and fix issues (3 steps)
    code-quality     Comprehensive quality review (4 steps)
    performance      Performance optimization (3 steps)
    security-audit   Security review and hardening (3 steps)
    api             API design and implementation (4 steps)
    frontend        Frontend feature development (4 steps)
    deploy          Deployment pipeline setup (3 steps)

Options:
    --list           Show all available workflows
    -h, --help       Show this help message

Examples:
    $(basename "$0") new-feature
    $(basename "$0") bug-fix
    $(basename "$0") --list

Output:
    Agent sequence with tool suggestions for each step
EOF
}

# Color support detection
if command -v tput &> /dev/null && [ -t 1 ]; then
  COLORS=$(tput colors 2>/dev/null || echo 0)
  if [ "$COLORS" -ge 8 ]; then
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
    CYAN=$(tput setaf 6)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    MAGENTA=$(tput setaf 5)
  else
    BOLD="" RESET="" CYAN="" GREEN="" YELLOW="" BLUE="" MAGENTA=""
  fi
else
  BOLD="" RESET="" CYAN="" GREEN="" YELLOW="" BLUE="" MAGENTA=""
fi

# Helper function to print workflow header
print_header() {
  local workflow_name="$1"
  local description="$2"
  echo ""
  echo "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo "${BOLD}${CYAN}Workflow: ${workflow_name}${RESET}"
  echo "${CYAN}${description}${RESET}"
  echo "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
}

# Helper function to print agent step
print_step() {
  local step_num="$1"
  local agent_name="$2"
  local purpose="$3"
  local tools="$4"

  echo "${BOLD}${GREEN}Step ${step_num}:${RESET} ${BOLD}${agent_name}${RESET}"
  echo "  ${YELLOW}Purpose:${RESET} ${purpose}"
  echo "  ${BLUE}Tools:${RESET} ${tools}"
  echo ""
}

# Handle flags
case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  --list)
    echo ""
    echo "${BOLD}Available Workflows:${RESET}"
    echo ""
    echo "  ${GREEN}new-feature${RESET}      - Complete feature implementation (architect → backend → security → frontend → test → deploy)"
    echo "  ${GREEN}bug-fix${RESET}          - Debug and fix issues (debugger → fix → test)"
    echo "  ${GREEN}code-quality${RESET}     - Comprehensive quality review (refactor + security + performance → test → review)"
    echo "  ${GREEN}performance${RESET}      - Performance optimization (profiler → optimize → validate)"
    echo "  ${GREEN}security-audit${RESET}   - Security review and hardening (security → code review → infrastructure)"
    echo "  ${GREEN}api${RESET}              - API design and implementation (designer → backend → tester → documenter)"
    echo "  ${GREEN}frontend${RESET}         - Frontend feature development (ui-designer → frontend → accessibility → test)"
    echo "  ${GREEN}deploy${RESET}           - Deployment pipeline setup (deployment → security → observability)"
    echo ""
    echo "Run: ${CYAN}$(basename "$0") <workflow-name>${RESET} for detailed agent sequence"
    echo ""
    exit 0
    ;;
esac

# Validate workflow argument
if [ $# -eq 0 ]; then
  echo "Error: Workflow name required" >&2
  echo ""
  usage
  exit 2
fi

WORKFLOW="$1"

# Display workflow details
case "$WORKFLOW" in
  new-feature)
    print_header "New Feature Implementation" "Full-stack feature development with security and testing"

    print_step "1" "code-architect" "Design system architecture and folder structure" \
      "All tools (Read, Write, Edit, MultiEdit, Bash, Grep, Glob, WebSearch, WebFetch, Task)"

    print_step "2" "backend-architect" "Implement server-side logic and APIs" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "3" "security-practice-reviewer" "Security audit and vulnerability scanning" \
      "Read, Grep, Glob, Bash, WebSearch + secret-scanner.py, vuln-checker.sh"

    print_step "4" "frontend-developer" "Build UI components and state management" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "5" "test-engineer" "Comprehensive testing (unit/integration/E2E)" \
      "Bash, Read, Write, Grep, MultiEdit"

    print_step "6" "deployment-engineer" "Setup CI/CD and deployment pipeline" \
      "Write, Read, MultiEdit, Bash, Grep"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (each step depends on previous)"
    echo "${MAGENTA}Estimated Time:${RESET} 2-4 hours for medium feature"
    echo ""
    ;;

  bug-fix)
    print_header "Bug Fix Workflow" "Systematic debugging and permanent fixes"

    print_step "1" "debugger" "Root cause analysis and reproduction" \
      "Read, Edit, Bash, Grep, Glob"

    print_step "2" "backend-architect|frontend-developer" "Implement fix (choose based on bug location)" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "3" "test-engineer" "Add regression tests and verify fix" \
      "Bash, Read, Write, Grep, MultiEdit"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (debugging → fix → test)"
    echo "${MAGENTA}Estimated Time:${RESET} 30min - 2 hours depending on complexity"
    echo ""
    ;;

  code-quality)
    print_header "Code Quality Review" "Comprehensive quality and maintainability audit"

    print_step "1a" "refactoring-specialist" "Code cleanup and technical debt reduction (PARALLEL)" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "1b" "security-practice-reviewer" "Security audit (PARALLEL)" \
      "Read, Grep, Glob, Bash, WebSearch"

    print_step "1c" "performance-profiler" "Performance bottleneck analysis (PARALLEL)" \
      "Read, Bash, Grep, Glob, WebSearch"

    print_step "2" "test-engineer" "Update test suite for changes" \
      "Bash, Read, Write, Grep, MultiEdit"

    print_step "3" "code-reviewer" "Final code review and best practices check" \
      "Read, Grep, Glob, Bash"

    echo "${MAGENTA}Execution Mode:${RESET} Hybrid (parallel reviews → sequential validation)"
    echo "${MAGENTA}Estimated Time:${RESET} 1-3 hours for comprehensive review"
    echo ""
    ;;

  performance)
    print_header "Performance Optimization" "Profile, optimize, and validate performance improvements"

    print_step "1" "performance-profiler" "Identify bottlenecks and slow queries" \
      "Read, Bash, Grep, Glob, WebSearch"

    print_step "2" "backend-architect|frontend-developer" "Implement optimizations (choose based on bottleneck)" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "3" "performance-profiler" "Validate improvements with benchmarks" \
      "Read, Bash, Grep, Glob"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (profile → optimize → validate)"
    echo "${MAGENTA}Estimated Time:${RESET} 1-4 hours depending on complexity"
    echo ""
    ;;

  security-audit)
    print_header "Security Audit & Hardening" "Comprehensive security review and remediation"

    print_step "1" "security-practice-reviewer" "Vulnerability scanning and compliance check" \
      "Read, Grep, Glob, Bash, WebSearch + secret-scanner.py, vuln-checker.sh"

    print_step "2" "code-reviewer" "Code quality and security best practices audit" \
      "Read, Grep, Glob, Bash"

    print_step "3" "infrastructure-architect" "Infrastructure security review (cloud, network)" \
      "Read, Write, Bash, Grep, WebSearch"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (app security → code review → infrastructure)"
    echo "${MAGENTA}Estimated Time:${RESET} 2-6 hours for thorough audit"
    echo ""
    ;;

  api)
    print_header "API Design & Implementation" "REST/GraphQL API development workflow"

    print_step "1" "api-designer" "Design API spec (OpenAPI/GraphQL schema)" \
      "Write, Read, MultiEdit, Bash, Grep, WebSearch"

    print_step "2" "backend-architect" "Implement API endpoints and business logic" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "3" "api-tester" "API testing and load testing" \
      "Bash, Read, Write, Grep"

    print_step "4" "codebase-documenter" "Generate API documentation" \
      "Read, Write, Bash, Grep"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (design → implement → test → document)"
    echo "${MAGENTA}Estimated Time:${RESET} 2-5 hours for complete API"
    echo ""
    ;;

  frontend)
    print_header "Frontend Feature Development" "UI/UX design and implementation"

    print_step "1" "ui-designer" "Design UI components and mockups" \
      "Write, Read, MultiEdit, Bash, WebSearch"

    print_step "2" "frontend-developer" "Implement React/Vue/Angular components" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "3" "accessibility-specialist" "WCAG compliance and accessibility audit" \
      "Read, Bash, Grep, Glob, WebSearch"

    print_step "4" "test-engineer" "E2E and component testing" \
      "Bash, Read, Write, Grep, MultiEdit"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (design → implement → accessibility → test)"
    echo "${MAGENTA}Estimated Time:${RESET} 2-4 hours for complete feature"
    echo ""
    ;;

  deploy)
    print_header "Deployment Pipeline Setup" "CI/CD and infrastructure automation"

    print_step "1" "deployment-engineer" "Setup CI/CD pipeline (Docker, Kubernetes)" \
      "Write, Read, MultiEdit, Bash, Grep"

    print_step "2" "security-practice-reviewer" "Review deployment security (secrets, permissions)" \
      "Read, Grep, Glob, Bash, WebSearch"

    print_step "3" "observability-engineer" "Setup logging, metrics, and monitoring" \
      "Write, Read, Bash, Grep"

    echo "${MAGENTA}Execution Mode:${RESET} Sequential (pipeline → security → observability)"
    echo "${MAGENTA}Estimated Time:${RESET} 2-6 hours for complete setup"
    echo ""
    ;;

  *)
    echo "Error: Unknown workflow '$WORKFLOW'" >&2
    echo ""
    echo "Available workflows: new-feature, bug-fix, code-quality, performance, security-audit, api, frontend, deploy"
    echo "Run with --list for more details"
    exit 1
    ;;
esac

echo "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "${GREEN}Copy-paste agent names from steps above to launch workflow${RESET}"
echo "${YELLOW}Tip: Use Claude Code's Plan mode for multi-agent parallel execution${RESET}"
echo ""
