#!/bin/bash
# Warn on Sensitive File Reads — PreToolUse (Read)
# Warns (not blocks) when reading files that may contain secrets
# Uses decision:warn to alert without blocking

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [ -z "$FILE_PATH" ] || [ "$FILE_PATH" = "null" ]; then
    exit 0
fi

FILENAME=$(basename "$FILE_PATH")
FILENAME_LOWER=$(echo "$FILENAME" | tr '[:upper:]' '[:lower:]')
FILEPATH_LOWER=$(echo "$FILE_PATH" | tr '[:upper:]' '[:lower:]')

WARN=false
REASON=""

# Environment files
case "$FILENAME_LOWER" in
    .env|.env.*)
        WARN=true
        REASON="Reading environment file '$FILENAME' — may contain secrets. Do not include sensitive values in your response."
        ;;
esac

# Key/certificate files
case "$FILENAME_LOWER" in
    *.pem|*.key|*.p12|*.pfx|*.jks|*.keystore)
        WARN=true
        REASON="Reading key/certificate file '$FILENAME' — contains cryptographic material. Never output private key contents."
        ;;
esac

# SSH keys
case "$FILENAME_LOWER" in
    id_rsa|id_ed25519|id_ecdsa|id_dsa|authorized_keys|known_hosts)
        WARN=true
        REASON="Reading SSH file '$FILENAME' — may contain private keys. Never output private key material."
        ;;
esac

# Credential/secret files by path pattern
if echo "$FILEPATH_LOWER" | grep -qE '(credentials|secrets?\.ya?ml|secrets?\.json|\.secret|token|\.htpasswd|\.netrc|\.pgpass)'; then
    WARN=true
    REASON="Reading file matching credential pattern: '$FILENAME'. Do not include secrets in your response."
fi

# Docker/K8s secrets
if echo "$FILEPATH_LOWER" | grep -qE '(docker-compose.*\.ya?ml|kube.*secret|vault)' && echo "$FILEPATH_LOWER" | grep -qiE 'secret'; then
    WARN=true
    REASON="Reading infrastructure secrets file '$FILENAME'. Be careful not to expose sensitive values."
fi

if [ "$WARN" = true ]; then
    echo "CAUTION: $REASON"
fi

exit 0
