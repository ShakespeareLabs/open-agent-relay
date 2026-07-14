#!/usr/bin/env bash
set -euo pipefail

: "${RELAY_ACCESS_KEY:?Set RELAY_ACCESS_KEY to at least 16 characters}"
: "${CLAUDE_WORKSPACE:?Set CLAUDE_WORKSPACE to a dedicated review checkout}"

command -v claude >/dev/null || {
  echo "claude is not installed" >&2
  exit 1
}

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$CLAUDE_WORKSPACE"

exec relay serve \
  --host "${RELAY_HOST:-0.0.0.0}" \
  --port "${RELAY_PORT:-8789}" \
  --name claude-readonly-review \
  --description "Read-only Claude Code review of a dedicated checkout" \
  --execution-timeout "${RELAY_EXECUTION_TIMEOUT:-900}" \
  -- "$script_dir/claude_review.sh"
