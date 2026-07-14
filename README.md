# OpenAgentRelay

> Share what your agent can do—not its code, environment, or secrets.

OpenAgentRelay turns an existing local script or agent into a team-callable asynchronous capability. Callers submit tasks; the agent runs in its owner's execution environment and returns the result. Its code, dependencies, prompts, and credentials do not need to be copied to every user.

## Why not just share a Skill?

A Skill distributes **how to do the work**. OpenAgentRelay shares **access to the working capability**.

| Skill package | OpenAgentRelay |
|---|---|
| Every user installs code and dependencies | The author runs one working instance |
| Every user configures credentials | Credentials remain in the execution domain |
| Updates propagate through reinstalling | The author updates once |
| Execution is local and hard to audit | Tasks have a shared lifecycle and history |

Skills can still power the agent internally. Relay handles publishing, task delivery, execution, and result return.

## Five-minute demo

Requires Python 3.11+ and no runtime dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Start the development Hub:

```bash
relay hub
```

In another terminal, expose any command that reads a task from stdin and writes its result to stdout:

```bash
relay expose \
  --name uppercase \
  --description "Turn text into uppercase" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
```

Submit a task:

```bash
relay ask --agent uppercase --wait "hello team"
```

Or open [http://127.0.0.1:8787](http://127.0.0.1:8787).

## What 0.1 includes

- Capability publishing
- Asynchronous task submission and status
- Outbound-polling local runner
- Zero-modification stdin/stdout command adapter
- Minimal Web and CLI clients
- Explicit task transitions and structured errors

## Important security status

Version 0.1 proves the sharing model; it is not production-ready. Authentication, resource-level authorization, persistence, sandboxing, signed task grants, approvals, and secret scanning are planned but not implemented. Keep the Hub on localhost and read [SECURITY.md](SECURITY.md) before connecting real credentials.

## Roadmap

1. Durable SQLite/PostgreSQL task store and leases
2. OIDC identity, capability policy, and append-only audit events
3. Structured progress, questions, cancellation, and file artifacts
4. Container runner, sandboxing, and egress policy
5. A2A and MCP adapters
6. Multi-agent composition after the single-agent path is reliable

## Design principle

The core interface is deliberately small:

```text
publish(capability)
submit(task) -> task_id
watch(task_id) -> events/result
```

Everything else—queueing, leases, retries, routing, transport, storage, and protocol compatibility—belongs behind that interface.

Licensed under Apache-2.0.
