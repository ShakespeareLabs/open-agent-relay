from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class RelayClient:
    def __init__(self, hub: str):
        self.hub = hub.rstrip("/")

    def request(self, method: str, path: str, data: object | None = None) -> Any | None:
        body = None if data is None else json.dumps(data).encode()
        request = Request(
            f"{self.hub}{path}",
            data=body,
            method=method,
            headers={"content-type": "application/json"} if body else {},
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status == 204:
                    return None
                return json.loads(response.read())
        except HTTPError as exc:
            detail = exc.read().decode()
            raise RuntimeError(f"Hub returned {exc.code}: {detail}") from exc

    def publish(self, name: str, description: str) -> dict[str, Any]:
        return self.request("POST", "/v1/capabilities", {"name": name, "description": description})

    def submit(self, capability: str, input_value: object) -> dict[str, Any]:
        return self.request("POST", "/v1/tasks", {"capability": capability, "input": input_value})

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/tasks/{task_id}")

