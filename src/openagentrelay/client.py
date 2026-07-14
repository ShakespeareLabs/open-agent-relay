from __future__ import annotations

import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


class RelayClientError(RuntimeError):
    def __init__(self, status: int | None, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"error": {"status": self.status, "code": self.code, "message": self.message}}


class RelayClient:
    def __init__(self, target: str, access_key: str, caller_id: str | None = None, timeout: float | None = None):
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RelayClientError(None, "INVALID_TARGET", "target must be an http:// or https:// URL")
        if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
            raise RelayClientError(None, "INVALID_TIMEOUT", "request timeout must be a finite number greater than zero")
        self.target = target.rstrip("/")
        self.access_key = access_key
        self.caller_id = caller_id
        self.timeout = timeout

    def request(self, method: str, path: str, data: object | None = None) -> Any | None:
        body = None if data is None else json.dumps(data).encode()
        request = Request(
            f"{self.target}{path}",
            data=body,
            method=method,
            headers=self._headers(body is not None),
        )
        try:
            timeout = self.timeout if self.timeout is not None else self._advertised_timeout(path)
            with urlopen(request, timeout=timeout) as response:
                if response.status == 204:
                    return None
                try:
                    return json.loads(response.read())
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise RelayClientError(
                        response.status,
                        "INVALID_RESPONSE",
                        "agent returned a response that is not valid JSON",
                    ) from exc
        except HTTPError as exc:
            detail = exc.read().decode()
            exc.close()
            try:
                error = json.loads(detail)["error"]
                code = str(error.get("code", "HTTP_ERROR"))
                message = str(error.get("message", detail))
            except (json.JSONDecodeError, KeyError, TypeError):
                code = "HTTP_ERROR"
                message = detail or f"agent returned HTTP {exc.code}"
            raise RelayClientError(exc.code, code, message) from exc
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RelayClientError(None, "CONNECTION_ERROR", str(reason)) from exc

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {"content-type": "application/json"} if has_body else {}
        headers["authorization"] = f"Bearer {self.access_key}"
        if self.caller_id:
            headers["x-relay-caller-id"] = self.caller_id
        return headers

    def _advertised_timeout(self, path: str) -> float:
        if path != "/v1/invoke":
            return 10
        card = self.card()
        try:
            advertised = float(card.get("limits", {}).get("execution_timeout_seconds", 600))
        except (AttributeError, TypeError, ValueError) as exc:
            raise RelayClientError(None, "INVALID_AGENT_CARD", "execution timeout is invalid") from exc
        if not math.isfinite(advertised) or advertised <= 0 or advertised > 86_400:
            raise RelayClientError(None, "INVALID_AGENT_CARD", "execution timeout is outside the supported range")
        return advertised + 10

    def card(self) -> dict[str, Any]:
        response = self.request("GET", "/.well-known/agent-card.json")
        if not isinstance(response, dict):
            raise RelayClientError(None, "INVALID_AGENT_CARD", "agent card must be a JSON object")
        return response

    def invoke(
        self,
        input_value: object,
        *,
        new_conversation: bool = False,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"input": input_value}
        if new_conversation:
            data["new_conversation"] = True
        if conversation_id:
            data["conversation_id"] = conversation_id
        response = self.request("POST", "/v1/invoke", data)
        if not isinstance(response, dict):
            raise RelayClientError(None, "INVALID_RESPONSE", "agent response must be a JSON object")
        return response
