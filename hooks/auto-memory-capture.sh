#!/bin/bash
# Auto-capture valuable memories from tool outputs
# Captures MORE but SMARTER - filters for truly useful patterns

TOOL_NAME="$1"
TOOL_OUTPUT="$2"
EXIT_CODE="$3"

# Only capture if tool succeeded
if [ "$EXIT_CODE" -ne 0 ]; then
    exit 0
fi

# Check if memory service is available (fail silently if not)
if ! curl -sf http://localhost:8100/health >/dev/null 2>&1; then
    exit 0
fi

# Get current project context
PROJECT_DIR=$(basename "$(pwd)" 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

# Memory capture based on tool type
case "$TOOL_NAME" in
    "WebFetch")
        # Save ALL WebFetch results (documentation, guides, examples)
        URL=$(echo "$TOOL_OUTPUT" | jq -r '.url // empty' 2>/dev/null)
        CONTENT=$(echo "$TOOL_OUTPUT" | jq -r '.content // empty' 2>/dev/null | head -c 10240)

        if [ -n "$URL" ] && [ -n "$CONTENT" ] && [ ${#CONTENT} -gt 100 ]; then
            # Extract domain and detect library/framework
            DOMAIN=$(echo "$URL" | sed -E 's|https?://([^/]+).*|\1|')

            # Detect tech from URL
            TECH_TAGS=""
            if echo "$URL" | grep -qi "react"; then TECH_TAGS="\"react\","; fi
            if echo "$URL" | grep -qi "docker"; then TECH_TAGS="$TECH_TAGS\"docker\","; fi
            if echo "$URL" | grep -qi "postgres\|postgresql"; then TECH_TAGS="$TECH_TAGS\"postgresql\","; fi
            if echo "$URL" | grep -qi "supabase"; then TECH_TAGS="$TECH_TAGS\"supabase\","; fi
            if echo "$URL" | grep -qi "typescript"; then TECH_TAGS="$TECH_TAGS\"typescript\","; fi

            curl -s http://localhost:8100/memories -X POST \
                -H "Content-Type: application/json" \
                -d "{
                    \"type\": \"docs\",
                    \"content\": \"${CONTENT}\",
                    \"source\": \"${URL}\",
                    \"tags\": [${TECH_TAGS}\"documentation\", \"webfetch\", \"${DOMAIN}\"],
                    \"project\": \"${PROJECT_DIR}\",
                    \"context\": \"Fetched while working on ${PROJECT_DIR}\"
                }" >/dev/null 2>&1
        fi
        ;;

    "Bash")
        # Capture VALUABLE bash commands (deployments, fixes, configs, installs)
        COMMAND="$2"

        # Detect command type and extract key info
        SHOULD_SAVE=false
        TAGS=""
        CONTENT_TYPE="pattern"

        if echo "$COMMAND" | grep -qE "^docker|docker-compose|docker compose"; then
            SHOULD_SAVE=true
            TAGS="\"docker\",\"deployment\","
            CONTENT_TYPE="pattern"
        elif echo "$COMMAND" | grep -qE "^npm (install|run|build|start|test)"; then
            SHOULD_SAVE=true
            TAGS="\"npm\",\"build\","
        elif echo "$COMMAND" | grep -qE "^(pip|pip3) install"; then
            SHOULD_SAVE=true
            TAGS="\"python\",\"dependencies\","
        elif echo "$COMMAND" | grep -qE "^git (clone|pull|checkout)"; then
            SHOULD_SAVE=true
            TAGS="\"git\",\"workflow\","
        elif echo "$COMMAND" | grep -qE "curl.*POST|curl.*PUT|curl.*DELETE"; then
            SHOULD_SAVE=true
            TAGS="\"api\",\"curl\","
        elif echo "$COMMAND" | grep -qE "systemctl|service"; then
            SHOULD_SAVE=true
            TAGS="\"system\",\"services\","
        elif echo "$COMMAND" | grep -qE "chmod|chown|mkdir -p|ln -s"; then
            SHOULD_SAVE=true
            TAGS="\"filesystem\",\"setup\","
        fi

        if [ "$SHOULD_SAVE" = true ]; then
            # Truncate output to reasonable length
            OUTPUT=$(echo "$TOOL_OUTPUT" | head -c 10240)

            curl -s http://localhost:8100/memories -X POST \
                -H "Content-Type: application/json" \
                -d "{
                    \"type\": \"${CONTENT_TYPE}\",
                    \"content\": \"Command: ${COMMAND}\n\nOutput:\n${OUTPUT}\",
                    \"tags\": [${TAGS}\"bash\", \"command\", \"${PROJECT_DIR}\"],
                    \"project\": \"${PROJECT_DIR}\",
                    \"context\": \"Successful command on ${GIT_BRANCH}\"
                }" >/dev/null 2>&1
        fi
        ;;

    "Task")
        # Capture agent task results - extract INSIGHTS not full output
        AGENT_TYPE=$(echo "$TOOL_OUTPUT" | jq -r '.subagent_type // .agent_type // empty' 2>/dev/null)

        # Extract summary/key findings from agent output (first 800 chars)
        RESULT=$(echo "$TOOL_OUTPUT" | jq -r '.result // .output // empty' 2>/dev/null | head -c 10240)

        if [ -n "$AGENT_TYPE" ] && [ -n "$RESULT" ] && [ ${#RESULT} -gt 50 ]; then
            curl -s http://localhost:8100/memories -X POST \
                -H "Content-Type: application/json" \
                -d "{
                    \"type\": \"learning\",
                    \"content\": \"Agent ${AGENT_TYPE} findings: ${RESULT}\",
                    \"tags\": [\"agent\", \"${AGENT_TYPE}\", \"task\", \"${PROJECT_DIR}\"],
                    \"project\": \"${PROJECT_DIR}\",
                    \"context\": \"Task executed on ${GIT_BRANCH}\"
                }" >/dev/null 2>&1
        fi
        ;;

    "Read")
        # Capture when reading configuration files (env, docker-compose, etc)
        FILE_PATH=$(echo "$TOOL_OUTPUT" | jq -r '.file_path // empty' 2>/dev/null)

        if echo "$FILE_PATH" | grep -qE "(docker-compose\.yml|\.env\.example|config\.(js|ts|json)|package\.json|tsconfig\.json)"; then
            CONTENT=$(echo "$TOOL_OUTPUT" | jq -r '.content // empty' 2>/dev/null | head -c 10240)
            FILENAME=$(basename "$FILE_PATH")

            if [ -n "$CONTENT" ] && [ ${#CONTENT} -gt 50 ]; then
                curl -s http://localhost:8100/memories -X POST \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"type\": \"pattern\",
                        \"content\": \"Configuration from ${FILENAME}:\n\n${CONTENT}\",
                        \"tags\": [\"config\", \"${FILENAME}\", \"${PROJECT_DIR}\"],
                        \"project\": \"${PROJECT_DIR}\",
                        \"context\": \"Config file read on ${GIT_BRANCH}\"
                    }" >/dev/null 2>&1
            fi
        fi
        ;;
esac

exit 0
