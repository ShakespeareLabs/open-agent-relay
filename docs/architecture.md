# Architecture

The `main` branch implements direct local-network access without a Hub.

```text
Teammate CLI / Agent
       |
       | HTTP request over a trusted LAN
       v
OpenAgentRelay server on the author's machine
       |
       | stdin / stdout
       v
Local script or agent + its own tools and credentials
```

## Public interface

- `GET /.well-known/agent-card.json` describes the available agent.
- `POST /v1/invoke` sends one input and waits for one result.
- `relay serve` exposes a local command.
- `relay ask` calls a known machine directly.

## Current execution adapter

- Local command runner using stdin/stdout
- HTTP/JSON client
- Bounded in-memory conversation store with caller binding and expiry
- Execution timeout plus combined stdout/stderr size enforcement

The command adapter starts one process per request. It sends the request to stdin, treats stdout as the final result, and keeps stderr local. The default request is stateless. Optional conversations store a bounded transcript, not a Codex session, and prepend relevant prior turns to the next execution. The server publishes its execution, request, and output limits in the Agent Card so clients and operators can inspect the boundary.

## Planned adapters

- TLS and device identity
- Local-network discovery
- Container runners
- A2A-compatible direct invocation
- Structured progress and file transfer

The older asynchronous Hub experiment is preserved on the `hub-mode` branch. It is intentionally separate from the direct mode so callers do not need to understand two network models at once.
