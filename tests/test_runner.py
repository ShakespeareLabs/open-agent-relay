import sys
import unittest

from openagentrelay.runner import CommandFailed, run_command


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


if __name__ == "__main__":
    unittest.main()
