import json
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
        with self.assertRaisesRegex(RuntimeError, "Agent returned 401"):
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


if __name__ == "__main__":
    unittest.main()
