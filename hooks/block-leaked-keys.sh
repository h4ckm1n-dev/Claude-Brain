#!/bin/bash
# Block Leaked Keys in Prompts — UserPromptSubmit
# Blocks sending messages that contain API keys, tokens, or private key material
# Exit with decision:block to prevent the prompt from being sent

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.user_prompt // ""')

if [ -z "$PROMPT" ] || [ "$PROMPT" = "null" ]; then
    exit 0
fi

ISSUES=""

# AWS Access Keys (always start with AKIA)
if echo "$PROMPT" | grep -qE 'AKIA[0-9A-Z]{16}'; then
    ISSUES="${ISSUES}\n- AWS Access Key detected (AKIA...)"
fi

# AWS keys with context clues
if echo "$PROMPT" | grep -qE '[A-Za-z0-9/+=]{40}' && echo "$PROMPT" | grep -qiE 'aws.*(key|cred)'; then
    ISSUES="${ISSUES}\n- Possible AWS key detected"
fi

# OpenAI / Anthropic API keys
if echo "$PROMPT" | grep -qE 'sk-[a-zA-Z0-9_-]{20,}'; then
    ISSUES="${ISSUES}\n- API key detected (sk-...)"
fi

# GitHub tokens
if echo "$PROMPT" | grep -qE 'gh[pousr]_[A-Za-z0-9_]{36,}'; then
    ISSUES="${ISSUES}\n- GitHub token detected (ghp_/gho_/ghu_/ghs_/ghr_...)"
fi

# Private keys (PEM format)
if echo "$PROMPT" | grep -qE '-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'; then
    ISSUES="${ISSUES}\n- Private key (PEM) detected in prompt"
fi

# Slack tokens
if echo "$PROMPT" | grep -qE 'xox[bpors]-[0-9]{10,}-[a-zA-Z0-9-]+'; then
    ISSUES="${ISSUES}\n- Slack token detected (xox...)"
fi

# Generic password patterns (password = "..." or password: "...")
if echo "$PROMPT" | grep -qiE '(password|passwd|pwd)\s*[:=]\s*["\x27][^\s"'\'']{8,}'; then
    ISSUES="${ISSUES}\n- Possible password in plaintext"
fi

if [ -n "$ISSUES" ]; then
    REASON=$(printf "SECURITY: Your prompt may contain leaked keys/tokens:%b\n\nRemove them before sending. Use environment variables or file references instead." "$ISSUES")
    echo "{\"decision\": \"block\", \"reason\": \"$REASON\"}"
    exit 0
fi

exit 0
