from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Sequence

from .client import RelayClient


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


def serve_runner(
    client: RelayClient,
    capability: str,
    command: Sequence[str],
    poll_interval: float = 1.0,
    once: bool = False,
) -> None:
    while True:
        task = client.request("POST", "/v1/runners/claim", {"capability": capability})
        if task is None:
            if once:
                return
            time.sleep(poll_interval)
            continue
        try:
            result = run_command(command, task["input"])
            client.request("POST", f"/v1/tasks/{task['id']}/complete", {"result": result})
        except CommandFailed as exc:
            print(f"Task {task['id']} failed locally: {exc.detail}")
            client.request("POST", f"/v1/tasks/{task['id']}/fail", {"error": str(exc)})
        except Exception as exc:
            client.request("POST", f"/v1/tasks/{task['id']}/fail", {"error": str(exc)})
        if once:
            return
