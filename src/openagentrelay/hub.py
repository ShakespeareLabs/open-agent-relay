from __future__ import annotations

import json
import threading
from hmac import compare_digest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .models import Capability, Task
from .store import Conflict, InMemoryStore, NotFound


class RequestProblem(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpenAgentRelay Hub</title><style>
body{font:16px system-ui;max-width:760px;margin:64px auto;padding:0 20px;color:#171717}
input,select,button{font:inherit;padding:10px;margin:4px 0}input{width:70%}button{cursor:pointer}
pre{background:#f5f5f5;padding:16px;white-space:pre-wrap;border-radius:8px}.muted{color:#666}
</style></head><body><h1>OpenAgentRelay Hub</h1>
<p class="muted">Asynchronous capability routing without shipping code or business credentials.</p>
<input id="key" type="password" placeholder="Client access key"><button onclick="load()">Connect</button><br>
<select id="cap"></select><br><input id="prompt" placeholder="What should the agent do?">
<button onclick="submitTask()">Submit</button><pre id="out">Enter a client key.</pre>
<script>
function headers(){return {'content-type':'application/json','authorization':'Bearer '+key.value}}
async function load(){let r=await fetch('/v1/capabilities',{headers:headers()});let d=await r.json();cap.replaceChildren();for(let x of d.items||[]){let o=document.createElement('option');o.textContent=x.name;cap.appendChild(o)}out.textContent=r.ok?'Connected.':JSON.stringify(d,null,2)}
async function submitTask(){let r=await fetch('/v1/tasks',{method:'POST',headers:headers(),body:JSON.stringify({capability:cap.value,input:prompt.value})});let d=await r.json();out.textContent=JSON.stringify(d,null,2);if(d.id)poll(d.id)}
async function poll(id){let r=await fetch('/v1/tasks/'+id,{headers:headers()});let d=await r.json();out.textContent=JSON.stringify(d,null,2);if(!['completed','failed','cancelled'].includes(d.status))setTimeout(()=>poll(id),1000)}
</script></body></html>"""


class RelayServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        store: InMemoryStore | None = None,
        *,
        client_key: str,
        runner_key: str,
        lease_seconds: float = 60,
        max_request_bytes: int = 1_048_576,
        max_concurrency: int = 32,
    ) -> None:
        if lease_seconds < 0.3:
            raise ValueError("lease_seconds must be at least 0.3")
        if compare_digest(client_key, runner_key):
            raise ValueError("client and runner keys must be different")
        self.store = store or InMemoryStore(lease_seconds=lease_seconds)
        self.client_key = client_key
        self.runner_key = runner_key
        self.lease_seconds = lease_seconds
        self.max_request_bytes = max_request_bytes
        self.request_slots = threading.BoundedSemaphore(max_concurrency)
        super().__init__(address, RelayHandler)


class RelayHandler(BaseHTTPRequestHandler):
    server: RelayServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError as exc:
            raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_CONTENT_LENGTH", "content-length must be an integer") from exc
        if length < 0:
            raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_CONTENT_LENGTH", "content-length cannot be negative")
        if length > self.server.max_request_bytes:
            raise RequestProblem(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE", "request body is too large")
        if length == 0:
            return {}
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "request body must be a JSON object")
        return data

    def _require_role(self, role: str) -> None:
        supplied = self.headers.get("authorization", "")
        expected = self.server.client_key if role == "client" else self.server.runner_key
        other = self.server.runner_key if role == "client" else self.server.client_key
        if compare_digest(supplied, f"Bearer {expected}"):
            return
        if compare_digest(supplied, f"Bearer {other}"):
            raise RequestProblem(HTTPStatus.FORBIDDEN, "FORBIDDEN", f"{role} credentials are required")
        raise RequestProblem(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "valid credentials are required")

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})

    def do_GET(self) -> None:
        if not self.server.request_slots.acquire(blocking=False):
            self._error(HTTPStatus.TOO_MANY_REQUESTS, "BUSY", "Hub concurrency limit reached")
            return
        try:
            self._handle_get()
        finally:
            self.server.request_slots.release()

    def _handle_get(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            body = INDEX_HTML.encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok", "lease_seconds": self.server.lease_seconds})
            return
        try:
            self._require_role("client")
            if path == "/v1/capabilities":
                items = [item.to_dict() for item in self.server.store.list_capabilities()]
                self._send_json(HTTPStatus.OK, {"items": items})
                return
            if path.startswith("/v1/tasks/"):
                task_id = path.rsplit("/", 1)[-1]
                self._send_json(HTTPStatus.OK, self.server.store.get(task_id).to_dict())
                return
            raise RequestProblem(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")
        except RequestProblem as exc:
            self._error(exc.status, exc.code, exc.message)
        except NotFound as exc:
            self._error(HTTPStatus.NOT_FOUND, "TASK_NOT_FOUND", str(exc))
        except Exception as exc:
            print(f"Hub request failed locally: {exc}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Hub request failed")

    def do_POST(self) -> None:
        if not self.server.request_slots.acquire(blocking=False):
            self._error(HTTPStatus.TOO_MANY_REQUESTS, "BUSY", "Hub concurrency limit reached")
            return
        try:
            self._handle_post()
        finally:
            self.server.request_slots.release()

    def _handle_post(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/v1/tasks":
                self._require_role("client")
            elif path in {"/v1/capabilities", "/v1/runners/claim"} or (
                path.startswith("/v1/tasks/")
                and path.endswith(("/heartbeat", "/complete", "/fail"))
            ):
                self._require_role("runner")
            else:
                raise RequestProblem(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")

            data = self._json_body()
            if path == "/v1/capabilities":
                capability = Capability(
                    name=data["name"],
                    description=data.get("description", ""),
                    owner=data.get("owner", "local"),
                    risk=data.get("risk", "read-only"),
                )
                self._send_json(HTTPStatus.CREATED, self.server.store.publish(capability).to_dict())
                return
            if path == "/v1/tasks":
                max_attempts = data.get("max_attempts", 3)
                if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
                    raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "max_attempts must be an integer")
                if not isinstance(data.get("capability"), str):
                    raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "capability must be a string")
                task = Task(
                    capability=data["capability"],
                    input=data.get("input"),
                    requester=data.get("requester", "anonymous"),
                    max_attempts=max_attempts,
                )
                self._send_json(HTTPStatus.CREATED, self.server.store.submit(task).to_dict())
                return
            if path == "/v1/runners/claim":
                task = self.server.store.claim(data["capability"])
                if task is None:
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.end_headers()
                else:
                    payload = task.to_dict(include_lease=True)
                    payload["lease_seconds"] = self.server.lease_seconds
                    self._send_json(HTTPStatus.OK, payload)
                return

            task_id = path.split("/")[3]
            lease_id = str(data.get("lease_id", ""))
            if path.endswith("/heartbeat"):
                task = self.server.store.heartbeat(task_id, lease_id)
                self._send_json(HTTPStatus.OK, task.to_dict(include_lease=True))
                return
            if path.endswith("/complete"):
                task = self.server.store.complete(task_id, data.get("result"), lease_id)
                self._send_json(HTTPStatus.OK, task.to_dict())
                return
            if path.endswith("/fail"):
                retryable = data.get("retryable", True)
                if not isinstance(retryable, bool):
                    raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "retryable must be a boolean")
                task = self.server.store.fail(
                    task_id,
                    str(data.get("error", "execution failed")),
                    lease_id,
                    retryable=retryable,
                )
                self._send_json(HTTPStatus.OK, task.to_dict())
                return
            raise RequestProblem(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")
        except RequestProblem as exc:
            self._error(exc.status, exc.code, exc.message)
        except KeyError as exc:
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", f"missing field: {exc.args[0]}")
        except json.JSONDecodeError:
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_JSON", "request body must be valid JSON")
        except NotFound as exc:
            self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", str(exc))
        except Conflict as exc:
            self._error(HTTPStatus.CONFLICT, "INVALID_TASK_STATE", str(exc))
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", str(exc))
        except Exception as exc:
            print(f"Hub request failed locally: {exc}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Hub request failed")


def serve(
    host: str,
    port: int,
    *,
    client_key: str,
    runner_key: str,
    lease_seconds: float = 60,
    max_request_bytes: int = 1_048_576,
    max_concurrency: int = 32,
) -> None:
    server = RelayServer(
        (host, port),
        client_key=client_key,
        runner_key=runner_key,
        lease_seconds=lease_seconds,
        max_request_bytes=max_request_bytes,
        max_concurrency=max_concurrency,
    )
    print(f"OpenAgentRelay Hub listening on http://{host}:{port}")
    server.serve_forever()
