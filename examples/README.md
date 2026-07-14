# End-to-end examples

These examples turn a local command into a capability that another computer or agent can call through `relay`.

| Example | What stays local | External dependency |
|---|---|---|
| [Read-only campaign report](read-only-campaign-report/) | Source CSV and report code | None |
| [Codex read-only review](codex-read-only-review/) | Repository, Codex config, and credentials | Codex CLI |
| [Claude Code read-only review](claude-read-only-review/) | Repository, Claude Code config, and credentials | Claude Code CLI |

Start with the campaign report because it is deterministic and has no model dependency. The Agent examples deliberately use read-only modes and dedicated workspaces.

All examples inherit the Alpha security boundary: trusted LAN only, plain HTTP, one shared key, no sensitive input, and no production write operations. Read [SECURITY.md](../SECURITY.md) first.
