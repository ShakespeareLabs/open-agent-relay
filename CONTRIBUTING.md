# Contributing

OpenAgentRelay is in its first design phase. Before adding a framework or infrastructure dependency, explain which user problem it removes.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Keep the default path dependency-free, local-first, and Hub-free. The `main` branch is for direct local-network access; the `hub-mode` branch preserves the asynchronous Hub experiment. New execution, identity, and protocol implementations should sit behind explicit adapters.

## Release checks

Build release artifacts from a fresh checkout. Setuptools can reuse an ignored `build/` directory, so a working tree that previously built another branch must not be used as the release source.

Before tagging a release:

```bash
rm -rf build dist src/*.egg-info
python -m pip wheel . --no-deps -w dist
python -m unittest discover -s tests -v
```

Install the wheel in a new virtual environment, run the tests against that installed package, and confirm the wheel contains only the modules tracked on the release branch.

Releases are published by `.github/workflows/publish.yml` through PyPI Trusted Publishing. The GitHub release tag must exactly match `v<project.version>`, for example `v0.1.0`. The workflow builds both a wheel and source distribution, checks their metadata, and uploads only from the protected `pypi` environment.

For the first release, register a pending PyPI publisher with these exact values before publishing the GitHub release:

| Field | Value |
|---|---|
| PyPI project | `open-agent-relay` |
| Owner | `ShakespeareLabs` |
| Repository | `open-agent-relay` |
| Workflow | `publish.yml` |
| Environment | `pypi` |
