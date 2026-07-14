# Contributing

OpenAgentRelay is in its first design phase. Before adding a framework or infrastructure dependency, explain which user problem it removes.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Keep the default path dependency-free and local-first. New execution, identity, storage, and protocol implementations should sit behind explicit adapters.

