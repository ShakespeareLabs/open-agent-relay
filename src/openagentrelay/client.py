from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RelayClientError(RuntimeError):
    def __init__(self, status: int | None, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"error": {"status": self.status, "code": self.code, "message": self.message}}


class RelayClient:
    def __init__(self, hub: str, access_key: str, timeout: float = 30):
        self.hub = hub.rstrip("/")
        self.access_key = access_key
        self.timeout = timeout

    def request(self, method: str, path: str, data: object | None = None) -> Any | None:
        body = None if data is None else json.dumps(data).encode()
        request = Request(
            f"{self.hub}{path}",
            data=body,
            method=method,
            headers=self._headers(body is not None),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status == 204:
                    return None
                return json.loads(response.read())
        except HTTPError as exc:
            detail = exc.read().decode()
            exc.close()
            try:
                error = json.loads(detail)["error"]
                code = str(error.get("code", "HTTP_ERROR"))
                message = str(error.get("message", detail))
            except (json.JSONDecodeError, KeyError, TypeError):
                code = "HTTP_ERROR"
                message = detail or f"Hub returned HTTP {exc.code}"
            raise RelayClientError(exc.code, code, message) from exc
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise RelayClientError(None, "CONNECTION_ERROR", str(reason)) from exc

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {"content-type": "application/json"} if has_body else {}
        headers["authorization"] = f"Bearer {self.access_key}"
        return headers

    def publish(self, name: str, description: str) -> dict[str, Any]:
        return self.request("POST", "/v1/capabilities", {"name": name, "description": description})

    def submit(self, capability: str, input_value: object, max_attempts: int = 3) -> dict[str, Any]:
        return self.request(
            "POST",
            "/v1/tasks",
            {"capability": capability, "input": input_value, "max_attempts": max_attempts},
        )

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/tasks/{task_id}")
