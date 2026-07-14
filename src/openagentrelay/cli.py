from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time

from .client import RelayClient, RelayClientError
from .hub import serve
from .runner import serve_runner


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="relay", description="Share agent capabilities without shipping code or secrets.")
    sub = root.add_subparsers(dest="command", required=True)

    hub = sub.add_parser("hub", help="start a development Hub")
    hub.add_argument("--host", default="127.0.0.1")
    hub.add_argument("--port", type=_positive_int, default=8787)
    hub.add_argument("--access-key", help="client key; prefer RELAY_ACCESS_KEY")
    hub.add_argument("--runner-key", help="runner key; prefer RELAY_RUNNER_KEY")
    hub.add_argument("--lease-seconds", type=_positive_float, default=60)
    hub.add_argument("--max-request-bytes", type=_positive_int, default=1_048_576)
    hub.add_argument("--max-concurrency", type=_positive_int, default=32)

    expose = sub.add_parser("expose", help="publish and serve a local command")
    expose.add_argument("--hub", default="http://127.0.0.1:8787")
    expose.add_argument("--name", required=True)
    expose.add_argument("--description", default="")
    expose.add_argument("--runner-key", help="prefer RELAY_RUNNER_KEY")
    expose.add_argument("--request-timeout", type=_positive_float, default=30)
    expose.add_argument("--execution-timeout", type=_positive_int, default=600)
    expose.add_argument("--once", action="store_true")
    expose.add_argument("agent_command", nargs=argparse.REMAINDER)

    ask = sub.add_parser("ask", help="submit a task")
    ask.add_argument("--hub", default="http://127.0.0.1:8787")
    ask.add_argument("--agent", required=True)
    ask.add_argument("--access-key", help="prefer RELAY_ACCESS_KEY")
    ask.add_argument("--request-timeout", type=_positive_float, default=30)
    ask.add_argument("--wait-timeout", type=_positive_float, default=660)
    ask.add_argument("--max-attempts", type=_attempts, default=3)
    ask.add_argument("--wait", action="store_true")
    ask.add_argument("--json", action="store_true")
    ask.add_argument("prompt")

    sub.add_parser("version", help="show version")
    return root


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _validate_key(value: str, label: str) -> None:
    if len(value) < 16:
        raise SystemExit(f"{label} must contain at least 16 characters")


def _attempts(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 10:
        raise argparse.ArgumentTypeError("must be between 1 and 10")
    return parsed


def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except RelayClientError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from None


def _run() -> None:
    args = parser().parse_args()
    if args.command == "hub":
        client_key = args.access_key or os.getenv("RELAY_ACCESS_KEY") or secrets.token_urlsafe(24)
        runner_key = args.runner_key or os.getenv("RELAY_RUNNER_KEY") or secrets.token_urlsafe(24)
        _validate_key(client_key, "client key")
        _validate_key(runner_key, "runner key")
        if secrets.compare_digest(client_key, runner_key):
            raise SystemExit("client key and runner key must be different")
        print(f"Client key: {client_key}")
        print(f"Runner key: {runner_key}")
        serve(
            args.host,
            args.port,
            client_key=client_key,
            runner_key=runner_key,
            lease_seconds=args.lease_seconds,
            max_request_bytes=args.max_request_bytes,
            max_concurrency=args.max_concurrency,
        )
        return
    if args.command == "version":
        from . import __version__
        print(__version__)
        return

    if args.command == "expose":
        runner_key = args.runner_key or os.getenv("RELAY_RUNNER_KEY")
        if not runner_key:
            raise SystemExit("--runner-key or RELAY_RUNNER_KEY is required")
        _validate_key(runner_key, "runner key")
        client = RelayClient(args.hub, runner_key, timeout=args.request_timeout)
        command = args.agent_command
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            raise SystemExit("an agent command is required after --")
        client.publish(args.name, args.description)
        print(f"Published {args.name}; waiting for tasks.")
        serve_runner(
            client,
            args.name,
            command,
            once=args.once,
            execution_timeout=args.execution_timeout,
        )
        return
    if args.command == "ask":
        access_key = args.access_key or os.getenv("RELAY_ACCESS_KEY")
        if not access_key:
            raise SystemExit("--access-key or RELAY_ACCESS_KEY is required")
        _validate_key(access_key, "client key")
        client = RelayClient(args.hub, access_key, timeout=args.request_timeout)
        task = client.submit(args.agent, args.prompt, max_attempts=args.max_attempts)
        if not args.json:
            print(task["id"])
        if not args.wait:
            if args.json:
                print(json.dumps(task, ensure_ascii=False))
            return
        deadline = time.monotonic() + args.wait_timeout
        while time.monotonic() < deadline:
            task = client.get_task(task["id"])
            if task["status"] in {"completed", "failed", "cancelled"}:
                print(json.dumps(task, ensure_ascii=False, indent=None if args.json else 2))
                if task["status"] != "completed":
                    raise SystemExit(1)
                return
            time.sleep(0.5)
        print(json.dumps({"error": {"code": "WAIT_TIMEOUT", "message": "task did not finish before wait timeout"}}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
