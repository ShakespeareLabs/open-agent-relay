# Security

OpenAgentRelay 0.1 is a development preview for trusted local networks, not a production security boundary.

## Core security model

- Agent code and business credentials remain on the machine serving the agent.
- A caller sends an input and receives an output; it does not receive the command, environment, or business credentials.
- Every invocation requires a shared access key. If the author does not provide one, the CLI generates a temporary key at startup.
- The server enforces configurable request-size, execution-time, and execution-concurrency limits.
- The command adapter enforces a combined stdout/stderr size limit and stops oversized commands.
- Task inputs and agent outputs are untrusted data.

## Network warning

Version 0.1 uses a shared bearer key over plain HTTP. The key prevents unauthenticated calls, but it does not encrypt traffic or identify individual users. Use it only on a trusted LAN. Do not expose the port directly to the public internet, and do not connect production write operations or sensitive data.

Prefer `RELAY_ACCESS_KEY` over `--access-key` so the key is not stored in shell history or exposed in process arguments. Relay-managed conversations use a random local caller ID to prevent accidental cross-caller continuation, but caller IDs are not authenticated identities and can be spoofed by someone who already has the shared access key.

Relay removes its own `RELAY_ACCESS_KEY`, `RELAY_CALLER_ID`, and `RELAY_RUNNER_KEY` variables from the child command's environment. Other environment variables are inherited because the local Agent may need its own business credentials; publishers remain responsible for minimizing those credentials.

## Publisher isolation

Keeping credentials on the publisher's machine does not guarantee that an Agent cannot disclose or misuse them. A caller controls the request, and a capable Agent can read files, call tools, access the network, or return data available to its process.

- Create a dedicated workspace for each published capability.
- Give the process only the files, Skills, MCP servers, network access, and credentials it needs.
- Prefer read-only credentials and read-only Agent sandbox settings.
- Do not publish an everyday general-purpose Agent that has access to personal files or broad business credentials.
- Keep write operations disabled, or enforce idempotency and human approval inside the underlying Agent.

## Not implemented in 0.1

- Encrypted transport (TLS)
- Per-user identity and resource-level authorization
- Sandboxed command execution and network egress controls
- Per-user rate limits
- Signed requests
- Log and output secret scanning
- Approval gates for write operations
- HTTP connection limits and protection against hostile slow clients

Do not expose the 0.1 server to the public internet or attach production credentials to an untrusted agent command.

Use the repository's GitHub Security page to contact the maintainers about vulnerabilities. Do not open a public issue containing secrets, credentials, personal data, or exploit details. Maintainers should enable GitHub private vulnerability reporting before the public Alpha announcement.
