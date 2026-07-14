from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence


class CommandFailed(RuntimeError):
    def __init__(self, detail: str):
        super().__init__("agent command failed")
        self.detail = detail


def run_command(command: Sequence[str], task_input: object, timeout: int = 600) -> str:
    value = task_input if isinstance(task_input, str) else json.dumps(task_input, ensure_ascii=False)
    completed = subprocess.run(
        list(command),
        input=value,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"command exited with {completed.returncode}"
        raise CommandFailed(detail)
    return completed.stdout.strip()
