#!/usr/bin/env bash
set -euo pipefail

: "${RELAY_ACCESS_KEY:?Set RELAY_ACCESS_KEY to at least 16 characters}"

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

exec relay serve \
  --host "${RELAY_HOST:-0.0.0.0}" \
  --port "${RELAY_PORT:-8787}" \
  --name campaign-report \
  --description "Read-only summary of a local campaign CSV" \
  -- python "$script_dir/report.py"
