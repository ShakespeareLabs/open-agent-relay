# Codex read-only review

This example shares code-review capability without sharing the repository, Codex installation, or credentials. Each request starts an ephemeral Codex run in a dedicated read-only workspace.

## Publisher

Create a separate checkout containing only the code callers may ask about, then run:

```bash
export CODEX_WORKSPACE="/absolute/path/to/review-checkout"
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
./serve.sh
```

The wrapper ignores user Codex configuration and requests a read-only sandbox. Review the workspace itself for secrets because readable files may still appear in model output.

## Caller

```bash
export RELAY_ACCESS_KEY="replace-with-at-least-16-characters"
relay ask \
  --target http://PUBLISHER_LAN_IP:8788 \
  --expect-agent codex-readonly-review \
  --request-timeout 930 \
  --json \
  "Review the authentication code for correctness and security risks. Do not modify files."
```
