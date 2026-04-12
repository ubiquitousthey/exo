#!/bin/bash
# check-greppy.sh — Ensure greppy daemon is running before search operations

if ! command -v greppy &>/dev/null; then
  exit 0  # greppy not installed, skip silently
fi

if greppy status &>/dev/null; then
  exit 0  # daemon already running
fi

# Try to start the daemon
echo "Greppy daemon not running, starting..." >&2
greppy start &>/dev/null

# Verify it started
sleep 1
if greppy status &>/dev/null; then
  exit 0
fi

echo "Failed to start greppy daemon. Install or check greppy configuration." >&2
exit 2  # block the tool call
