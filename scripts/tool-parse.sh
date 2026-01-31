#!/usr/bin/env bash
set -euo pipefail

# Parse JSON output from tools
# Usage: tool-parse.sh "$json_output" <field>
# Fields: success, errors, summary, data

usage() {
  cat <<EOF
Usage: $(basename "$0") JSON_OUTPUT FIELD

Parse JSON output from Claude Code tools.

Arguments:
    JSON_OUTPUT  The JSON string from a tool (use quotes!)
    FIELD        What to extract: success|errors|summary|data

Examples:
    result=\$(python3 tools/security/secret-scanner.py .)
    tool-parse.sh "\$result" success    # ✅ PASS or ❌ FAIL
    tool-parse.sh "\$result" errors     # List errors
    tool-parse.sh "\$result" summary    # Summary data

Output:
    Formatted text (success/errors) or JSON (summary/data)
EOF
}

# Handle --help flag
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# PATTERN: Use python3 for JSON parsing
json_output="${1:-}"
field="${2:-}"

if [ -z "$json_output" ] || [ -z "$field" ]; then
  usage
  exit 2
fi

# Helper function to safely parse JSON with error handling
safe_json_parse() {
  local python_code="$1"
  local result
  local exit_code

  result=$(echo "$json_output" | python3 -c "$python_code" 2>&1) || exit_code=$?

  if [ "${exit_code:-0}" -ne 0 ]; then
    echo "Error: Invalid JSON input or parsing error" >&2
    echo "Details: $result" >&2
    exit 1
  fi

  echo "$result"
}

case "$field" in
  success)
    # Extract success boolean, format as ✅/❌
    safe_json_parse "import sys, json; data = json.load(sys.stdin); print('✅ PASS' if data.get('success') else '❌ FAIL')"
    ;;
  errors)
    # Extract and format errors array
    safe_json_parse "import sys, json; data = json.load(sys.stdin); errors = data.get('errors', []); print('\\n'.join(f'  - {e}' if isinstance(e, str) else f\"  - {e.get('message', str(e))}\" for e in errors) if errors else '  None')"
    ;;
  summary)
    # Extract summary from data section
    safe_json_parse "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('data', {}).get('summary', {}), indent=2))"
    ;;
  data)
    # Return full data section
    safe_json_parse "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('data', {}), indent=2))"
    ;;
  *)
    echo "Error: Unknown field '$field'" >&2
    echo "Valid fields: success, errors, summary, data" >&2
    usage
    exit 1
    ;;
esac
