# Initialize Project for Agent Ecosystem

Set up a project to work with the 43-agent ecosystem

**Usage:** `/init-project [project-name]`

**Input:** $ARGUMENTS (optional project name)

---

## Instructions

Initialize a project directory with the necessary structure and files to work effectively with the agent ecosystem.

### 1. Detect Project Context

Determine if initializing in existing or new project:

```bash
# Check current directory
current_dir=$(pwd)
project_name=${ARGUMENTS:-$(basename "$current_dir")}

# Check if already initialized
if [ -f ".claude/PROJECT_CONTEXT.md" ] || [ -f "PROJECT_CONTEXT.md" ]; then
  echo "⚠️  Agent ecosystem appears to be already initialized"
  echo ""
  echo "Found existing configuration:"
  [ -f ".claude/PROJECT_CONTEXT.md" ] && echo "  • .claude/PROJECT_CONTEXT.md"
  [ -f "PROJECT_CONTEXT.md" ] && echo "  • PROJECT_CONTEXT.md"
  echo ""
  echo "Options:"
  echo "  1. Continue and reinitialize (overwrites existing)"
  echo "  2. Cancel initialization"
  echo ""
  read -p "Continue? (y/n): " confirm
  [ "$confirm" != "y" ] && exit 0
fi

# Check if git repository
is_git_repo=false
if git rev-parse --git-dir > /dev/null 2>&1; then
  is_git_repo=true
fi
```

### 2. Create Directory Structure

```bash
echo "📁 Creating agent ecosystem structure..."

# Option A: Local .claude directory (project-specific)
# Option B: Root level (simpler structure)

# Ask user preference
echo ""
echo "Directory structure preference:"
echo "  1. .claude/ directory (keeps ecosystem files organized)"
echo "  2. Root level (simpler, direct access)"
echo ""
read -p "Choose (1 or 2): " structure_choice

if [ "$structure_choice" == "1" ]; then
  base_dir=".claude"
else
  base_dir="."
fi

# Create directories
mkdir -p "$base_dir/docs/api"
mkdir -p "$base_dir/docs/architecture"
mkdir -p "$base_dir/docs/database"
mkdir -p "$base_dir/docs/design"

echo "✅ Created directory structure:"
echo "   $base_dir/"
echo "   └── docs/"
echo "       ├── api/           (API specifications)"
echo "       ├── architecture/  (Architecture decisions)"
echo "       ├── database/      (Schema, ERDs)"
echo "       └── design/        (UI/UX mockups)"
```

### 3. Initialize PROJECT_CONTEXT.md

```bash
echo ""
echo "📝 Initializing PROJECT_CONTEXT.md..."

# Copy template
cp ~/.claude/PROJECT_CONTEXT_TEMPLATE.md ./PROJECT_CONTEXT.md

# Customize with project info
# (Replace placeholder values)

echo "✅ Created PROJECT_CONTEXT.md"
```

### 4. Create .gitignore Rules (If Git Repo)

```bash
if [ "$is_git_repo" = true ]; then
  echo ""
  echo "📋 Updating .gitignore..."

  gitignore_additions="
# Agent Ecosystem
PROJECT_ARCHIVE_*.md
*.log

# Keep these in git
!PROJECT_CONTEXT.md
!docs/
"

  if [ -f ".gitignore" ]; then
    # Check if already has agent ecosystem rules
    if ! grep -q "# Agent Ecosystem" .gitignore; then
      echo "$gitignore_additions" >> .gitignore
      echo "✅ Updated .gitignore"
    else
      echo "ℹ️  .gitignore already has agent ecosystem rules"
    fi
  else
    echo "$gitignore_additions" > .gitignore
    echo "✅ Created .gitignore"
  fi
fi
```

### 5. Run Environment Check

```bash
echo ""
echo "🔍 Checking environment..."
echo ""

# Run tool check
bash ~/.claude/scripts/check-tools.sh
```

### 6. Create Quick Start Guide

```bash
echo ""
echo "📚 Creating QUICKSTART.md..."

cat > QUICKSTART.md << 'EOF'
# Agent Ecosystem Quick Start

Your project is now set up to work with the 43-agent ecosystem!

## 🚀 Getting Started

### 1. Create Your First Feature

Create a feature description file:

\`\`\`bash
cat > INITIAL.md << 'FEATURE'
# Feature: User Authentication

Implement user login and registration with JWT tokens.

## Requirements
- Email/password login
- JWT token generation
- Secure password hashing
- Session management

## Examples
See similar auth implementation in: [other-project/auth]

## Documentation
- JWT: https://jwt.io/
- bcrypt: https://github.com/kelektiv/node.bcrypt.js
FEATURE
\`\`\`

### 2. Let Claude Code Plan and Execute

Simply describe your feature to Claude Code:

\`\`\`
"Implement user authentication with JWT tokens, email/password login, and secure password hashing"
\`\`\`

Claude Code will:
- Enter Plan mode to design the approach
- Select appropriate agents automatically
- Execute agent workflow
- Coordinate between agents via PROJECT_CONTEXT.md
- Run validation
- Report completion

Or use quick-agent for direct execution:
\`\`\`bash
/quick-agent backend-architect: implement JWT authentication
\`\`\`

## 📋 Common Commands

### Quick Tasks
\`\`\`bash
# Launch single agent for quick task
/quick-agent backend-architect: add logging to auth endpoint

# Find right agent for task
/agent-select implement password reset feature

# Review your changes
/review-code

# Run validation
/validate
\`\`\`

### Project Management
\`\`\`bash
# Check project status
/status

# View agent analytics
/agent-metrics

# Clean up context
/context-clean
\`\`\`

### Debugging
\`\`\`bash
# Debug failed task
/debug-task tests failing after auth refactor

# Debug with specific agent
/quick-agent debugger: investigate login button not working
\`\`\`

### Discovery
\`\`\`bash
# Browse available agents
/list-agents

# Search agents by category
/list-agents backend
/list-agents testing
\`\`\`

## 🎯 Workflow Patterns

### Simple Feature (Single Agent)
\`\`\`bash
1. /quick-agent [agent-name]: [task]
2. Review changes
3. Commit
\`\`\`

### Complex Feature (Multiple Agents)
\`\`\`bash
1. Describe the feature to Claude Code
2. Let Claude Code plan the approach
3. Review and approve the plan
4. /status to check progress
5. /validate to confirm quality
6. Commit and push
\`\`\`

### Bug Fixing
\`\`\`bash
1. /debug-task [description of bug]
2. Let debugger agent investigate
3. Review proposed fix
4. /validate to confirm
5. Commit
\`\`\`

### Code Review
\`\`\`bash
1. Make changes
2. /review-code
3. Address issues
4. /validate
5. Commit
\`\`\`

## 📚 Learn More

- Agent catalog: /list-agents
- Agent metrics: /agent-metrics
- Project status: /status
- CLAUDE.md: ~/.claude/CLAUDE.md (full documentation)

## 💡 Tips

1. **Use Plan mode for features**: Let Claude Code plan complex features
2. **Use quick-agent for fixes**: /quick-agent [agent]: [task]
3. **Validate often**: /validate before committing
4. **Check status**: /status to see progress
5. **Clean context**: /context-clean when file gets large
6. **Debug systematically**: /debug-task for issues

## 🆘 Need Help?

- Find right agent: /agent-select [task description]
- Browse agents: /list-agents
- Check metrics: /agent-metrics
- View status: /status

Happy building! 🚀
EOF

echo "✅ Created QUICKSTART.md"
```

### 7. Create Sample INITIAL.md (Optional)

Ask user if they want to create a sample feature:

```
Would you like to create a sample INITIAL.md to get started? (y/n)
```

If yes:
```bash
cat > INITIAL.md << 'EOF'
# Feature: Sample Feature

This is a sample feature description file. Replace with your actual feature.

## Goal
[What needs to be built]

## Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

## Examples
[Point to similar code in codebase]

## Documentation
[Relevant documentation links]

## Technical Notes
[Any important technical considerations]
EOF

echo "✅ Created sample INITIAL.md"
echo "   Edit this file with your feature description"
```

### 8. Run Initial Health Check

```bash
echo ""
echo "🏥 Running agent health check..."
echo ""

bash ~/.claude/scripts/agent-health-check.sh 2>/dev/null || echo "⚠️  Agent health check not available"
```

### 9. Present Initialization Summary

```
🎉 INITIALIZATION COMPLETE!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project: [project-name]
Location: [directory path]

✅ Created Structure:
   [If .claude/]
   • .claude/docs/             (Artifacts)

   [If root level]
   • docs/                     (Artifacts)

   • PROJECT_CONTEXT.md        (Agent coordination)
   • QUICKSTART.md             (Getting started guide)
   [If created]
   • INITIAL.md                (Sample feature)

✅ Git Integration:
   [If git repo]
   • Updated .gitignore
   • Ready for commits

🔧 Environment:
   [Tool availability summary]

   [If tools missing]
   ⚠️  Some tools not available:
       Install: [installation commands]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 NEXT STEPS:

1. Read the quick start guide:
   cat QUICKSTART.md

2. Create your first feature:
   • Describe your feature to Claude Code
   • Let it plan and execute with specialized agents
   • Or use: /quick-agent [agent]: [task]

3. Explore available commands:
   • /status        - View project status
   • /list-agents   - Browse available agents
   • /agent-select  - Find right agent for task
   • /validate      - Run quality checks

4. Learn the workflow:
   • Simple fixes: /quick-agent [agent]: [task]
   • Complex features: Use Claude Code's Plan mode
   • Debugging: /debug-task [issue]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 Resources:
   • Quick Start: QUICKSTART.md
   • Full Docs: ~/.claude/CLAUDE.md
   • Agent List: /list-agents
   • Project Status: /status

💡 Tip: Start with a simple feature to learn the workflow!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Your project is ready for the 43-agent ecosystem!
```

---

## Initialization Modes

### Mode 1: New Project
```bash
mkdir my-new-project
cd my-new-project
git init
/init-project my-new-project
```

### Mode 2: Existing Project
```bash
cd existing-project
/init-project
# Integrates with existing structure
```

### Mode 3: Monorepo
```bash
cd monorepo/packages/my-service
/init-project my-service
# Local .claude/ directory
```

---

## Directory Structure Options

**Option A: .claude/ directory (Organized)**
```
project/
├── .claude/
│   └── docs/
├── PROJECT_CONTEXT.md
├── QUICKSTART.md
└── [your code]
```

**Option B: Root level (Simple)**
```
project/
├── docs/
├── PROJECT_CONTEXT.md
├── QUICKSTART.md
└── [your code]
```

---

## Notes

- Safe to run on existing projects (asks for confirmation)
- Creates minimal structure, expands as needed
- Integrates with git if repository exists
- Provides immediate quick start guide
- Checks environment and suggests tool installation
- Can be customized per project type
- Does not modify existing code
- Only creates agent ecosystem infrastructure
