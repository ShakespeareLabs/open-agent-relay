from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class RelayClient:
    def __init__(self, target: str, access_key: str):
        self.target = target.rstrip("/")
        self.access_key = access_key

    def request(self, method: str, path: str, data: object | None = None) -> Any | None:
        body = None if data is None else json.dumps(data).encode()
        request = Request(
            f"{self.target}{path}",
            data=body,
            method=method,
            headers=self._headers(body is not None),
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status == 204:
                    return None
                return json.loads(response.read())
        except HTTPError as exc:
            detail = exc.read().decode()
            exc.close()
            raise RuntimeError(f"Agent returned {exc.code}: {detail}") from exc

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {"content-type": "application/json"} if has_body else {}
        headers["authorization"] = f"Bearer {self.access_key}"
        return headers

    def card(self) -> dict[str, Any]:
        return self.request("GET", "/.well-known/agent-card.json")

    def invoke(self, input_value: object) -> dict[str, Any]:
        return self.request("POST", "/v1/invoke", {"input": input_value})
