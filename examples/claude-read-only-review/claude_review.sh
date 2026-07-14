#!/usr/bin/env bash
set -euo pipefail

request=$(cat)
exec claude \
  --print \
  --permission-mode plan \
  --disallowedTools "Edit,Write,NotebookEdit,WebFetch,WebSearch" \
  "$request"
