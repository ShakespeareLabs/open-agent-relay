#!/usr/bin/env bash
set -euo pipefail

: "${RELAY_ACCESS_KEY:?Set RELAY_ACCESS_KEY to at least 16 characters}"
: "${CODEX_WORKSPACE:?Set CODEX_WORKSPACE to a dedicated review checkout}"

command -v codex >/dev/null || {
  echo "codex is not installed" >&2
  exit 1
}

exec relay serve \
  --host "${RELAY_HOST:-0.0.0.0}" \
  --port "${RELAY_PORT:-8788}" \
  --name codex-readonly-review \
  --description "Read-only Codex review of a dedicated checkout" \
  --execution-timeout "${RELAY_EXECUTION_TIMEOUT:-900}" \
  -- codex exec \
       --ephemeral \
       --sandbox read-only \
       --ignore-user-config \
       --skip-git-repo-check \
       -C "$CODEX_WORKSPACE" \
       -
