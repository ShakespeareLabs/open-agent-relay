from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any


class ConversationError(Exception):
    code = "CONVERSATION_ERROR"


class ConversationNotFound(ConversationError):
    code = "CONVERSATION_NOT_FOUND"


class ConversationForbidden(ConversationError):
    code = "CONVERSATION_FORBIDDEN"


@dataclass
class Conversation:
    id: str
    owner: str
    updated_at: float
    turns: list[tuple[str, str]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


class ConversationStore:
    def __init__(self, ttl_seconds: int = 3600, max_history_chars: int = 65_536) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_history_chars = max_history_chars
        self._items: dict[str, Conversation] = {}
        self._lock = threading.RLock()

    def create(self, owner: str) -> Conversation:
        self._require_owner(owner)
        with self._lock:
            self._remove_expired()
            conversation = Conversation(
                id=f"conv_{secrets.token_urlsafe(18)}",
                owner=owner,
                updated_at=time.monotonic(),
            )
            self._items[conversation.id] = conversation
            return conversation

    def get(self, conversation_id: str, owner: str) -> Conversation:
        self._require_owner(owner)
        with self._lock:
            self._remove_expired()
            try:
                conversation = self._items[conversation_id]
            except KeyError as exc:
                raise ConversationNotFound("conversation does not exist or has expired") from exc
            if not secrets.compare_digest(conversation.owner, owner):
                raise ConversationForbidden("conversation belongs to another caller")
            conversation.updated_at = time.monotonic()
            return conversation

    def render(self, conversation: Conversation, input_value: object) -> object:
        if not conversation.turns:
            return input_value
        current = self._text(input_value)
        sections = ["Continue this conversation using the prior turns below."]
        used = len(current)
        selected: list[tuple[str, str]] = []
        for user, assistant in reversed(conversation.turns):
            size = len(user) + len(assistant) + 20
            if selected and used + size > self.max_history_chars:
                break
            selected.append((user, assistant))
            used += size
        for user, assistant in reversed(selected):
            sections.extend((f"User: {user}", f"Assistant: {assistant}"))
        sections.append(f"User: {current}")
        return "\n\n".join(sections)

    def append(self, conversation: Conversation, input_value: object, result: object) -> None:
        with self._lock:
            user = self._text(input_value)
            assistant = self._text(result)
            if len(user) + len(assistant) > self.max_history_chars:
                half = max(1, self.max_history_chars // 2)
                user = user[-half:]
                assistant = assistant[-half:]
            conversation.turns.append((user, assistant))
            while sum(len(user) + len(assistant) for user, assistant in conversation.turns) > self.max_history_chars:
                conversation.turns.pop(0)
            conversation.updated_at = time.monotonic()

    def _remove_expired(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        expired = [key for key, value in self._items.items() if value.updated_at < cutoff]
        for key in expired:
            del self._items[key]

    @staticmethod
    def _require_owner(owner: str) -> None:
        if not owner:
            raise ConversationForbidden("a caller ID is required for conversations")
        if len(owner) > 256:
            raise ConversationForbidden("caller ID is too long")

    @staticmethod
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
