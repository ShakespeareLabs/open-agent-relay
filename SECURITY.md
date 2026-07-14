# Security

OpenAgentRelay 0.1 is a development preview, not a production security boundary.

## Core security model

- Agent code and credentials remain in the runner's execution environment.
- Runners make outbound connections to the Hub; the Hub does not open a shell on the runner.
- Capability manifests declare secret requirements but never contain secret values.
- Task inputs and agent outputs are untrusted data.

## Not implemented in 0.1

- Authentication and resource-level authorization
- Encrypted persistent storage
- Sandboxed command execution and network egress controls
- Signed manifests or task grants
- Log and artifact secret scanning
- Approval gates for write operations

Do not expose the 0.1 Hub to the public internet or attach production credentials to an untrusted agent command.

Report vulnerabilities privately to the project maintainers. Please do not open a public issue containing secrets or exploit details.

