from __future__ import annotations

from threading import Condition, RLock

from .models import Capability, Task, TaskStatus


class StoreError(Exception):
    pass


class NotFound(StoreError):
    pass


class Conflict(StoreError):
    pass


class InMemoryStore:
    """Thread-safe development store behind the Hub interface."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._tasks: dict[str, Task] = {}
        self._lock = RLock()
        self._available = Condition(self._lock)

    def publish(self, capability: Capability) -> Capability:
        if not capability.name.strip():
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
            self._tasks[task.id] = task
            self._available.notify_all()
            return task

    def get(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as exc:
                raise NotFound(f"unknown task: {task_id}") from exc

    def claim(self, capability: str) -> Task | None:
        with self._lock:
            for task in self._tasks.values():
                if task.capability == capability and task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.RUNNING
                    task.attempt += 1
                    task.touch()
                    return task
            return None

    def complete(self, task_id: str, result: object) -> Task:
        with self._lock:
            task = self.get(task_id)
            if task.status != TaskStatus.RUNNING:
                raise Conflict(f"task is {task.status}, expected running")
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.touch()
            return task

    def fail(self, task_id: str, error: str) -> Task:
        with self._lock:
            task = self.get(task_id)
            if task.status != TaskStatus.RUNNING:
                raise Conflict(f"task is {task.status}, expected running")
            task.error = error
            task.status = TaskStatus.FAILED
            task.touch()
            return task

