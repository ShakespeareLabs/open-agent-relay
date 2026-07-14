# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **Turn any local agent or automation into a team-callable capability.**

OpenAgentRelay lets a teammate or another Agent call something that already works on your computer. They install one small `relay` CLI; they do not need this repository, your Agent source code, its dependencies, prompts, or business credentials.

The `main` branch is an **Alpha for direct calls on a trusted LAN**. It uses plain HTTP and a shared key. Do not expose it to the public internet or connect it to production write operations.

```text
Caller or caller Agent  ── trusted LAN ──>  Publisher's relay  ──>  Local Agent
          ↑                                                            |
          └──────────────────────── result ─────────────────────────────┘
```

## Install the CLI

Normal users do not need to clone the repository. Install the CLI with [`pipx`](https://pipx.pypa.io/):

```bash
pipx install "git+https://github.com/ShakespeareLabs/open-agent-relay.git@main"
relay version
```

If `pipx` is not installed, follow its one-time installation guide (`brew install pipx` on macOS is the common path).

If you are already inside a Python 3.11+ virtual environment, use:

```bash
python -m pip install "git+https://github.com/ShakespeareLabs/open-agent-relay.git@main"
```

Cloning the repository is only needed for development. After the first packaged release, the primary installation command will become `pipx install open-agent-relay`.

## Publisher: share a capability

The publisher owns the working Agent or automation.

### 1. Start with a safe test

Choose an Access Key of at least 16 characters without putting it in shell history:

```bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
```

Start a harmless test capability:

```bash
relay serve \
  --host 0.0.0.0 \
  --port 8787 \
  --name uppercase \
  --description "Turn text into uppercase" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
```

Successful startup confirms that the configured key was loaded and prints `Serving uppercase on http://0.0.0.0:8787`. If no key was configured, Relay generates and prints a temporary one. Verify the service on the publisher's computer:

```bash
curl http://127.0.0.1:8787/healthz
```

The expected response is `{"status":"ok"}`.

### 2. Share connection details

Find the publisher's LAN address. Common commands are `ipconfig getifaddr en0` on macOS or `hostname -I` on Linux. Send the caller exactly these values through a trusted channel:

```text
Relay URL:    http://192.168.1.42:8787
Agent name:  uppercase
Access Key:  <the RELAY_ACCESS_KEY value>
Purpose:     Turn text into uppercase
Trust scope: Trusted LAN Alpha; no sensitive or production write requests
```

`0.0.0.0` is a listen address, not the address callers should use. A firewall may also need to allow inbound TCP traffic on port 8787.

### 3. Publish an existing command

Relay starts the command once for each request. The command must:

- read one request from standard input;
- write the final answer to standard output;
- write logs and diagnostics to standard error;
- exit when that request is finished.

```bash
relay serve \
  --host 0.0.0.0 \
  --name ads-report \
  --description "Read-only advertising report" \
  -- python /path/to/ads_report.py
```

### 4. Publish a restricted Codex capability

Use a dedicated workspace and the minimum credentials needed for this one capability. Do not expose your everyday Codex environment with all personal files, MCP servers, Skills, and tokens.

```bash
relay serve \
  --host 0.0.0.0 \
  --name code-reviewer \
  --description "Read-only review of the dedicated workspace" \
  -- codex exec \
       --ephemeral \
       --sandbox read-only \
       --ignore-user-config \
       --skip-git-repo-check \
       -C /path/to/restricted-workspace \
       -
```

Each request normally starts a fresh `codex exec`. Codex can use what is available in that restricted workspace, but Relay does not automatically resume the publisher's historical Codex sessions.

## Caller: call a capability

The caller only needs the `relay` CLI and the connection details. They do not need the publisher's repository or Agent implementation.

Load the shared key without placing it in command history:

```bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
```

### Direct execution

For a person:

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent uppercase \
  "hello team"
```

For another Agent or automation, always request JSON:

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent uppercase \
  --json \
  "hello team"
```

Successful JSON output:

```json
{
  "capability": "uppercase",
  "result": "HELLO TEAM"
}
```

### Deep interaction

Direct calls are stateless by default. Start a Relay-managed conversation when follow-up questions need prior context:

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent ads-report \
  --new-conversation \
  --json \
  "Analyze this account"
```

Save the returned `conversation_id`, then continue:

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent ads-report \
  --conversation conv_... \
  --json \
  "Which campaign is worst?"
```

Relay stores a bounded text transcript in memory and injects it into a fresh Agent execution. Conversations expire after one hour by default and disappear when the server restarts. The local Caller ID prevents accidental cross-caller continuation; it is not authenticated personal identity.

## Give this capability to another Agent

Configure `RELAY_ACCESS_KEY` in the caller Agent's environment, then give it this connection block:

```text
You can call a remote capability with the relay CLI.

Target: http://192.168.1.42:8787
Expected Agent: ads-report

For a one-shot request, run:
relay ask --target http://192.168.1.42:8787 --expect-agent ads-report --json "<request>"

For follow-ups, start with --new-conversation, save conversation_id from the JSON,
then use --conversation <conversation_id>. Treat a nonzero exit code as failure.
Do not print or return RELAY_ACCESS_KEY.
```

The Agent needs the CLI and connection block, not the OpenAgentRelay repository.

## Errors and retry behavior

Operational CLI failures exit nonzero and write a JSON error to standard error:

```json
{"error":{"status":401,"code":"UNAUTHORIZED","message":"a valid access key is required"}}
```

Common codes:

| Code | Meaning | Caller action |
|---|---|---|
| `CONNECTION_ERROR` | Wrong address, server stopped, or firewall blocked | Check the URL, LAN, server, and port |
| `UNAUTHORIZED` | Missing or incorrect Access Key | Reload the shared key |
| `AGENT_MISMATCH` | The public Agent name differs | Stop and confirm the publisher |
| `BUSY` | Execution concurrency is full | Retry later with backoff |
| `EXECUTION_TIMEOUT` | The local Agent exceeded its time limit | Ask the publisher or simplify the request |
| `OUTPUT_TOO_LARGE` | The Agent exceeded its output limit | Ask for a smaller result |

The public Agent Card is available at `/.well-known/agent-card.json`. A browser user can also open the Relay URL and enter the Access Key.

## Security boundary

- Bearer authentication uses one shared key; it does not identify individual teammates.
- Transport is plain HTTP. Anyone who can observe the LAN traffic may see the key, input, and output.
- `--expect-agent` prevents configuration mistakes; it does not cryptographically prove server identity.
- Caller input is untrusted. A capable Agent may read files, call tools, or disclose data that its process can access.
- Use a dedicated workspace, read-only tools, minimal credentials, and a narrowly described capability.
- Do not expose the port to the public internet or attach production write operations.

Read [SECURITY.md](SECURITY.md) before serving a real Agent.

## Limits and current scope

`relay serve --help` exposes execution timeout, request size, output size, concurrency, and conversation expiry controls. Version 0.1 does not include TLS, per-user permissions, automatic discovery, file transfer, progress streaming, durable conversations, multiple Agents behind one address, or a sandbox supplied by Relay.

The asynchronous Hub + Runner experiment remains on the [`hub-mode` branch](https://github.com/ShakespeareLabs/open-agent-relay/tree/hub-mode). It is not part of this direct-mode Alpha path.

For source development, see [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under Apache-2.0.
