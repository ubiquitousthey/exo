#!/bin/bash
# pre-push-git.sh — Git pre-push hook, symlinked into .git/hooks/pre-push
# Resolves through symlink to find exo's hooks directory

REAL_PATH="$(realpath "$0")"
HOOKS_DIR="$(dirname "$REAL_PATH")"

exec "$HOOKS_DIR/pre-push-check.sh" --exit-code 1
