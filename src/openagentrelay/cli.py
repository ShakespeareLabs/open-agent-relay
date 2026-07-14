from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import sys
from functools import partial
from pathlib import Path

from .client import RelayClient, RelayClientError
from .runner import run_command
from .server import serve


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="relay", description="Share agent capabilities without shipping code or secrets.")
    sub = root.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve", help="serve a local command directly over the network")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=_positive_int, default=8787)
    serve_parser.add_argument("--name", required=True)
    serve_parser.add_argument("--description", default="")
    serve_parser.add_argument("--access-key")
    serve_parser.add_argument("--execution-timeout", type=_positive_int, default=600)
    serve_parser.add_argument("--max-request-bytes", type=_positive_int, default=1_048_576)
    serve_parser.add_argument("--max-output-bytes", type=_positive_int, default=1_048_576)
    serve_parser.add_argument("--max-concurrency", type=_positive_int, default=4)
    serve_parser.add_argument("--conversation-ttl", type=_positive_int, default=3600)
    serve_parser.add_argument("agent_command", nargs=argparse.REMAINDER)

    ask = sub.add_parser("ask", help="call an agent directly")
    ask.add_argument("--target", required=True)
    ask.add_argument("--access-key", help="prefer RELAY_ACCESS_KEY to avoid shell history")
    ask.add_argument("--request-timeout", type=_positive_float)
    ask.add_argument("--caller-id")
    ask.add_argument("--expect-agent", help="refuse the call if the agent card has a different name")
    session = ask.add_mutually_exclusive_group()
    session.add_argument("--new-conversation", action="store_true")
    session.add_argument("--conversation")
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
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return parsed


def _validate_key(value: str) -> None:
    if len(value) < 16:
        raise SystemExit("access key must contain at least 16 characters")


def main() -> None:
    try:
        _run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except RelayClientError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from None
    except OSError as exc:
        print(
            json.dumps(
                {"error": {"status": None, "code": "LOCAL_ERROR", "message": str(exc)}},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


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
        configured_key = args.access_key or os.getenv("RELAY_ACCESS_KEY")
        access_key = configured_key or secrets.token_urlsafe(24)
        _validate_key(access_key)
        if configured_key:
            print("Access key: loaded from configuration", flush=True)
        else:
            print(f"Generated access key: {access_key}", flush=True)
        executor = partial(
            run_command,
            command,
            timeout=args.execution_timeout,
            max_output_bytes=args.max_output_bytes,
        )
        serve(
            args.host,
            args.port,
            name=args.name,
            description=args.description,
            executor=executor,
            access_key=access_key,
            execution_timeout=args.execution_timeout,
            max_request_bytes=args.max_request_bytes,
            max_output_bytes=args.max_output_bytes,
            max_concurrency=args.max_concurrency,
            conversation_ttl=args.conversation_ttl,
        )
        return
    if args.command == "ask":
        access_key = args.access_key or os.getenv("RELAY_ACCESS_KEY")
        if not access_key:
            raise SystemExit("--access-key or RELAY_ACCESS_KEY is required")
        _validate_key(access_key)
        uses_conversation = args.new_conversation or args.conversation
        caller_id = args.caller_id or os.getenv("RELAY_CALLER_ID")
        if uses_conversation and not caller_id:
            caller_id = _load_or_create_caller_id()
        client = RelayClient(args.target, access_key, caller_id=caller_id, timeout=args.request_timeout)
        if args.expect_agent:
            actual_agent = client.card().get("name")
            if actual_agent != args.expect_agent:
                raise RelayClientError(
                    409,
                    "AGENT_MISMATCH",
                    f"expected agent {args.expect_agent!r}, got {actual_agent!r}",
                )
        response = client.invoke(
            args.prompt,
            new_conversation=args.new_conversation,
            conversation_id=args.conversation,
        )
        if args.json:
            print(json.dumps(response, ensure_ascii=False, indent=2))
        else:
            print(response["result"])
            if response.get("conversation_id"):
                print(f"Conversation: {response['conversation_id']}", file=sys.stderr)


def _load_or_create_caller_id() -> str:
    root = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = root / "openagentrelay" / "caller-id"
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = f"caller_{secrets.token_urlsafe(18)}"
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return path.read_text().strip()
        with os.fdopen(descriptor, "w") as handle:
            handle.write(value + "\n")
        return value


if __name__ == "__main__":
    main()
