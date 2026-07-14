import subprocess
import sys
import unittest
from unittest import mock

from openagentrelay.runner import CommandFailed, CommandOutputTooLarge, run_command


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

    def test_output_limit_stops_oversized_command(self) -> None:
        with self.assertRaises(CommandOutputTooLarge):
            run_command(
                [sys.executable, "-c", "print('x' * 100000)"],
                "hello",
                max_output_bytes=1024,
            )

    def test_timeout_stops_command(self) -> None:
        with self.assertRaises(subprocess.TimeoutExpired):
            run_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                "hello",
                timeout=0.05,
            )

    def test_relay_credentials_are_not_passed_to_agent_command(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import os; print(os.getenv('RELAY_ACCESS_KEY', ''))",
        ]
        with mock.patch.dict("os.environ", {"RELAY_ACCESS_KEY": "do-not-expose"}):
            output = run_command(command, "hello")
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
