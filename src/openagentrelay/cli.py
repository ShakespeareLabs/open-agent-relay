from __future__ import annotations

import argparse
import json
import time

from .client import RelayClient
from .hub import serve
from .runner import serve_runner


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="relay", description="Share agent capabilities without shipping code or secrets.")
    sub = root.add_subparsers(dest="command", required=True)

    hub = sub.add_parser("hub", help="start a development Hub")
    hub.add_argument("--host", default="127.0.0.1")
    hub.add_argument("--port", type=int, default=8787)

    expose = sub.add_parser("expose", help="publish and serve a local command")
    expose.add_argument("--hub", default="http://127.0.0.1:8787")
    expose.add_argument("--name", required=True)
    expose.add_argument("--description", default="")
    expose.add_argument("--once", action="store_true")
    expose.add_argument("agent_command", nargs=argparse.REMAINDER)

    ask = sub.add_parser("ask", help="submit a task")
    ask.add_argument("--hub", default="http://127.0.0.1:8787")
    ask.add_argument("--agent", required=True)
    ask.add_argument("--wait", action="store_true")
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
    if args.command == "hub":
        serve(args.host, args.port)
        return
    if args.command == "version":
        from . import __version__
        print(__version__)
        return

    client = RelayClient(args.hub)
    if args.command == "expose":
        command = args.agent_command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise SystemExit("an agent command is required after --")
        client.publish(args.name, args.description)
        print(f"Published {args.name}; waiting for tasks.")
        serve_runner(client, args.name, command, once=args.once)
        return
    if args.command == "ask":
        task = client.submit(args.agent, args.prompt)
        print(task["id"])
        if not args.wait:
            return
        while True:
            task = client.get_task(task["id"])
            if task["status"] in {"completed", "failed", "cancelled"}:
                print(json.dumps(task, ensure_ascii=False, indent=2))
                return
            time.sleep(0.5)


if __name__ == "__main__":
    main()
