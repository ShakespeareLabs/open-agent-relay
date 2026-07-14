import json
import subprocess
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openagentrelay.client import RelayClient
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


if __name__ == "__main__":
    unittest.main()
