import sys
import unittest

from openagentrelay.client import RelayClientError
from openagentrelay.runner import CommandFailed, _post_final, run_command


class RunnerTests(unittest.TestCase):
    def test_command_receives_stdin_and_returns_stdout(self) -> None:
        output = run_command(
            [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
            "hello agent",
        )
        self.assertEqual(output, "HELLO AGENT")

    def test_nonzero_exit_is_an_error(self) -> None:
        with self.assertRaises(CommandFailed) as raised:
            run_command(
                [sys.executable, "-c", "import sys; print('broken', file=sys.stderr); raise SystemExit(2)"],
                "hello",
            )
        self.assertEqual(str(raised.exception), "agent command failed")
        self.assertEqual(raised.exception.detail, "broken")

    def test_final_update_retries_transient_network_error(self) -> None:
        class FakeClient:
            calls = 0

            def request(self, method, path, data):
                self.calls += 1
                if self.calls == 1:
                    raise RelayClientError(None, "CONNECTION_ERROR", "lost response")
                return {"status": "completed"}

        client = FakeClient()
        _post_final(client, "/complete", {"result": "done"})
        self.assertEqual(client.calls, 2)


if __name__ == "__main__":
    unittest.main()
