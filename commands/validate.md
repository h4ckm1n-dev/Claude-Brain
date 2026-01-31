# Run Validation Checks

Run code quality, testing, and security validation checks

**Usage:** `/validate [type]`

**Input:** $ARGUMENTS (optional: syntax, tests, security, quality, all)

---

## Instructions

Run validation checks to ensure code quality and correctness. If no type specified, runs all available validations.

### 1. Determine Validation Scope

Parse $ARGUMENTS:
- `syntax` or `lint` → Linting and type checking only
- `tests` or `test` → Unit and integration tests only
- `security` or `sec` → Security scans only
- `quality` or `metrics` → Code quality metrics only
- `all` or empty → Run all available validations

### 2. Detect Project Type

Automatically detect project type by checking for:

```bash
# Python project indicators
if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
  PROJECT_TYPE="python"
# TypeScript/JavaScript project indicators
elif [ -f "package.json" ] || [ -f "tsconfig.json" ]; then
  PROJECT_TYPE="javascript"
# Go project indicators
elif [ -f "go.mod" ]; then
  PROJECT_TYPE="go"
# Rust project indicators
elif [ -f "Cargo.toml" ]; then
  PROJECT_TYPE="rust"
else
  PROJECT_TYPE="unknown"
fi
```

### 3. Run Validations Based on Type

#### Level 1: Syntax & Linting

**Python:**
```bash
echo "🔍 Running Python syntax checks..."

# Ruff - Fast linter
if command -v ruff &> /dev/null; then
  echo "  → Running ruff..."
  ruff check . --fix || true
else
  echo "  ⚠️  ruff not installed (pip install ruff)"
fi

# MyPy - Type checking
if command -v mypy &> /dev/null; then
  echo "  → Running mypy..."
  mypy . || true
else
  echo "  ⚠️  mypy not installed (pip install mypy)"
fi

# Black - Code formatting (check only)
if command -v black &> /dev/null; then
  echo "  → Checking formatting with black..."
  black --check . || true
else
  echo "  ⚠️  black not installed (pip install black)"
fi
```

**TypeScript/JavaScript:**
```bash
echo "🔍 Running TypeScript/JavaScript syntax checks..."

# TypeScript compiler
if command -v npx &> /dev/null; then
  if [ -f "tsconfig.json" ]; then
    echo "  → Running tsc..."
    npx tsc --noEmit || true
  fi

  # ESLint
  if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f "eslint.config.js" ]; then
    echo "  → Running eslint..."
    npx eslint . --fix || true
  fi

  # Prettier check
  if [ -f ".prettierrc" ] || [ -f "prettier.config.js" ]; then
    echo "  → Checking formatting with prettier..."
    npx prettier --check . || true
  fi
else
  echo "  ⚠️  npm/npx not available"
fi
```

**Go:**
```bash
echo "🔍 Running Go syntax checks..."

if command -v go &> /dev/null; then
  echo "  → Running go vet..."
  go vet ./... || true

  echo "  → Running go fmt check..."
  gofmt -l . || true

  if command -v golangci-lint &> /dev/null; then
    echo "  → Running golangci-lint..."
    golangci-lint run || true
  fi
fi
```

#### Level 2: Tests

**Python:**
```bash
echo "🧪 Running Python tests..."

if command -v pytest &> /dev/null; then
  echo "  → Running pytest with coverage..."
  pytest tests/ -v --cov=src --cov-report=term-missing || true
else
  echo "  ⚠️  pytest not installed (pip install pytest pytest-cov)"
fi
```

**TypeScript/JavaScript:**
```bash
echo "🧪 Running JavaScript/TypeScript tests..."

if [ -f "package.json" ]; then
  if grep -q '"test"' package.json; then
    echo "  → Running npm test..."
    npm test || true
  else
    echo "  ⚠️  No test script found in package.json"
  fi
fi
```

**Go:**
```bash
echo "🧪 Running Go tests..."

if command -v go &> /dev/null; then
  echo "  → Running go test..."
  go test ./... -v -cover || true
fi
```

#### Level 3: Security

**Python:**
```bash
echo "🔒 Running Python security checks..."

# Bandit - Security linter
if command -v bandit &> /dev/null; then
  echo "  → Running bandit..."
  bandit -r . -ll || true
else
  echo "  ⚠️  bandit not installed (pip install bandit)"
fi

# Safety - Dependency vulnerability check
if command -v safety &> /dev/null; then
  if [ -f "requirements.txt" ]; then
    echo "  → Running safety check..."
    safety check -r requirements.txt || true
  fi
else
  echo "  ⚠️  safety not installed (pip install safety)"
fi
```

**TypeScript/JavaScript:**
```bash
echo "🔒 Running npm security audit..."

if [ -f "package.json" ]; then
  echo "  → Running npm audit..."
  npm audit || true
fi
```

**Go:**
```bash
echo "🔒 Running Go security checks..."

if command -v gosec &> /dev/null; then
  echo "  → Running gosec..."
  gosec ./... || true
else
  echo "  ⚠️  gosec not installed (go install github.com/securego/gosec/v2/cmd/gosec@latest)"
fi
```

#### Level 4: Code Quality Metrics

**Python:**
```bash
echo "📊 Running Python code quality metrics..."

# Radon - Complexity metrics
if command -v radon &> /dev/null; then
  echo "  → Running radon complexity check..."
  radon cc . -a -nb || true

  echo "  → Running radon maintainability index..."
  radon mi . || true
else
  echo "  ⚠️  radon not installed (pip install radon)"
fi
```

**TypeScript/JavaScript:**
```bash
echo "📊 Running JavaScript code quality metrics..."

if command -v npx &> /dev/null; then
  # Check if complexity reporter is available
  if npm list complexity-report &> /dev/null; then
    echo "  → Running complexity analysis..."
    npx complexity-report --format plain . || true
  fi
fi
```

### 4. Generate Summary Report

After all validations complete, generate a summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 VALIDATION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project Type: [detected type]
Validation Scope: [syntax/tests/security/quality/all]

🔍 Syntax & Linting:
   [✅/❌] Linter (ruff/eslint/etc)
   [✅/❌] Type checker (mypy/tsc)
   [✅/❌] Formatter (black/prettier)

   Issues found: [count]
   Auto-fixed: [count]

🧪 Tests:
   [✅/❌] Test suite execution

   Tests passed: [X/Y]
   Coverage: [percentage]%
   Failed tests: [count]

🔒 Security:
   [✅/❌] Security scan
   [✅/❌] Dependency audit

   Vulnerabilities: [count]
   Critical: [count]
   High: [count]

📊 Code Quality:
   [✅/❌] Complexity analysis
   [✅/❌] Maintainability index

   High complexity functions: [count]
   Maintainability score: [average]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Status: [✅ PASS / ⚠️ WARNINGS / ❌ FAIL]

[If failures:]
❌ Critical Issues:
   - [Issue 1]
   - [Issue 2]

💡 Next Steps:
   - Fix critical issues before committing
   - Review warnings
   - Consider running specific validation: /validate [type]

[If all pass:]
✅ All validations passed!
   Code is ready for commit/PR
```

---

## Error Handling

- If no validation tools installed: Show warning but don't fail
- If project type unknown: Offer to run generic checks
- If validation command fails: Capture output and show errors
- Always run with `|| true` to continue even on failures

---

## Examples

**Run all validations:**
```
/validate
/validate all
```

**Run specific validation:**
```
/validate syntax
/validate tests
/validate security
/validate quality
```

---

## Notes

- All validation commands run non-destructively (read-only except for auto-fixes)
- Auto-fixes are only applied for linting (with user's implicit consent)
- Tests and security scans are informational only
- Results are saved to console output for review
- Use before commits, PRs, or after major changes
