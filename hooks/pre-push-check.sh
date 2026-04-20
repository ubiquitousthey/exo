#!/bin/bash
# pre-push-check.sh — Shared runner for pre-push checks
# Discovers and executes project-declared checks from .exo/pre-push

set -uo pipefail

EXIT_CODE=1
PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --exit-code) EXIT_CODE="$2"; shift 2;;
    --project-dir) PROJECT_DIR="$2"; shift 2;;
    *) shift;;
  esac
done

if [[ "${EXO_SKIP_PRE_PUSH:-}" == "1" ]]; then
  exit 0
fi

CONFIG="$PROJECT_DIR/.exo/pre-push"
if [[ ! -f "$CONFIG" ]]; then
  exit 0
fi

if [[ -x "$CONFIG" ]]; then
  (cd "$PROJECT_DIR" && "$CONFIG") || exit "$EXIT_CODE"
else
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    echo "› $line" >&2
    (cd "$PROJECT_DIR" && eval "$line") || { echo "FAILED: $line" >&2; exit "$EXIT_CODE"; }
  done < "$CONFIG"
fi
