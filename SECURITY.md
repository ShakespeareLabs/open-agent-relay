# Security

OpenAgentRelay 0.1 is a development preview for trusted local networks, not a production security boundary.

## Core security model

- Agent code and business credentials remain on the machine serving the agent.
- A caller sends an input and receives an output; it does not receive the command, environment, or business credentials.
- Every invocation requires a shared access key. If the author does not provide one, the CLI generates a temporary key at startup.
- Task inputs and agent outputs are untrusted data.

## Network warning

Version 0.1 uses a shared bearer key over plain HTTP. The key prevents unauthenticated calls, but it does not encrypt traffic or identify individual users. Use it only on a trusted LAN. Do not expose the port directly to the public internet, and do not connect production write operations or sensitive data.

## Not implemented in 0.1

- Encrypted transport (TLS)
- Per-user identity and resource-level authorization
- Sandboxed command execution and network egress controls
- Rate limiting and request size limits
- Signed requests
- Log and output secret scanning
- Approval gates for write operations

Do not expose the 0.1 server to the public internet or attach production credentials to an untrusted agent command.

Report vulnerabilities privately to the project maintainers. Please do not open a public issue containing secrets or exploit details.
