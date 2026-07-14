from __future__ import annotations

from threading import Condition, RLock
import secrets
import time
from datetime import UTC, datetime, timedelta

from .models import Capability, Task, TaskStatus


class StoreError(Exception):
    pass


class NotFound(StoreError):
    pass


class Conflict(StoreError):
    pass


class InMemoryStore:
    """Thread-safe development store behind the Hub interface."""

    def __init__(self, lease_seconds: float = 60) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._tasks: dict[str, Task] = {}
        self._lock = RLock()
        self._available = Condition(self._lock)
        self.lease_seconds = lease_seconds
        self._lease_deadlines: dict[str, float] = {}

    def publish(self, capability: Capability) -> Capability:
        if not isinstance(capability.name, str) or not capability.name.strip():
            raise ValueError("capability name is required")
        with self._lock:
            self._capabilities[capability.name] = capability
            return capability

    def list_capabilities(self) -> list[Capability]:
        with self._lock:
            return sorted(self._capabilities.values(), key=lambda item: item.name)

    def submit(self, task: Task) -> Task:
        with self._available:
            if task.capability not in self._capabilities:
                raise NotFound(f"unknown capability: {task.capability}")
            if task.max_attempts < 1 or task.max_attempts > 10:
                raise ValueError("max_attempts must be between 1 and 10")
            self._tasks[task.id] = task
            self._available.notify_all()
            return task

    def get(self, task_id: str) -> Task:
        with self._lock:
            self._requeue_expired()
            try:
                return self._tasks[task_id]
            except KeyError as exc:
                raise NotFound(f"unknown task: {task_id}") from exc

    def claim(self, capability: str) -> Task | None:
        with self._lock:
            if not isinstance(capability, str) or not capability:
                raise ValueError("capability name must be a non-empty string")
            self._requeue_expired()
            for task in self._tasks.values():
                if task.capability == capability and task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.RUNNING
                    task.attempt += 1
                    task.lease_id = f"lease_{secrets.token_urlsafe(18)}"
                    self._extend_lease(task)
                    task.touch()
                    return task
            return None

    def heartbeat(self, task_id: str, lease_id: str) -> Task:
        with self._lock:
            task = self.get(task_id)
            self._require_lease(task, lease_id)
            self._extend_lease(task)
            task.touch()
            return task

    def complete(self, task_id: str, result: object, lease_id: str) -> Task:
        with self._lock:
            task = self.get(task_id)
            if task.status == TaskStatus.COMPLETED and task.lease_id == lease_id:
                if task.result == result:
                    return task
                raise Conflict("task was already completed with a different result")
            self._require_lease(task, lease_id)
            if task.status != TaskStatus.RUNNING:
                raise Conflict(f"task is {task.status}, expected running")
            task.result = result
            task.error = None
            task.status = TaskStatus.COMPLETED
            task.touch()
            self._lease_deadlines.pop(task.id, None)
            return task

    def fail(self, task_id: str, error: str, lease_id: str, *, retryable: bool = True) -> Task:
        with self._lock:
            task = self.get(task_id)
            if task.last_failure_lease_id == lease_id and task.last_failure_error == error:
                return task
            if task.status == TaskStatus.FAILED and task.lease_id == lease_id and task.error == error:
                return task
            self._require_lease(task, lease_id)
            if task.status != TaskStatus.RUNNING:
                raise Conflict(f"task is {task.status}, expected running")
            task.error = error
            task.last_failure_lease_id = lease_id
            task.last_failure_error = error
            self._lease_deadlines.pop(task.id, None)
            if retryable and task.attempt < task.max_attempts:
                task.status = TaskStatus.PENDING
                task.lease_id = None
                task.lease_expires_at = None
                self._available.notify_all()
            else:
                task.status = TaskStatus.FAILED
            task.touch()
            return task

    def _extend_lease(self, task: Task) -> None:
        self._lease_deadlines[task.id] = time.monotonic() + self.lease_seconds
        task.lease_expires_at = (datetime.now(UTC) + timedelta(seconds=self.lease_seconds)).isoformat()

    def _require_lease(self, task: Task, lease_id: str) -> None:
        if task.status != TaskStatus.RUNNING:
            raise Conflict(f"task is {task.status}, expected running")
        if not lease_id or task.lease_id != lease_id:
            raise Conflict("task lease is missing, stale, or belongs to another runner")

    def _requeue_expired(self) -> None:
        now = time.monotonic()
        for task in self._tasks.values():
            deadline = self._lease_deadlines.get(task.id)
            if task.status != TaskStatus.RUNNING or deadline is None or deadline > now:
                continue
            self._lease_deadlines.pop(task.id, None)
            task.error = "runner lease expired"
            task.lease_id = None
            task.lease_expires_at = None
            task.status = TaskStatus.PENDING if task.attempt < task.max_attempts else TaskStatus.FAILED
            task.touch()
