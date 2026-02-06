#!/bin/bash
# Protect Sensitive Files - PreToolUse (Write|Edit)
# Blocks writes to .env, credentials, secrets, and private keys

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

FILENAME=$(basename "$FILE_PATH")
FILEPATH_LOWER=$(echo "$FILE_PATH" | tr '[:upper:]' '[:lower:]')

# Deny patterns
BLOCKED=false
REASON=""

case "$FILENAME" in
    .env|.env.*|.env.local|.env.production|.env.staging)
        BLOCKED=true
        REASON="Writing to environment file '$FILENAME' is blocked. These files contain secrets."
        ;;
    *.pem|*.key|*private_key*|*id_rsa*|*id_ed25519*)
        BLOCKED=true
        REASON="Writing to private key file '$FILENAME' is blocked."
        ;;
esac

if echo "$FILEPATH_LOWER" | grep -qiE "(credentials|secret|private.key|\.git/config)"; then
    BLOCKED=true
    REASON="Writing to sensitive file '$FILE_PATH' is blocked. Path matches credential/secret pattern."
fi

if [ "$BLOCKED" = true ]; then
    echo "{\"decision\": \"block\", \"reason\": \"$REASON\"}"
    exit 0
fi

exit 0
