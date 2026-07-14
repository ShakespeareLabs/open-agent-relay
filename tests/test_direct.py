import contextlib
import io
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openagentrelay.cli import parser
from openagentrelay import cli
from openagentrelay.client import RelayClient
from openagentrelay.runner import CommandOutputTooLarge
from openagentrelay.server import DirectServer


class DirectModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = DirectServer(
            ("127.0.0.1", 0),
            name="uppercase",
            description="Turn text into uppercase",
            executor=lambda value: str(value).upper(),
            access_key="team-secret",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.target = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def test_agent_card_is_public(self) -> None:
        client = RelayClient(self.target, "unused-for-public-card")
        card = client.card()
        self.assertEqual(card["name"], "uppercase")
        self.assertEqual(card["authentication"], "bearer")
        self.assertEqual(card["limits"]["execution_timeout_seconds"], 600)
        self.assertEqual(card["limits"]["max_output_bytes"], 1_048_576)

    def test_authorized_caller_can_invoke(self) -> None:
        client = RelayClient(self.target, "team-secret")
        response = client.invoke("hello team")
        self.assertEqual(response["result"], "HELLO TEAM")

    def test_missing_key_is_rejected(self) -> None:
        request = Request(
            f"{self.target}/v1/invoke",
            data=json.dumps({"input": "hello team"}).encode(),
            method="POST",
            headers={"content-type": "application/json"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

    def test_wrong_key_is_rejected(self) -> None:
        client = RelayClient(self.target, "wrong-key")
        with self.assertRaisesRegex(RuntimeError, "UNAUTHORIZED"):
            client.invoke("hello team")

    def test_missing_input_is_rejected(self) -> None:
        request = Request(
            f"{self.target}/v1/invoke",
            data=b"{}",
            method="POST",
            headers={
                "content-type": "application/json",
                "authorization": "Bearer team-secret",
            },
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_null_body_is_rejected_as_bad_request(self) -> None:
        request = Request(
            f"{self.target}/v1/invoke",
            data=b"null",
            method="POST",
            headers={"content-type": "application/json", "authorization": "Bearer team-secret"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_request_size_limit_is_enforced(self) -> None:
        self.server.max_request_bytes = 16
        request = Request(
            f"{self.target}/v1/invoke",
            data=json.dumps({"input": "long request"}).encode(),
            method="POST",
            headers={"content-type": "application/json", "authorization": "Bearer team-secret"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 413)
        raised.exception.close()

    def test_new_conversation_keeps_context_for_same_caller(self) -> None:
        seen: list[object] = []

        def executor(value: object) -> str:
            seen.append(value)
            return f"answer-{len(seen)}"

        self.server.executor = executor
        client = RelayClient(self.target, "team-secret", caller_id="caller-a")
        first = client.invoke("first question", new_conversation=True)
        second = client.invoke("follow up", conversation_id=first["conversation_id"])
        self.assertEqual(first["result"], "answer-1")
        self.assertEqual(second["result"], "answer-2")
        self.assertEqual(seen[0], "first question")
        self.assertIn("User: first question", str(seen[1]))
        self.assertIn("Assistant: answer-1", str(seen[1]))
        self.assertIn("User: follow up", str(seen[1]))

    def test_conversation_is_bound_to_caller(self) -> None:
        owner = RelayClient(self.target, "team-secret", caller_id="caller-a")
        conversation = owner.invoke("private context", new_conversation=True)["conversation_id"]
        other = RelayClient(self.target, "team-secret", caller_id="caller-b")
        with self.assertRaisesRegex(RuntimeError, "CONVERSATION_FORBIDDEN"):
            other.invoke("show context", conversation_id=conversation)

    def test_execution_timeout_is_structured(self) -> None:
        def timeout(_: object) -> object:
            raise subprocess.TimeoutExpired(["agent"], 1)

        self.server.executor = timeout
        client = RelayClient(self.target, "team-secret")
        with self.assertRaisesRegex(RuntimeError, "EXECUTION_TIMEOUT"):
            client.invoke("slow")

    def test_concurrency_limit_returns_busy(self) -> None:
        started = threading.Event()
        release = threading.Event()

        def slow(value: object) -> object:
            started.set()
            release.wait(2)
            return value

        self.server.executor = slow
        self.server.execution_slots = threading.BoundedSemaphore(1)
        first = threading.Thread(target=lambda: RelayClient(self.target, "team-secret").invoke("first"))
        first.start()
        self.assertTrue(started.wait(1))
        try:
            with self.assertRaisesRegex(RuntimeError, "BUSY"):
                RelayClient(self.target, "team-secret").invoke("second")
        finally:
            release.set()
            first.join(2)

    def test_busy_new_conversation_does_not_leave_orphan(self) -> None:
        started = threading.Event()
        release = threading.Event()

        def slow(value: object) -> object:
            started.set()
            release.wait(2)
            return value

        self.server.executor = slow
        self.server.execution_slots = threading.BoundedSemaphore(1)
        first = threading.Thread(target=lambda: RelayClient(self.target, "team-secret").invoke("first"))
        first.start()
        self.assertTrue(started.wait(1))
        try:
            with self.assertRaisesRegex(RuntimeError, "BUSY"):
                RelayClient(self.target, "team-secret", caller_id="caller-a").invoke(
                    "second",
                    new_conversation=True,
                )
            self.assertEqual(len(self.server.conversations), 0)
        finally:
            release.set()
            first.join(2)

    def test_failed_new_conversation_does_not_leave_orphan(self) -> None:
        def fail(_: object) -> object:
            raise RuntimeError("broken")

        self.server.executor = fail
        with self.assertRaisesRegex(RuntimeError, "EXECUTION_FAILED"):
            RelayClient(self.target, "team-secret", caller_id="caller-a").invoke(
                "hello",
                new_conversation=True,
            )
        self.assertEqual(len(self.server.conversations), 0)

    def test_output_limit_error_is_structured(self) -> None:
        def oversized(_: object) -> object:
            raise CommandOutputTooLarge(1024)

        self.server.executor = oversized
        with self.assertRaisesRegex(RuntimeError, "OUTPUT_TOO_LARGE"):
            RelayClient(self.target, "team-secret").invoke("hello")


class ClientValidationTests(unittest.TestCase):
    def test_configured_key_is_not_printed(self) -> None:
        secret = "configured-secret-key"
        output = io.StringIO()
        argv = [
            "relay",
            "serve",
            "--name",
            "test",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
        with (
            mock.patch.dict(os.environ, {"RELAY_ACCESS_KEY": secret}, clear=True),
            mock.patch.object(sys, "argv", argv),
            mock.patch("openagentrelay.cli.serve"),
            contextlib.redirect_stdout(output),
        ):
            cli.main()
        self.assertNotIn(secret, output.getvalue())
        self.assertIn("loaded from configuration", output.getvalue())

    def test_non_finite_request_timeout_is_rejected_by_cli(self) -> None:
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser().parse_args(
                    [
                        "ask",
                        "--target",
                        "http://127.0.0.1:8787",
                        f"--request-timeout={value}",
                        "hello",
                    ]
                )

    def test_target_requires_http_url(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "INVALID_TARGET"):
            RelayClient("127.0.0.1:8787", "team-secret")

    def test_programmatic_timeout_must_be_finite_and_positive(self) -> None:
        for value in (float("nan"), float("inf"), 0, -1):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "INVALID_TIMEOUT"):
                RelayClient("http://127.0.0.1:8787", "team-secret", timeout=value)

    def test_invalid_success_response_is_structured(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                self._send(json.dumps({"name": "test", "limits": {"execution_timeout_seconds": 1}}).encode())

            def do_POST(self) -> None:
                self._send(b"not-json")

            def _send(self, body: bytes) -> None:
                self.send_response(200)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = RelayClient(f"http://127.0.0.1:{server.server_port}", "team-secret")
            with self.assertRaisesRegex(RuntimeError, "INVALID_RESPONSE"):
                client.invoke("hello")
        finally:
            server.shutdown()
            server.server_close()

    def test_non_object_agent_card_is_structured(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                body = b"[]"
                self.send_response(200)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = RelayClient(f"http://127.0.0.1:{server.server_port}", "team-secret")
            with self.assertRaisesRegex(RuntimeError, "INVALID_AGENT_CARD"):
                client.card()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
