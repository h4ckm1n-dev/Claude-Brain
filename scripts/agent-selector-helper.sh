#!/usr/bin/env bash
# Interactive agent selection helper
# Usage: ./agent-selector-helper.sh

set -euo pipefail

echo "🤖 Agent Selector Helper"
echo "========================"
echo ""
echo "Answer a few questions to find the right agent(s):"
echo ""

# Question 1: Domain
echo "1. What are you building?"
echo "   a) API or backend logic"
echo "   b) User interface / frontend"
echo "   c) Tests"
echo "   d) Infrastructure / deployment"
echo "   e) Data analysis / analytics"
echo "   f) AI/ML features"
echo "   g) Security review"
echo "   h) Performance optimization"
echo "   i) Bug fixing"
echo "   j) Code refactoring"
echo "   k) Other"
read -rp "Your choice (a-k): " domain

# Question 2: Scope
echo ""
echo "2. What's the scope?"
echo "   a) New feature (architecture needed)"
echo "   b) Modify existing code"
echo "   c) Fix a bug"
echo "   d) Optimize performance"
echo "   e) Review/audit code"
read -rp "Your choice (a-e): " scope

# Question 3: Complexity
echo ""
echo "3. How many files will be affected?"
echo "   a) Single file, <10 lines"
echo "   b) 1-3 files"
echo "   c) 3+ files or multiple modules"
read -rp "Your choice (a-c): " complexity

# Suggest agents
echo ""
echo "📋 Recommended Agents:"
echo ""

case "$domain" in
  a)
    echo "🔧 Backend Development:"
    if [[ "$scope" == "a" ]]; then
      echo "  1. code-architect - Start here for new features (system design)"
      echo "  2. api-designer - Create REST/GraphQL API specifications"
      echo "  3. backend-architect - Implement server-side logic, databases"
      echo ""
      echo "  Workflow: code-architect → api-designer → backend-architect → test-engineer"
    else
      echo "  - backend-architect: Server-side logic, APIs, databases"
      echo "  - database-optimizer: Query optimization, schema design"
    fi
    ;;
  b)
    echo "🎨 Frontend Development:"
    if [[ "$scope" == "a" ]]; then
      echo "  1. ui-designer - Design system and mockups first"
      echo "  2. frontend-developer - Implement UI components"
      echo "  3. test-engineer - Create frontend tests"
      echo ""
      echo "  Workflow: ui-designer → frontend-developer → test-engineer"
    else
      echo "  - frontend-developer: UI components, state management"
      echo "  - ux-researcher: User experience analysis"
      echo "  - accessibility-specialist: WCAG compliance"
    fi
    ;;
  c)
    echo "🧪 Testing:"
    echo "  - test-engineer: Unit, integration, E2E tests"
    echo "  - api-tester: API testing specifically"
    if [[ "$complexity" == "c" ]]; then
      echo "  - code-architect: Test strategy for complex systems"
    fi
    ;;
  d)
    echo "🚀 Infrastructure:"
    if [[ "$scope" == "a" ]]; then
      echo "  1. infrastructure-architect - Cloud architecture design"
      echo "  2. deployment-engineer - CI/CD implementation"
      echo "  3. observability-engineer - Monitoring setup"
    else
      echo "  - deployment-engineer: CI/CD, Docker, Kubernetes"
      echo "  - infrastructure-architect: Cloud architecture"
    fi
    ;;
  e)
    echo "📊 Data & Analytics:"
    echo "  - data-scientist: Data analysis, SQL, BigQuery"
    echo "  - analytics-engineer: Event tracking, analytics systems"
    echo "  - visualization-dashboard-builder: Interactive dashboards"
    echo "  - database-optimizer: Query optimization"
    ;;
  f)
    echo "🤖 AI & Machine Learning:"
    echo "  - ai-engineer: ML features, LLM integration"
    echo "  - ai-prompt-engineer: Prompt optimization"
    if [[ "$scope" == "a" ]]; then
      echo "  - code-architect: AI system architecture"
    fi
    ;;
  g)
    echo "🔒 Security:"
    echo "  - security-practice-reviewer: Security audits, vulnerability scanning"
    echo "  - code-reviewer: Code quality and security review"
    ;;
  h)
    echo "⚡ Performance:"
    echo "  - performance-profiler: Performance bottlenecks, optimization"
    echo "  - database-optimizer: Query optimization"
    if [[ "$scope" == "e" ]]; then
      echo "  - code-reviewer: Performance code review"
    fi
    ;;
  i)
    echo "🐛 Bug Fixing:"
    echo "  - debugger: Systematic debugging, root cause analysis"
    if [[ "$complexity" == "c" ]]; then
      echo "  - code-architect: System-wide bug investigation"
    fi
    ;;
  j)
    echo "🔄 Code Refactoring:"
    echo "  - refactoring-specialist: Code cleanup, technical debt"
    echo "  - code-reviewer: Quality review after refactoring"
    if [[ "$scope" == "a" ]]; then
      echo "  - code-architect: Architectural refactoring"
    fi
    ;;
  k)
    echo "💡 Other Specialized Agents:"
    echo "  - mobile-app-developer: iOS/Android apps"
    echo "  - game-developer: Game development"
    echo "  - blockchain-developer: Web3, smart contracts"
    echo "  - content-marketing-specialist: Marketing content"
    echo "  - technical-writer: Documentation"
    echo "  - seo-specialist: SEO optimization"
    ;;
esac

echo ""
echo "💡 Tips:"
echo "  - For trivial changes (<10 lines, single file): Work directly without agent"
echo "  - For complex features (3+ files): Always use specialized agent"
echo "  - Use code-architect first for new features requiring architecture"
echo ""
echo "📚 More Information:"
echo "  - Keyword triggers: ~/.claude/CLAUDE.md (auto-agent-selection)"
echo "  - All 42 agents: ~/.claude/CLAUDE.md (full list with capabilities)"
echo "  - Agent definitions: ~/.claude/agents/*.md"
echo ""
echo "🔍 Keyword Shortcuts:"
echo "  API/REST/GraphQL → api-designer or backend-architect"
echo "  frontend/UI/React → frontend-developer"
echo "  test/testing/TDD → test-engineer"
echo "  deploy/CI/CD/Docker → deployment-engineer"
echo "  slow/optimize/performance → performance-profiler"
echo "  security/vulnerability/auth → security-practice-reviewer"
echo "  refactor/technical debt → refactoring-specialist"
echo "  bug/error/broken → debugger"
echo ""
exit 0
