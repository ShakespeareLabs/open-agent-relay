from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from collections.abc import Sequence
from typing import BinaryIO


class CommandFailed(RuntimeError):
    def __init__(self, detail: str):
        super().__init__("agent command failed")
        self.detail = detail


class CommandOutputTooLarge(RuntimeError):
    def __init__(self, limit: int):
        super().__init__(f"agent output exceeded {limit} bytes")
        self.limit = limit


def run_command(
    command: Sequence[str],
    task_input: object,
    timeout: int = 600,
    max_output_bytes: int = 1_048_576,
) -> str:
    value = task_input if isinstance(task_input, str) else json.dumps(task_input, ensure_ascii=False)
    with (
        tempfile.TemporaryFile() as task_input_file,
        tempfile.TemporaryFile() as stdout_file,
        tempfile.TemporaryFile() as stderr_file,
    ):
        task_input_file.write(value.encode())
        task_input_file.seek(0)
        environment = os.environ.copy()
        for name in ("RELAY_ACCESS_KEY", "RELAY_CALLER_ID", "RELAY_RUNNER_KEY"):
            environment.pop(name, None)
        process = subprocess.Popen(
            list(command),
            stdin=task_input_file,
            stdout=stdout_file,
            stderr=stderr_file,
            env=environment,
        )
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if _output_size(stdout_file, stderr_file) > max_output_bytes:
                process.kill()
                process.wait()
                raise CommandOutputTooLarge(max_output_bytes)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(list(command), timeout)
            try:
                process.wait(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                pass
        if _output_size(stdout_file, stderr_file) > max_output_bytes:
            raise CommandOutputTooLarge(max_output_bytes)
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode(errors="replace")
        stderr = stderr_file.read().decode(errors="replace")
        if process.returncode != 0:
            detail = stderr.strip() or f"command exited with {process.returncode}"
            raise CommandFailed(detail)
        return stdout.strip()


def _output_size(stdout_file: BinaryIO, stderr_file: BinaryIO) -> int:
    return os.fstat(stdout_file.fileno()).st_size + os.fstat(stderr_file.fileno()).st_size
