from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Capability:
    name: str
    description: str = ""
    owner: str = "local"
    risk: str = "read-only"
    online: bool = True
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    capability: str
    input: Any
    requester: str = "anonymous"
    id: str = field(default_factory=lambda: f"task_{uuid4().hex[:12]}")
    status: TaskStatus = TaskStatus.PENDING
    result: Any | None = None
    error: str | None = None
    attempt: int = 0
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def touch(self) -> None:
        self.updated_at = now_iso()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

