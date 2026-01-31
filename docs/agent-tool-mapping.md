# Agent-Tool Integration Mapping

**Purpose**: Define which custom tools each of the 43 agents can access based on their domain expertise and use cases.

**Tool Location**: `~/.claude/tools/`

---

## Tool Categories Overview

| Category | Tools | Total |
|----------|-------|-------|
| Security | secret-scanner.py, vuln-checker.sh, permission-auditor.py, cert-validator.sh | 4 |
| DevOps | docker-manager.sh, env-manager.py, service-health.sh, resource-monitor.py, ci-status.sh | 5 |
| Analysis | complexity-check.py, type-coverage.py, duplication-detector.py, import-analyzer.py | 4 |
| Testing | coverage-reporter.py, test-selector.py, mutation-score.sh, flakiness-detector.py | 4 |
| Data | log-analyzer.py, sql-explain.py, metrics-aggregator.py | 3 |
| Core | file-converter.py, mock-server.py, health-check.sh | 3 |

---

## Agent-to-Tool Mappings

### Security & Code Quality Agents

#### security-practice-reviewer
**Tools** (8):
- `tools/security/secret-scanner.py` - Scan code for exposed secrets
- `tools/security/vuln-checker.sh` - Check dependencies for vulnerabilities
- `tools/security/permission-auditor.py` - Audit file permissions
- `tools/security/cert-validator.sh` - Validate SSL/TLS certificates
- `tools/devops/env-manager.py` - Validate .env files for secrets
- `tools/analysis/complexity-check.py` - Identify overly complex code (security risk)
- `tools/core/file-converter.py` - Convert config formats
- `tools/core/health-check.sh` - Validate tool ecosystem

**Primary Use Cases**: Security audits, vulnerability scanning, secrets detection

---

#### code-reviewer
**Tools** (9):
- `tools/security/secret-scanner.py` - Check for committed secrets
- `tools/analysis/complexity-check.py` - Cyclomatic complexity analysis
- `tools/analysis/type-coverage.py` - Type annotation coverage
- `tools/analysis/duplication-detector.py` - Find duplicate code
- `tools/analysis/import-analyzer.py` - Detect circular imports
- `tools/testing/coverage-reporter.py` - Analyze test coverage
- `tools/testing/mutation-score.sh` - Validate test quality
- `tools/core/file-converter.py` - Format conversion
- `tools/core/health-check.sh` - Ecosystem validation

**Primary Use Cases**: Code quality review, best practices enforcement

---

#### refactoring-specialist
**Tools** (6):
- `tools/analysis/complexity-check.py` - Identify refactoring targets
- `tools/analysis/type-coverage.py` - Improve type safety
- `tools/analysis/duplication-detector.py` - Eliminate duplicate code
- `tools/analysis/import-analyzer.py` - Resolve circular dependencies
- `tools/testing/coverage-reporter.py` - Ensure refactored code is tested
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Code cleanup, technical debt reduction

---

### DevOps & Infrastructure Agents

#### deployment-engineer
**Tools** (10):
- `tools/security/vuln-checker.sh` - Pre-deployment security scan
- `tools/security/permission-auditor.py` - Audit deployed file permissions
- `tools/security/cert-validator.sh` - Validate SSL certificates
- `tools/devops/docker-manager.sh` - Manage Docker containers/images
- `tools/devops/env-manager.py` - Validate environment configurations
- `tools/devops/service-health.sh` - Health check deployed services
- `tools/devops/resource-monitor.py` - Monitor deployment resources
- `tools/devops/ci-status.sh` - Check CI/CD pipeline status
- `tools/core/file-converter.py` - Convert config formats
- `tools/core/health-check.sh` - Pre-deployment validation

**Primary Use Cases**: CI/CD, deployment automation, infrastructure management

---

#### infrastructure-architect
**Tools** (7):
- `tools/security/cert-validator.sh` - Infrastructure SSL validation
- `tools/devops/docker-manager.sh` - Container architecture
- `tools/devops/env-manager.py` - Infrastructure configuration
- `tools/devops/service-health.sh` - Service availability monitoring
- `tools/devops/resource-monitor.py` - Resource capacity planning
- `tools/data/metrics-aggregator.py` - Infrastructure metrics
- `tools/core/file-converter.py` - Config format conversion

**Primary Use Cases**: Cloud architecture, scaling, high availability

---

#### observability-engineer
**Tools** (6):
- `tools/devops/service-health.sh` - Service health monitoring
- `tools/devops/resource-monitor.py` - System resource tracking
- `tools/data/log-analyzer.py` - Log analysis and error detection
- `tools/data/metrics-aggregator.py` - Metrics collection and aggregation
- `tools/testing/flakiness-detector.py` - Detect unstable services
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Logging, metrics, tracing, alerting

---

### Backend & Database Agents

#### backend-architect
**Tools** (9):
- `tools/security/secret-scanner.py` - Prevent secrets in code
- `tools/security/cert-validator.sh` - API SSL validation
- `tools/devops/docker-manager.sh` - Containerization
- `tools/devops/env-manager.py` - Environment management
- `tools/devops/service-health.sh` - API health checks
- `tools/data/log-analyzer.py` - Backend error analysis
- `tools/data/sql-explain.py` - Query optimization
- `tools/core/mock-server.py` - API mocking for development
- `tools/core/file-converter.py` - Config conversion

**Primary Use Cases**: Backend services, API implementation, microservices

---

#### database-optimizer
**Tools** (5):
- `tools/data/sql-explain.py` - Query analysis and optimization
- `tools/data/log-analyzer.py` - Database error logs
- `tools/data/metrics-aggregator.py` - Database performance metrics
- `tools/devops/resource-monitor.py` - Database resource usage
- `tools/core/file-converter.py` - Config format conversion

**Primary Use Cases**: Query optimization, schema design, indexing

---

#### api-designer
**Tools** (5):
- `tools/security/cert-validator.sh` - API SSL configuration
- `tools/devops/service-health.sh` - API endpoint validation
- `tools/data/log-analyzer.py` - API error analysis
- `tools/core/mock-server.py` - API mocking and prototyping
- `tools/core/file-converter.py` - API spec format conversion

**Primary Use Cases**: REST/GraphQL design, API documentation

---

### Testing & Quality Agents

#### test-engineer
**Tools** (9):
- `tools/testing/coverage-reporter.py` - Test coverage analysis
- `tools/testing/test-selector.py` - Intelligent test selection
- `tools/testing/mutation-score.sh` - Test quality validation
- `tools/testing/flakiness-detector.py` - Identify flaky tests
- `tools/devops/ci-status.sh` - CI test run status
- `tools/devops/service-health.sh` - Integration test endpoints
- `tools/data/log-analyzer.py` - Test failure logs
- `tools/core/mock-server.py` - Test mocking
- `tools/core/file-converter.py` - Test data conversion

**Primary Use Cases**: Unit/integration/E2E testing, TDD/BDD

---

#### api-tester
**Tools** (6):
- `tools/testing/coverage-reporter.py` - API test coverage
- `tools/devops/service-health.sh` - API endpoint testing
- `tools/data/log-analyzer.py` - API error logs
- `tools/data/metrics-aggregator.py` - API performance metrics
- `tools/core/mock-server.py` - API mocking
- `tools/core/file-converter.py` - Test data conversion

**Primary Use Cases**: API testing, load testing, contract testing

---

#### debugger
**Tools** (10):
- `tools/security/secret-scanner.py` - Check for leaked secrets in errors
- `tools/analysis/complexity-check.py` - Identify complex buggy code
- `tools/analysis/import-analyzer.py` - Debug circular imports
- `tools/testing/test-selector.py` - Run related tests
- `tools/testing/flakiness-detector.py` - Identify intermittent bugs
- `tools/devops/service-health.sh` - Debug service issues
- `tools/devops/resource-monitor.py` - Debug resource issues
- `tools/data/log-analyzer.py` - Error pattern analysis
- `tools/data/metrics-aggregator.py` - Anomaly detection
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Bug fixing, root cause analysis, error reproduction

---

### Language Specialists

#### python-expert
**Tools** (8):
- `tools/security/secret-scanner.py` - Python security scanning
- `tools/analysis/complexity-check.py` - Python complexity analysis
- `tools/analysis/type-coverage.py` - Python type hints coverage
- `tools/analysis/duplication-detector.py` - Duplicate Python code
- `tools/analysis/import-analyzer.py` - Python circular imports
- `tools/testing/coverage-reporter.py` - Python test coverage
- `tools/testing/mutation-score.sh` - Python mutation testing
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Advanced Python, async/await, type safety

---

#### typescript-expert
**Tools** (8):
- `tools/security/secret-scanner.py` - TypeScript security scanning
- `tools/analysis/complexity-check.py` - TypeScript complexity
- `tools/analysis/type-coverage.py` - TypeScript type coverage
- `tools/analysis/duplication-detector.py` - Duplicate TypeScript code
- `tools/analysis/import-analyzer.py` - Circular imports
- `tools/testing/coverage-reporter.py` - Test coverage
- `tools/testing/mutation-score.sh` - Mutation testing (Stryker)
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Advanced TypeScript, type system, strict types

---

### Frontend & Mobile Agents

#### frontend-developer
**Tools** (6):
- `tools/security/secret-scanner.py` - Detect exposed API keys
- `tools/analysis/complexity-check.py` - Component complexity
- `tools/analysis/duplication-detector.py` - Duplicate UI code
- `tools/devops/service-health.sh` - Frontend API health checks
- `tools/core/mock-server.py` - Mock API endpoints
- `tools/core/file-converter.py` - Config conversion

**Primary Use Cases**: React/Vue/Angular, state management, frontend apps

---

#### mobile-app-developer
**Tools** (5):
- `tools/security/secret-scanner.py` - Detect exposed keys in mobile code
- `tools/devops/service-health.sh` - Mobile backend health checks
- `tools/data/log-analyzer.py` - Mobile app crash logs
- `tools/core/mock-server.py` - Mock backend for development
- `tools/core/file-converter.py` - Config conversion

**Primary Use Cases**: iOS/Android native apps, mobile architecture

---

#### mobile-ux-optimizer
**Tools** (4):
- `tools/analysis/complexity-check.py` - UI component complexity
- `tools/data/metrics-aggregator.py` - UX performance metrics
- `tools/devops/service-health.sh` - API response times
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Mobile-first UX, responsive design

---

### Performance & Optimization Agents

#### performance-profiler
**Tools** (8):
- `tools/analysis/complexity-check.py` - Identify performance hotspots
- `tools/devops/resource-monitor.py` - Real-time resource profiling
- `tools/devops/service-health.sh` - Response time measurement
- `tools/data/log-analyzer.py` - Performance error logs
- `tools/data/sql-explain.py` - Database query performance
- `tools/data/metrics-aggregator.py` - Performance metrics aggregation
- `tools/testing/flakiness-detector.py` - Performance-related flakiness
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Bottleneck identification, optimization, profiling

---

### Data & Analytics Agents

#### data-scientist
**Tools** (5):
- `tools/data/log-analyzer.py` - Data pipeline log analysis
- `tools/data/sql-explain.py` - Query optimization for analytics
- `tools/data/metrics-aggregator.py` - Data metrics aggregation
- `tools/testing/coverage-reporter.py` - Data pipeline test coverage
- `tools/core/file-converter.py` - Data format conversion

**Primary Use Cases**: Data analysis, SQL queries, insights extraction

---

#### analytics-engineer
**Tools** (5):
- `tools/data/log-analyzer.py` - Analytics event logs
- `tools/data/metrics-aggregator.py` - Event metrics aggregation
- `tools/devops/service-health.sh` - Analytics endpoint health
- `tools/testing/coverage-reporter.py` - Analytics test coverage
- `tools/core/file-converter.py` - Event data conversion

**Primary Use Cases**: Event tracking, analytics pipelines, conversion tracking

---

#### visualization-dashboard-builder
**Tools** (4):
- `tools/data/log-analyzer.py` - Dashboard error logs
- `tools/data/metrics-aggregator.py` - Dashboard data aggregation
- `tools/devops/service-health.sh` - Data source health checks
- `tools/core/file-converter.py` - Data format conversion

**Primary Use Cases**: Interactive dashboards, KPIs, real-time monitoring

---

### AI & Specialized Agents

#### ai-engineer
**Tools** (6):
- `tools/security/secret-scanner.py` - Detect API keys for AI services
- `tools/data/log-analyzer.py` - AI model error logs
- `tools/data/metrics-aggregator.py` - Model performance metrics
- `tools/devops/resource-monitor.py` - GPU/CPU resource monitoring
- `tools/testing/coverage-reporter.py` - ML pipeline test coverage
- `tools/core/file-converter.py` - Model config conversion

**Primary Use Cases**: AI/ML features, LLM integration, recommendation systems

---

#### ai-prompt-engineer
**Tools** (4):
- `tools/security/secret-scanner.py` - Detect API keys in prompts
- `tools/data/log-analyzer.py` - LLM error analysis
- `tools/data/metrics-aggregator.py` - Prompt performance metrics
- `tools/core/file-converter.py` - Prompt template conversion

**Primary Use Cases**: LLM prompt optimization, multi-step workflows

---

### Documentation & Content Agents

#### technical-writer
**Tools** (3):
- `tools/analysis/complexity-check.py` - Document complex code sections
- `tools/core/file-converter.py` - Documentation format conversion
- `tools/core/health-check.sh` - Validate documented tools

**Primary Use Cases**: Technical docs, API docs, tutorials

---

#### content-marketing-specialist
**Tools** (2):
- `tools/data/metrics-aggregator.py` - Content performance metrics
- `tools/core/file-converter.py` - Content format conversion

**Primary Use Cases**: Marketing copy, blogs, campaigns

---

#### codebase-documenter
**Tools** (6):
- `tools/security/secret-scanner.py` - Document security practices
- `tools/analysis/complexity-check.py` - Document complex modules
- `tools/analysis/import-analyzer.py` - Document dependencies
- `tools/data/sql-explain.py` - Document database queries
- `tools/core/health-check.sh` - Document tool ecosystem
- `tools/core/file-converter.py` - Format conversion

**Primary Use Cases**: Service documentation, CLAUDE.md files

---

### Specialized Domain Agents

#### game-developer
**Tools** (4):
- `tools/analysis/complexity-check.py` - Game logic complexity
- `tools/devops/resource-monitor.py` - Game performance monitoring
- `tools/testing/coverage-reporter.py` - Game logic test coverage
- `tools/core/file-converter.py` - Game asset conversion

**Primary Use Cases**: Game mechanics, physics, graphics programming

---

#### blockchain-developer
**Tools** (5):
- `tools/security/secret-scanner.py` - Detect exposed private keys
- `tools/security/vuln-checker.sh` - Smart contract vulnerabilities
- `tools/testing/coverage-reporter.py` - Smart contract test coverage
- `tools/devops/service-health.sh` - Blockchain node health
- `tools/core/file-converter.py` - Config conversion

**Primary Use Cases**: Smart contracts, DeFi, Web3

---

#### trading-bot-strategist
**Tools** (5):
- `tools/data/log-analyzer.py` - Trading bot error logs
- `tools/data/metrics-aggregator.py` - Trading performance metrics
- `tools/devops/service-health.sh` - Exchange API health checks
- `tools/testing/flakiness-detector.py` - Detect unreliable strategies
- `tools/core/file-converter.py` - Strategy config conversion

**Primary Use Cases**: Algorithmic trading, backtesting, risk management

---

### Remaining Agents (Universal Tools Only)

These agents primarily use the universal core utilities:

- **code-architect**: health-check.sh, file-converter.py
- **ui-designer**: file-converter.py
- **ux-researcher**: metrics-aggregator.py, file-converter.py
- **desktop-app-developer**: resource-monitor.py, file-converter.py
- **seo-specialist**: service-health.sh, metrics-aggregator.py, file-converter.py
- **accessibility-specialist**: complexity-check.py, file-converter.py
- **migration-specialist**: duplication-detector.py, import-analyzer.py, file-converter.py
- **localization-specialist**: file-converter.py
- **growth-hacker**: metrics-aggregator.py, log-analyzer.py, file-converter.py
- **finance-tracker**: metrics-aggregator.py, file-converter.py
- **math-checker**: file-converter.py
- **trend-researcher**: metrics-aggregator.py, log-analyzer.py, file-converter.py
- **visual-storyteller**: file-converter.py
- **context7-docs-fetcher**: file-converter.py

---

## Usage Instructions for Agents

### How Agents Should Invoke Tools

**Bash tool pattern**:
```bash
~/.claude/tools/devops/docker-manager.sh list-containers
~/.claude/tools/security/vuln-checker.sh package.json
```

**Python tool pattern**:
```bash
python3 ~/.claude/tools/analysis/complexity-check.py /path/to/code
python3 ~/.claude/tools/testing/coverage-reporter.py coverage.xml
```

### Tool Output Format

All tools return standardized JSON:
```json
{
  "success": true,
  "data": {},
  "errors": [],
  "metadata": {
    "tool": "tool-name",
    "version": "1.0.0",
    "timestamp": "2025-11-06T12:00:00Z"
  }
}
```

### Error Handling

Agents should:
1. Check `success` field before processing `data`
2. Log errors from `errors` array
3. Handle missing optional dependencies gracefully (tools have fallbacks)

---

## Tool Access Summary by Agent Count

| Tool | Agent Count | Most Common Use Case |
|------|-------------|----------------------|
| file-converter.py | 43 | Universal format conversion |
| health-check.sh | 8 | Ecosystem validation |
| secret-scanner.py | 12 | Security scanning |
| complexity-check.py | 11 | Code quality analysis |
| log-analyzer.py | 12 | Error analysis |
| metrics-aggregator.py | 11 | Performance metrics |
| service-health.sh | 13 | API/service health checks |
| resource-monitor.py | 7 | Resource profiling |
| coverage-reporter.py | 9 | Test coverage |
| sql-explain.py | 4 | Database optimization |
| mock-server.py | 5 | API mocking |
| type-coverage.py | 5 | Type safety |
| duplication-detector.py | 5 | Code deduplication |
| import-analyzer.py | 6 | Dependency analysis |
| test-selector.py | 3 | Intelligent test selection |
| flakiness-detector.py | 5 | Stability detection |
| mutation-score.sh | 4 | Test quality |
| vuln-checker.sh | 3 | Vulnerability scanning |
| permission-auditor.py | 3 | Permission auditing |
| cert-validator.sh | 5 | SSL/TLS validation |
| docker-manager.sh | 4 | Container management |
| env-manager.py | 5 | Environment validation |
| ci-status.sh | 2 | CI/CD monitoring |

---

## Integration Workflow

1. **Agent receives task** from user or coordinator
2. **Agent identifies relevant tools** from its available tool list
3. **Agent invokes tool** using Bash command
4. **Agent parses JSON output** and acts on results
5. **Agent logs tool usage** in PROJECT_CONTEXT.md if coordination required

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Total Tools**: 23
**Total Agent Mappings**: 156 tool assignments across 43 agents
