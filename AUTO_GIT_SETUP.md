# Automatic Git Commit & Push System

**Version**: 1.0
**Date**: 2026-02-01
**Status**: ✅ Active

---

## 📖 Overview

This system automatically commits changes when Claude Code completes a task. Two hook variants available:

1. **smart-git-commit.sh** - Intelligent conventional commits (ACTIVE)
2. **auto-git-commit.sh** - Basic auto-commit with file summaries

---

## 🎯 How It Works

### Architecture

```
Claude completes task
  ↓
[Stop Hook Triggered]
  ↓
intelligent-session-summary.sh (first)
  ↓
smart-git-commit.sh (second)
  ↓
Analyzes changed files → Determines commit type
  ↓
Generates conventional commit message
  ↓
Auto-commits (and optionally pushes)
  ↓
Logs to ~/.claude/logs/auto-git.log
```

### Hook Configuration

**File**: `~/.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/intelligent-session-summary.sh 2>/dev/null || true",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "~/.claude/hooks/smart-git-commit.sh 2>/dev/null || true",
            "timeout": 10,
            "description": "Auto-commit changes with intelligent messages at end of task"
          }
        ]
      }
    ]
  }
}
```

---

## 🧠 Smart Commit Logic

### File Type Detection

The hook analyzes changed files to determine commit type and scope:

| File Pattern | Detection | Commit Type | Scope |
|--------------|-----------|-------------|-------|
| `(test\|spec).(ts\|js\|py\|go)` | HAS_TESTS | `test` | `tests` |
| `(README\|CHANGELOG\|.md)` | HAS_DOCS | `docs` | `documentation` |
| `package.json\|requirements.txt` | HAS_CONFIG | `chore` | `config` |
| `.(tsx?\|jsx?\|vue\|svelte)` | HAS_FRONTEND | `feat` | `frontend` |
| `(server\|api\|route\|controller)` | HAS_BACKEND | `feat` | `backend` |
| `hooks/.*.sh` | HAS_HOOKS | `feat` | `hooks` |
| `agents/.*.md` | HAS_AGENTS | `docs` | `agents` |

### Commit Type Priority

```bash
if tests changed → test(tests)
elif docs changed → docs(documentation)
elif config changed → chore(config)
elif frontend + backend → feat(full-stack)
elif frontend only → feat(frontend)
elif backend only → feat(backend)
elif hooks changed → feat(hooks)
elif agents changed → docs(agents)
else → chore(general)
```

### Session Summary Integration

The hook tries to use context from `/tmp/claude/current-session-summary.txt` (created by intelligent-session-summary.sh):

**With summary:**
```
feat(backend): Add user authentication with JWT tokens

Changed files:
  M  src/auth/jwt.ts
  M  src/middleware/auth.ts
  A  tests/auth.test.ts

Session context:
  Implemented JWT authentication
  Added middleware for protected routes

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Without summary (fallback):**
```
feat(backend): update 3 files

Changed files:
  M  src/auth/jwt.ts
  M  src/middleware/auth.ts
  A  tests/auth.test.ts

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## ⚙️ Configuration Options

### Environment Variables

Set these in your environment or add to settings.json `env` section:

```bash
# Smart Git Commit Configuration
export CLAUDE_AUTO_COMMIT_SMART=true   # Enable/disable smart commits (default: true)
export CLAUDE_AUTO_PUSH=false          # Auto-push after commit (default: false)

# Basic Git Commit Configuration (if using auto-git-commit.sh instead)
export CLAUDE_AUTO_COMMIT=true         # Enable/disable auto-commit (default: true)
export CLAUDE_AUTO_PUSH=false          # Auto-push after commit (default: false)
export CLAUDE_MIN_FILES_CHANGED=1      # Minimum files to trigger commit (default: 1)
```

### Switching Between Hooks

**Currently active**: `smart-git-commit.sh` (conventional commits)

**To switch to basic commits**:
Edit `~/.claude/settings.json` and change:
```json
"command": "~/.claude/hooks/smart-git-commit.sh 2>/dev/null || true"
```
to:
```json
"command": "~/.claude/hooks/auto-git-commit.sh 2>/dev/null || true"
```

---

## 🔒 Safety Features

### Pre-Commit Checks

Both hooks verify before committing:
1. ✅ Is this a git repository?
2. ✅ Are there actually changes to commit?
3. ✅ Are there enough changed files (configurable minimum)?

### Staged Changes

Hooks automatically stage all changes with `git add -A`, then commit.

**Warning**: This includes untracked files. Make sure your `.gitignore` is properly configured.

### Push Safety

Auto-push is **DISABLED by default** for safety.

When enabled (`CLAUDE_AUTO_PUSH=true`), the hook:
- Checks for remote repository
- Verifies current branch has upstream configured
- Only pushes if upstream exists
- Logs success/failure

**Recommended**: Keep auto-push disabled, manually push when ready.

---

## 📊 Commit Message Format

### Conventional Commits Standard

```
<type>(<scope>): <description>

<body>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `test` - Test additions/modifications
- `chore` - Maintenance (config, build, etc.)
- `refactor` - Code refactoring
- `perf` - Performance improvements

**Scopes**:
- `frontend` - UI/client changes
- `backend` - Server/API changes
- `full-stack` - Both frontend and backend
- `tests` - Testing changes
- `config` - Configuration changes
- `documentation` - Docs changes
- `hooks` - Hook script changes
- `agents` - Agent definition changes

---

## 🧪 Testing

### Test Basic Functionality

```bash
# 1. Make a simple change
echo "# Test" >> test-file.md

# 2. Trigger a Claude Code task (any simple task)
# The Stop hook will run when Claude finishes

# 3. Check git log
git log -1 --pretty=format:"%s"

# Expected: docs(documentation): update test-file.md
```

### Test Smart Type Detection

```bash
# Test frontend detection
echo "const x = 1;" >> src/components/Test.tsx
# Expected: feat(frontend): ...

# Test backend detection
echo "const x = 1;" >> src/api/routes.ts
# Expected: feat(backend): ...

# Test full-stack detection
echo "const x = 1;" >> src/components/Test.tsx
echo "const x = 1;" >> src/api/routes.ts
# Expected: feat(full-stack): ...

# Test test detection
echo "test('...', () => {});" >> tests/example.test.ts
# Expected: test(tests): ...
```

### Test Auto-Push (Optional)

```bash
# Enable auto-push
export CLAUDE_AUTO_PUSH=true

# Ensure upstream is configured
git branch --set-upstream-to=origin/main main

# Make a change and trigger Claude task
# Check if push occurred
git log origin/main..main  # Should be empty if push succeeded
```

### View Logs

```bash
# Real-time monitoring
tail -f ~/.claude/logs/auto-git.log

# View recent commits
tail -20 ~/.claude/logs/auto-git.log

# Filter by type
grep "✅ Smart commit created" ~/.claude/logs/auto-git.log
```

---

## 📝 Example Commit Messages

### Feature: Frontend + Backend

```
feat(full-stack): Add user profile editing

Changed files:
  M  src/components/ProfileForm.tsx
  M  src/api/users.ts
  M  src/types/user.ts

Session context:
  Implemented profile form validation
  Added API endpoint for profile updates
  Updated user type definitions

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Test: New Test Suite

```
test(tests): Add authentication test suite

Changed files:
  A  tests/auth/login.test.ts
  A  tests/auth/signup.test.ts
  A  tests/auth/jwt.test.ts

Session context:
  Created comprehensive auth test coverage
  Tests for login, signup, and JWT validation

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Documentation: README Update

```
docs(documentation): Update installation instructions

Changed files:
  M  README.md

Session context:
  Added Docker setup instructions
  Updated environment variable documentation

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Chore: Dependency Update

```
chore(config): Update dependencies

Changed files:
  M  package.json
  M  package-lock.json

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Hook: New Hook Added

```
feat(hooks): Add smart git commit automation

Changed files:
  A  .claude/hooks/smart-git-commit.sh
  M  .claude/settings.json

Session context:
  Created intelligent commit message generation
  Integrated conventional commits standard

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🐛 Troubleshooting

### Hook Not Running

**Symptoms**: No commits happening after Claude tasks

**Check**:
1. Verify hook is executable:
   ```bash
   ls -la ~/.claude/hooks/smart-git-commit.sh
   # Should show -rwxr-xr-x
   ```

2. Verify hook is in settings.json:
   ```bash
   grep -A 10 '"Stop":' ~/.claude/settings.json
   # Should show smart-git-commit.sh
   ```

3. Check if auto-commit is enabled:
   ```bash
   grep "AUTO_COMMIT" ~/.claude/hooks/smart-git-commit.sh
   # AUTO_COMMIT_SMART=${CLAUDE_AUTO_COMMIT_SMART:-true}
   ```

4. View logs for errors:
   ```bash
   tail -20 ~/.claude/logs/auto-git.log
   ```

### Commits Have Wrong Type

**Symptoms**: Test files committed as `feat` instead of `test`

**Cause**: File pattern detection order is wrong

**Fix**: Check file patterns in smart-git-commit.sh:
```bash
# Tests should be checked FIRST
if [ "$HAS_TESTS" -gt 0 ]; then
    COMMIT_TYPE="test"
    SCOPE="tests"
```

### No Session Summary in Commits

**Symptoms**: Commits say "update N files" instead of descriptive message

**Cause**: intelligent-session-summary.sh not running or failing

**Fix**:
1. Check if summary hook runs before git hook:
   ```bash
   grep -B 5 "smart-git-commit" ~/.claude/settings.json
   # intelligent-session-summary.sh should appear BEFORE
   ```

2. Verify summary file exists:
   ```bash
   cat /tmp/claude/current-session-summary.txt
   ```

3. Check summary hook logs:
   ```bash
   tail ~/.claude/logs/session-summaries.log
   ```

### Auto-Push Failing

**Symptoms**: Commit succeeds but push fails

**Check**:
1. Verify upstream branch:
   ```bash
   git rev-parse --abbrev-ref --symbolic-full-name @{u}
   # Should show: origin/main (or your branch)
   ```

2. Set upstream if missing:
   ```bash
   git push -u origin main
   ```

3. Check network/authentication:
   ```bash
   git fetch
   # Should succeed without errors
   ```

4. Check logs for specific error:
   ```bash
   grep "Failed to push" ~/.claude/logs/auto-git.log
   ```

### Commits Missing Files

**Symptoms**: Some changed files not included in commit

**Cause**: Files might be in .gitignore

**Check**:
```bash
git status --short
# Shows all changes

git ls-files --others --ignored --exclude-standard
# Shows ignored files
```

### Too Many Commits

**Symptoms**: Every tiny Claude response creates a commit

**Solution**: Increase minimum files threshold:
```bash
export CLAUDE_MIN_FILES_CHANGED=3  # Require 3+ files changed
```

Or switch to manual commits:
```bash
export CLAUDE_AUTO_COMMIT_SMART=false
```

---

## 🎯 Best Practices

### When to Enable Auto-Commit

**✅ GOOD USE CASES:**
- Active development with frequent small changes
- Working on feature branch (safe to commit often)
- Prototyping or experimentation
- Solo development projects

**❌ AVOID:**
- Working on main/production branch
- Collaborative projects (might conflict with others)
- When following strict PR review process
- When commits need manual review before sharing

### When to Enable Auto-Push

**⚠️ USE WITH CAUTION:**
- Only on personal feature branches
- Only when you want immediate backup to remote
- Never on shared branches without team agreement

**Recommended**: Keep auto-push DISABLED. Use manual `git push` when ready.

### Commit Hygiene

Even with auto-commits, maintain good practices:

1. **Use .gitignore properly**:
   ```bash
   # Add common patterns
   echo "node_modules/" >> .gitignore
   echo ".env" >> .gitignore
   echo "*.log" >> .gitignore
   ```

2. **Review commits periodically**:
   ```bash
   git log -10 --oneline
   # Check if messages make sense
   ```

3. **Squash before PR**:
   ```bash
   # Squash multiple auto-commits into one meaningful commit
   git rebase -i HEAD~10
   ```

4. **Amend if needed**:
   ```bash
   # If auto-commit message is unclear, amend it
   git commit --amend
   ```

### Session Summary Quality

To get better commit messages, ensure good session summaries:

The intelligent-session-summary.sh hook creates `/tmp/claude/current-session-summary.txt` which is used by the git hook.

**Better sessions = Better commit messages**

---

## 🔧 Customization

### Add New File Type Detection

Edit `/Users/h4ckm1n/.claude/hooks/smart-git-commit.sh`:

```bash
# Add after existing patterns (around line 42)
HAS_STYLES=$(echo "$CHANGED_FILES" | grep -c -E "\.(css|scss|sass)$")

# Add to commit type logic (around line 54)
if [ "$HAS_STYLES" -gt 0 ]; then
    COMMIT_TYPE="style"
    SCOPE="styling"
```

### Change Commit Type Priority

Edit the if/elif chain (lines 54-78):

```bash
# Current order:
# 1. Tests
# 2. Docs
# 3. Config
# 4. Frontend+Backend
# 5. Frontend
# 6. Backend

# To prioritize config changes, move config check to top:
if [ "$HAS_CONFIG" -gt 0 ]; then
    COMMIT_TYPE="chore"
    SCOPE="config"
elif [ "$HAS_TESTS" -gt 0 ]; then
    # ... rest
```

### Customize Commit Message Template

Edit the message generation (lines 84-122):

```bash
# Add custom footer
COMMIT_BODY="$COMMIT_BODY

Reviewed-by: AutoGit Bot
Ticket: PROJ-123"

# Change attribution
Co-Authored-By: Your Name <your@email.com>
```

### Disable for Specific Directories

Add skip logic at the top of the hook:

```bash
# Skip if in vendor/ directory
CURRENT_DIR=$(pwd)
if [[ "$CURRENT_DIR" == *"/vendor/"* ]]; then
    exit 0
fi

# Skip if PROJECT_ROOT has .no-auto-commit file
if [ -f ".no-auto-commit" ]; then
    exit 0
fi
```

---

## 📊 Monitoring & Analytics

### View Commit Statistics

```bash
# Count auto-commits today
grep "$(date '+%Y-%m-%d')" ~/.claude/logs/auto-git.log | grep -c "✅ Smart commit"

# Most common commit types
git log --oneline --since="1 week ago" | grep -oE "^[a-z]+\(" | sort | uniq -c | sort -rn

# Average commits per day
git log --oneline --since="1 month ago" | wc -l
```

### Log Analysis

```bash
# View recent activity
tail -50 ~/.claude/logs/auto-git.log

# Filter by commit type
grep "Type: feat" ~/.claude/logs/auto-git.log

# Check for push failures
grep "❌ Failed to push" ~/.claude/logs/auto-git.log

# View successful pushes
grep "✅ Pushed to" ~/.claude/logs/auto-git.log
```

### Git Statistics

```bash
# Commits by hour (shows when Claude is most active)
git log --format="%ad" --date=format:"%H" | sort | uniq -c

# Files changed most often
git log --name-only --oneline | grep -v "^[a-f0-9]" | sort | uniq -c | sort -rn | head -20

# Auto-commit vs manual commit ratio
TOTAL=$(git log --oneline --since="1 week ago" | wc -l)
AUTO=$(git log --oneline --since="1 week ago" | grep "Co-Authored-By: Claude" | wc -l)
echo "Auto: $AUTO / $TOTAL ($(( AUTO * 100 / TOTAL ))%)"
```

---

## 🔗 Integration with Other Systems

### Memory System Integration

The git hook runs AFTER intelligent-session-summary.sh, which creates session summaries used in commit messages.

**Flow**:
```
Claude completes task
  ↓
intelligent-session-summary.sh
  → Analyzes session
  → Creates /tmp/claude/current-session-summary.txt
  ↓
smart-git-commit.sh
  → Reads session summary
  → Generates commit message
  → Commits changes
```

### CI/CD Integration

Auto-commits work seamlessly with CI/CD:

```yaml
# .github/workflows/ci.yml
on:
  push:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm test
```

**Note**: Auto-pushed commits will trigger CI automatically if auto-push is enabled.

### Pre-commit Hooks

The auto-git-commit hook respects standard pre-commit hooks:

```bash
# Install pre-commit framework
pip install pre-commit

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer

# Auto-git-commit will run these before committing
```

---

## 🎓 Examples of Real-World Usage

### Example 1: Feature Development Session

**User task**: "Add user registration API endpoint"

**Files changed**:
- `src/api/auth.ts` (new endpoint)
- `src/types/user.ts` (type definitions)
- `tests/api/auth.test.ts` (tests)

**Auto-commit result**:
```
feat(full-stack): Add user registration API endpoint

Changed files:
  M  src/api/auth.ts
  M  src/types/user.ts
  A  tests/api/auth.test.ts

Session context:
  Created /api/auth/register endpoint
  Added validation for email and password
  Implemented bcrypt password hashing
  Created comprehensive test suite

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Commit hash**: `a7f3c21`
**Logged**: `~/.claude/logs/auto-git.log` with ✅ success

---

### Example 2: Bug Fix Session

**User task**: "Fix login not working with special characters in password"

**Files changed**:
- `src/utils/auth.ts` (URL encoding fix)

**Auto-commit result**:
```
fix(backend): Fix login with special characters in password

Changed files:
  M  src/utils/auth.ts

Session context:
  Added URL encoding for password field
  Prevents special characters from breaking auth

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Example 3: Documentation Update

**User task**: "Update README with new environment variables"

**Files changed**:
- `README.md`

**Auto-commit result**:
```
docs(documentation): Update README with environment variables

Changed files:
  M  README.md

Session context:
  Documented DATABASE_URL configuration
  Added JWT_SECRET setup instructions

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📚 Related Documentation

- **PLANNING_WORKFLOW_GUIDE.md** - Planning-first workflow
- **AUTO_PLANMODE_SETUP.md** - Auto plan mode suggestions
- **MEMORY_WORKFLOW.md** - Memory system integration
- **settings.json** - All hook configurations
- **CLAUDE.md** - Main agent configuration

---

## 🚀 Quick Start

### Installation (Already Complete)

✅ Hook created: `~/.claude/hooks/smart-git-commit.sh`
✅ Hook made executable: `chmod +x`
✅ Hook configured in `~/.claude/settings.json`
✅ Logging directory exists: `~/.claude/logs/`

### Verify Installation

```bash
# Check hook is executable
ls -la ~/.claude/hooks/smart-git-commit.sh
# Expected: -rwxr-xr-x

# Check hook is in settings
grep "smart-git-commit" ~/.claude/settings.json
# Expected: Found in Stop hooks

# Test with a dummy change
echo "# Test" >> test.md
# Complete a Claude task, check git log
git log -1
# Should see auto-commit
```

### First Use

1. Make a change in your project
2. Ask Claude to complete any task
3. When Claude finishes, check:
   ```bash
   git log -1 --oneline
   tail -5 ~/.claude/logs/auto-git.log
   ```
4. You should see an auto-commit with conventional commit format

---

## ❓ FAQ

**Q: Will this commit after EVERY Claude response?**
A: No, only when Claude completes a task (Stop hook) and there are uncommitted changes.

**Q: Can I disable it temporarily?**
A: Yes, set `export CLAUDE_AUTO_COMMIT_SMART=false` in your environment.

**Q: What if I want manual commits?**
A: Disable the hook or set minimum files threshold very high (e.g., `CLAUDE_MIN_FILES_CHANGED=999`).

**Q: Can I customize the commit message format?**
A: Yes, edit `~/.claude/hooks/smart-git-commit.sh` lines 84-122.

**Q: Will this conflict with my workflow?**
A: It works alongside manual commits. Auto-commits are just regular git commits.

**Q: What happens if commit fails?**
A: Error is logged to `~/.claude/logs/auto-git.log`, hook exits gracefully.

**Q: Can I use this with pre-commit hooks?**
A: Yes, the auto-commit respects and triggers pre-commit hooks.

**Q: Should I enable auto-push?**
A: Recommended to keep it disabled (`CLAUDE_AUTO_PUSH=false`). Push manually when ready.

**Q: How do I see what was auto-committed?**
A: Check `git log` or `~/.claude/logs/auto-git.log`.

**Q: Can I squash auto-commits later?**
A: Yes, use `git rebase -i` to squash multiple auto-commits before PR.

---

**Version**: 1.0
**Last Updated**: 2026-02-01
**Status**: ✅ Production Ready
**Maintainer**: Claude Code Agent Ecosystem
