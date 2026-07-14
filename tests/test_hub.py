import json
import threading
import unittest
from urllib.request import Request, urlopen

from openagentrelay.hub import RelayServer


class HubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = RelayServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def request(self, method: str, path: str, body: object | None = None):
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, method=method, headers={"content-type": "application/json"})
        with urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_publish_submit_claim_complete(self) -> None:
        status, _ = self.request("POST", "/v1/capabilities", {"name": "echo"})
        self.assertEqual(status, 201)
        _, task = self.request("POST", "/v1/tasks", {"capability": "echo", "input": "hello"})
        _, claimed = self.request("POST", "/v1/runners/claim", {"capability": "echo"})
        self.assertEqual(claimed["id"], task["id"])
        _, completed = self.request("POST", f"/v1/tasks/{task['id']}/complete", {"result": "HELLO"})
        self.assertEqual(completed["status"], "completed")


if __name__ == "__main__":
    unittest.main()

