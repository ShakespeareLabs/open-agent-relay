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
