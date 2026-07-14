from __future__ import annotations

import json
import subprocess
import threading
import time
from collections.abc import Sequence

from .client import RelayClient, RelayClientError


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
    execution_timeout: int = 600,
) -> None:
    while True:
        task = client.request("POST", "/v1/runners/claim", {"capability": capability})
        if task is None:
            if once:
                return
            time.sleep(poll_interval)
            continue
        stop_heartbeat = threading.Event()
        heartbeat_errors: list[Exception] = []
        lease_seconds = float(task.get("lease_seconds", 60))

        def heartbeat() -> None:
            interval = max(0.1, min(30.0, lease_seconds / 3))
            while not stop_heartbeat.wait(interval):
                try:
                    client.request(
                        "POST",
                        f"/v1/tasks/{task['id']}/heartbeat",
                        {"lease_id": task["lease_id"]},
                    )
                except Exception as exc:
                    if isinstance(exc, RelayClientError) and (
                        exc.status is None or exc.status == 429 or exc.status >= 500
                    ):
                        continue
                    heartbeat_errors.append(exc)
                    return

        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        result: object | None = None
        execution_error: str | None = None
        try:
            result = run_command(command, task["input"], timeout=execution_timeout)
        except CommandFailed as exc:
            print(f"Task {task['id']} failed locally: {exc.detail}")
            execution_error = "agent command failed"
        except subprocess.TimeoutExpired:
            print(f"Task {task['id']} timed out locally after {execution_timeout} seconds")
            execution_error = "agent execution timed out"
        except Exception as exc:
            print(f"Task {task['id']} failed locally: {exc}")
            execution_error = "agent execution failed"
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=1)

        if execution_error is None:
            _post_final(
                client,
                f"/v1/tasks/{task['id']}/complete",
                {"result": result, "lease_id": task["lease_id"]},
            )
        else:
            _post_final(
                client,
                f"/v1/tasks/{task['id']}/fail",
                {"error": execution_error, "lease_id": task["lease_id"], "retryable": True},
            )
        if heartbeat_errors:
            print(f"Task {task['id']} heartbeat failed locally: {heartbeat_errors[-1]}")
        if once:
            return


def _post_final(client: RelayClient, path: str, data: dict[str, object], attempts: int = 3) -> None:
    for attempt in range(attempts):
        try:
            client.request(
                "POST",
                path,
                data,
            )
            return
        except RelayClientError as exc:
            retryable = exc.status is None or exc.status >= 500
            if not retryable or attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))
