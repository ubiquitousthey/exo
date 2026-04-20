#!/bin/bash
# install-pre-push.sh — Install exo pre-push git hook in a project
# Usage: install-pre-push.sh [project-dir]

set -euo pipefail

PROJECT_DIR="${1:-.}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
GIT_DIR="$(cd "$PROJECT_DIR" && git rev-parse --git-dir)"

# Resolve relative git dir to absolute
if [[ "$GIT_DIR" != /* ]]; then
  GIT_DIR="$PROJECT_DIR/$GIT_DIR"
fi

HOOK_TARGET="$GIT_DIR/hooks/pre-push"
EXO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_SOURCE="$EXO_ROOT/hooks/pre-push-git.sh"

if [[ -e "$HOOK_TARGET" ]]; then
  echo "Error: $HOOK_TARGET already exists." >&2
  echo "Back it up or remove it, then re-run." >&2
  exit 1
fi

mkdir -p "$(dirname "$HOOK_TARGET")"
ln -s "$HOOK_SOURCE" "$HOOK_TARGET"
echo "Installed pre-push hook: $HOOK_TARGET -> $HOOK_SOURCE"
