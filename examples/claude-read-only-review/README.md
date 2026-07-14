# Claude Code read-only review

This example shares a Claude Code review capability while the checkout and Claude credentials remain on the publisher computer. It uses non-interactive print mode, plan permissions, and explicit write/network tool blocks.

## Publisher

Create a dedicated checkout containing only files callers may ask Claude to read, then run:

```bash
export CLAUDE_WORKSPACE="/absolute/path/to/review-checkout"
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
./serve.sh
```

Plan mode prevents edits but still allows read-only exploration. The wrapper additionally removes edit and web tools. Readable secrets can still be disclosed, so sanitize the workspace first.

## Caller

```bash
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
relay ask \
  --target http://PUBLISHER_LAN_IP:8789 \
  --expect-agent claude-readonly-review \
  --request-timeout 930 \
  --json \
  "Review the public API and identify confusing behavior. Do not modify files."
```
