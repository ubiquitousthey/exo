#!/bin/bash
# pre-push-claude.sh — Claude Code PreToolUse hook to intercept git push

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

if ! echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*(env\s+\S+=\S+\s+)*git\s+push\b'; then
  exit 0
fi

if echo "$COMMAND" | grep -qE 'git\s+push\b.*--no-verify'; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/pre-push-check.sh" --exit-code 2
