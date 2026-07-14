from __future__ import annotations

import argparse
import json
import os
import secrets
from functools import partial

from .client import RelayClient
from .runner import run_command
from .server import serve


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="relay", description="Share agent capabilities without shipping code or secrets.")
    sub = root.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="serve a local command directly over the network")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.add_argument("--name", required=True)
    serve_parser.add_argument("--description", default="")
    serve_parser.add_argument("--access-key")
    serve_parser.add_argument("agent_command", nargs=argparse.REMAINDER)

    ask = sub.add_parser("ask", help="call an agent directly")
    ask.add_argument("--target", required=True)
    ask.add_argument("--access-key")
    ask.add_argument("--json", action="store_true")
    ask.add_argument("prompt")

    sub.add_parser("version", help="show version")
    return root


def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        print("\nStopped.")


def _run() -> None:
    args = parser().parse_args()
    if args.command == "version":
        from . import __version__
        print(__version__)
        return

    if args.command == "serve":
        command = args.agent_command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise SystemExit("an agent command is required after --")
        access_key = args.access_key or os.getenv("RELAY_ACCESS_KEY") or secrets.token_urlsafe(24)
        print(f"Access key: {access_key}")
        executor = partial(run_command, command)
        serve(
            args.host,
            args.port,
            name=args.name,
            description=args.description,
            executor=executor,
            access_key=access_key,
        )
        return
    if args.command == "ask":
        access_key = args.access_key or os.getenv("RELAY_ACCESS_KEY")
        if not access_key:
            raise SystemExit("--access-key or RELAY_ACCESS_KEY is required")
        client = RelayClient(args.target, access_key)
        response = client.invoke(args.prompt)
        if args.json:
            print(json.dumps(response, ensure_ascii=False, indent=2))
        else:
            print(response["result"])


if __name__ == "__main__":
    main()
