import json
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from openagentrelay.hub import RelayServer


class HubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = RelayServer(("127.0.0.1", 0), client_key="client-key", runner_key="runner-key")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def request(self, method: str, path: str, body: object | None = None, key: str = "client-key"):
        data = None if body is None else json.dumps(body).encode()
        request = Request(
            self.base + path,
            data=data,
            method=method,
            headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        )
        with urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_publish_submit_claim_complete(self) -> None:
        status, _ = self.request("POST", "/v1/capabilities", {"name": "echo"}, key="runner-key")
        self.assertEqual(status, 201)
        _, task = self.request("POST", "/v1/tasks", {"capability": "echo", "input": "hello"})
        _, claimed = self.request("POST", "/v1/runners/claim", {"capability": "echo"}, key="runner-key")
        self.assertEqual(claimed["id"], task["id"])
        _, completed = self.request(
            "POST",
            f"/v1/tasks/{task['id']}/complete",
            {"result": "HELLO", "lease_id": claimed["lease_id"]},
            key="runner-key",
        )
        self.assertEqual(completed["status"], "completed")
        _, public = self.request("GET", f"/v1/tasks/{task['id']}")
        self.assertNotIn("lease_id", public)

    def test_missing_authentication_is_rejected(self) -> None:
        request = Request(self.base + "/v1/capabilities")
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

    def test_client_key_cannot_claim_tasks(self) -> None:
        request = Request(
            self.base + "/v1/runners/claim",
            data=b'{"capability":"echo"}',
            method="POST",
            headers={"content-type": "application/json", "authorization": "Bearer client-key"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 403)
        raised.exception.close()

    def test_null_body_returns_structured_bad_request(self) -> None:
        request = Request(
            self.base + "/v1/tasks",
            data=b"null",
            method="POST",
            headers={"content-type": "application/json", "authorization": "Bearer client-key"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        body = json.loads(raised.exception.read())
        self.assertEqual(body["error"]["code"], "INVALID_REQUEST")
        raised.exception.close()

    def test_non_string_capability_name_is_bad_request(self) -> None:
        request = Request(
            self.base + "/v1/capabilities",
            data=b'{"name":123}',
            method="POST",
            headers={"content-type": "application/json", "authorization": "Bearer runner-key"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()


if __name__ == "__main__":
    unittest.main()
