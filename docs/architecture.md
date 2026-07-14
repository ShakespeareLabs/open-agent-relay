# Architecture

OpenAgentRelay separates a control plane from execution domains.

```text
Web / CLI / Agent
       |
       v
Hub: capability registry + task lifecycle
       |
       v  outbound polling
Runner: local process / container / remote A2A agent
       |
       v
Agent code + tools + secrets stay in the execution domain
```

## Public concepts

- **Capability** describes what an agent can do, not how it is implemented.
- **Task** is a durable request with an observable lifecycle.
- **Artifact/Event** carries progress and results without exposing implementation details.

## Current adapters

- In-memory Hub store
- Local command runner using stdin/stdout
- HTTP/JSON client

## Planned adapters

- SQLite and PostgreSQL stores
- OIDC identity and policy enforcement
- Container and hosted runners
- A2A ingress/egress
- MCP exposure
- Object storage for artifacts

The project's own model remains capability/task/event. A2A and MCP are compatibility adapters rather than the core domain model.

