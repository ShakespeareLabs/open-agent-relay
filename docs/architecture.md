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
- **Task** is a request with an observable lifecycle. The current in-memory adapter is not durable across Hub restarts.
- **Artifact/Event** carries progress and results without exposing implementation details.

## Current adapters

- In-memory Hub store
- Local command runner using stdin/stdout
- HTTP/JSON client
- Role-separated bearer authentication
- Lease + heartbeat ownership of running tasks
- Bounded retries and idempotent completion

## Task lifecycle

```text
pending → running (leased) → completed
   ↑           |
   └── retry ──┘
               └→ failed after max attempts
```

Only the Runner holding the current lease can heartbeat, complete, or fail a running task. Expired leases requeue until the attempt limit is reached.

## Planned adapters

- SQLite and PostgreSQL stores
- OIDC identity and policy enforcement
- Container and hosted runners
- A2A ingress/egress
- MCP exposure
- Object storage for artifacts

The project's own model remains capability/task/event. A2A and MCP are compatibility adapters rather than the core domain model.
