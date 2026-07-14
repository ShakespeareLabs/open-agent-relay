# Security

OpenAgentRelay 0.1 is a development preview, not a production security boundary.

## Core security model

- Agent code and credentials remain in the runner's execution environment.
- Runners make outbound connections to the Hub; the Hub does not open a shell on the runner.
- A Client Key authorizes capability listing, task submission, and task reads.
- A separate Runner Key authorizes capability publication, task claims, heartbeats, and terminal updates.
- Request size and Hub concurrency are bounded, while task leases and attempts are finite.
- Task inputs and agent outputs are untrusted data.

Prefer `RELAY_ACCESS_KEY` and `RELAY_RUNNER_KEY` over command-line key arguments so secrets do not appear in process arguments or shell history. Role keys authenticate a role, not an individual person. Use different random values for the two roles and rotate both if either is exposed.

Leases provide at-least-once execution, not exactly-once side effects. A retried write can run more than once if a Runner loses its lease after the external system accepted the write. Keep this preview read-only or require idempotency keys and human approval in the underlying agent.

## Not implemented in 0.1

- Per-user identity and resource-level authorization
- TLS transport encryption
- Encrypted persistent storage
- Sandboxed command execution and network egress controls
- Signed manifests or task grants
- Log and artifact secret scanning
- Approval gates for write operations

Do not expose the 0.1 Hub to the public internet or attach production credentials to an untrusted agent command.

Report vulnerabilities privately to the project maintainers. Please do not open a public issue containing secrets or exploit details.
