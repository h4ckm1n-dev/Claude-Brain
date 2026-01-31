# Multi-Agent Workflow Examples

Detailed examples for common multi-agent coordination patterns.

**Reference**: These examples are extracted from CLAUDE.md to keep the main documentation concise. For quick workflow overviews, see the [Multi-Agent Workflows section in CLAUDE.md](../CLAUDE.md#-multi-agent-workflows).

---

## Workflow 1: Full-Stack Feature Development
**Scenario**: User authentication with OAuth
**Duration**: 4-6 hours
**Complexity**: Medium-High

```
PHASE 1: ARCHITECTURE (Sequential - 45min)
├─ code-architect (15min)
│  ├─ Designs: System architecture, folder structure
│  ├─ Creates: /docs/architecture/auth-system.md
│  └─ Success: Clear tech stack, security model defined
│
├─ database-optimizer (15min)
│  ├─ Uses: Architecture decisions
│  ├─ Creates: /docs/database/user-schema.sql
│  └─ Success: Normalized schema, proper indexes
│
└─ api-designer (15min)
   ├─ Uses: Database schema
   ├─ Creates: /docs/api/auth.yaml (OpenAPI spec)
   └─ Success: RESTful endpoints, clear contracts

PHASE 2: IMPLEMENTATION (Sequential - 2hrs)
├─ backend-architect (60min)
│  ├─ Uses: API spec, database schema
│  ├─ Implements: Auth routes, JWT middleware
│  └─ Success: Working API, password hashing, tokens
│
└─ security-practice-reviewer (30min)
   ├─ Reviews: Backend implementation
   ├─ Checks: SQL injection, XSS, CSRF, token security
   └─ Success: No critical vulnerabilities

PHASE 3: FRONTEND (Parallel - 1.5hrs)
└─ frontend-developer (90min)
   ├─ Uses: API spec
   ├─ Builds: Login/signup forms, auth state management
   └─ Success: Working UI, error handling, loading states

PHASE 4: TESTING (Sequential - 1.5hrs)
├─ test-engineer (60min)
│  ├─ Writes: Unit tests, integration tests, E2E flows
│  └─ Success: >80% coverage, edge cases covered
│
└─ code-reviewer (30min)
   ├─ Reviews: All code changes
   └─ Success: Code quality, maintainability verified

SUCCESS CRITERIA:
✓ Users can register, login, logout
✓ JWT tokens work correctly
✓ Passwords are hashed
✓ No security vulnerabilities
✓ Tests pass
✓ Code reviewed and approved

COMMON PITFALLS:
✗ Skipping security review → SQL injection, weak tokens
✗ No test coverage → Broken auth in production
✗ Missing error handling → Poor UX on failures
```

---

## Workflow 2: Production Deployment
**Scenario**: Deploy Node.js app to Kubernetes
**Duration**: 3-4 hours
**Complexity**: High

```
PHASE 1: DEPLOYMENT SETUP (Sequential - 90min)
└─ deployment-engineer (90min)
   ├─ Creates: Dockerfile, K8s manifests, CI/CD pipeline
   ├─ Files: /k8s/*.yaml, /.github/workflows/deploy.yml
   └─ Success: Clean builds, automated deployments

PHASE 2: SECURITY & OBSERVABILITY (Parallel - 90min)
├─ security-practice-reviewer (45min)
│  ├─ Reviews: Container security, secrets, network policies
│  └─ Success: Hardened containers, secure configs
│
├─ observability-engineer (45min)
│  ├─ Adds: Prometheus, Grafana, logging (ELK/Loki)
│  └─ Success: Metrics, logs, alerts configured
│
└─ performance-profiler (45min)
   ├─ Sets up: APM, resource limits, auto-scaling
   └─ Success: Performance baselines established

PHASE 3: VALIDATION (Sequential - 45min)
└─ test-engineer (45min)
   ├─ Runs: Smoke tests, load tests in staging
   └─ Success: Staging environment verified

SUCCESS CRITERIA:
✓ Application deploys successfully
✓ Health checks pass
✓ Monitoring shows green metrics
✓ Load tests show acceptable performance
✓ Security scan passes
✓ Rollback plan tested

COMMON PITFALLS:
✗ No health checks → Pod restart loops
✗ Missing resource limits → OOM kills
✗ No monitoring → Can't diagnose production issues
✗ Secrets in code → Security breach
```

---

## Workflow 3: AI Chatbot with RAG
**Scenario**: Add intelligent chatbot
**Duration**: 5-7 hours
**Complexity**: High

```
PHASE 1: AI ARCHITECTURE (Sequential - 90min)
├─ ai-engineer (60min)
│  ├─ Designs: RAG pipeline, vector DB, embeddings
│  ├─ Creates: /docs/architecture/rag-system.md
│  └─ Success: Clear data flow, model selection
│
└─ ai-prompt-engineer (30min)
   ├─ Creates: System prompts, few-shot examples
   ├─ Files: /src/prompts/chatbot-prompts.ts
   └─ Success: Consistent, high-quality responses

PHASE 2: BACKEND & DATA (Parallel - 2hrs)
├─ backend-architect (90min)
│  ├─ Builds: Chat API, streaming endpoints
│  └─ Success: Working chat interface
│
└─ database-optimizer (90min)
   ├─ Sets up: Pinecone/Weaviate, embedding pipeline
   └─ Success: Fast vector search

PHASE 3: FRONTEND (Sequential - 90min)
└─ frontend-developer (90min)
   ├─ Builds: Chat UI, streaming responses, history
   └─ Success: Smooth UX, typing indicators

PHASE 4: OPTIMIZATION & TESTING (Parallel - 2hrs)
├─ performance-profiler (60min)
│  ├─ Optimizes: Response time, caching, rate limits
│  └─ Success: <2s response time
│
└─ test-engineer (60min)
   ├─ Tests: AI responses, edge cases, fallbacks
   └─ Success: Graceful error handling

SUCCESS CRITERIA:
✓ Chatbot responds accurately to queries
✓ Context is retrieved correctly
✓ Response time <2 seconds
✓ Streaming works smoothly
✓ Handles edge cases gracefully
✓ Costs are monitored

COMMON PITFALLS:
✗ Poor prompt engineering → Inconsistent responses
✗ No caching → High costs, slow responses
✗ No rate limiting → API quota exhaustion
✗ Bad chunk strategy → Irrelevant context
```

---

## Workflow 4: Code Quality Sprint
**Scenario**: Improve legacy codebase
**Duration**: 4-6 hours
**Complexity**: Medium

```
PHASE 1: ANALYSIS (Parallel - 2hrs)
├─ refactoring-specialist (90min)
│  ├─ Analyzes: Code smells, design patterns needed
│  └─ Success: Refactoring plan created
│
├─ security-practice-reviewer (60min)
│  ├─ Scans: Vulnerabilities, insecure patterns
│  └─ Success: Security issues documented
│
├─ performance-profiler (60min)
│  ├─ Profiles: Bottlenecks, memory leaks
│  └─ Success: Optimization targets identified
│
└─ accessibility-specialist (45min)
   ├─ Audits: WCAG compliance, keyboard nav
   └─ Success: A11y issues documented

PHASE 2: IMPROVEMENTS (Sequential - 3hrs)
├─ refactoring-specialist (2hrs)
│  ├─ Refactors: Based on all findings
│  └─ Success: Cleaner, more maintainable code
│
└─ test-engineer (60min)
   ├─ Adds: Missing test coverage
   └─ Success: >70% coverage

PHASE 3: VALIDATION (Sequential - 45min)
├─ code-reviewer (30min)
│  └─ Success: All changes meet standards
│
└─ codebase-documenter (15min)
   └─ Success: Documentation updated

SUCCESS CRITERIA:
✓ Code complexity reduced
✓ Security vulnerabilities fixed
✓ Performance improved by 20%+
✓ Accessibility issues resolved
✓ Test coverage >70%
✓ Documentation current

COMMON PITFALLS:
✗ Too aggressive refactoring → Breaking changes
✗ No tests before refactoring → Regression bugs
✗ Ignoring performance → Wasted effort
```

---

## Workflow 5: E-Commerce Launch
**Scenario**: Product catalog with checkout
**Duration**: 2-3 days
**Complexity**: Very High

```
DAY 1: FOUNDATION
├─ PHASE 1: Design (Sequential - 3hrs)
│  ├─ code-architect → System architecture
│  ├─ database-optimizer → Product/order schema
│  └─ api-designer → E-commerce API
│
└─ PHASE 2: Backend (Sequential - 4hrs)
   ├─ backend-architect → API implementation
   └─ security-practice-reviewer → Payment security

DAY 2: FRONTEND & FEATURES
├─ PHASE 3: UI (Parallel - 5hrs)
│  ├─ frontend-developer → Catalog, cart, checkout
│  ├─ mobile-ux-optimizer → Mobile responsiveness
│  └─ seo-specialist → Product SEO
│
└─ PHASE 4: Marketing (Parallel - 3hrs)
   ├─ content-marketing-specialist → Product copy
   ├─ analytics-engineer → Conversion tracking
   └─ growth-hacker → Viral features

DAY 3: QUALITY & LAUNCH
├─ PHASE 5: Testing (Parallel - 3hrs)
│  ├─ test-engineer → E2E checkout flow
│  └─ performance-profiler → Load testing
│
└─ PHASE 6: Deploy (Sequential - 3hrs)
   ├─ deployment-engineer → Production deploy
   └─ observability-engineer → Dashboards

SUCCESS CRITERIA:
✓ Products display correctly
✓ Cart works on all devices
✓ Checkout completes successfully
✓ Payments process securely
✓ SEO optimized
✓ Analytics tracking works
✓ Handles 1000 concurrent users
✓ Monitoring shows healthy metrics

COMMON PITFALLS:
✗ Skipping load testing → Crashes on launch
✗ Poor mobile UX → Lost mobile sales
✗ No analytics → Can't optimize conversion
✗ Weak security → Payment fraud
```

---

## How to Choose Execution Mode

| Scenario | Mode | Why |
|----------|------|-----|
| Backend needs DB schema | Sequential | Backend depends on schema output |
| Frontend needs API spec | Sequential | Frontend needs contract to implement |
| Tests need working code | Sequential | Can't test what doesn't exist |
| Frontend + Backend with mocks | Parallel | Frontend can use mock API |
| Multiple code reviews | Parallel | Independent assessments |
| Security + Performance + A11y audits | Parallel | No dependencies between audits |
| Architecture → Implementation → Testing | Hybrid | Each phase builds on previous |

**General Pattern (Hybrid):**
1. **Architecture Phase**: Sequential (decisions build on each other)
2. **Implementation Phase**: Parallel by domain (frontend, backend, etc.)
3. **Quality Phase**: Parallel reviews (security, performance, code quality)
4. **Deployment Phase**: Sequential (ordered deployment steps)

---

**Back to main documentation**: [CLAUDE.md](../CLAUDE.md)
