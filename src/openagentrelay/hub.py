from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .models import Capability, Task
from .store import Conflict, InMemoryStore, NotFound


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpenAgentRelay</title><style>
body{font:16px system-ui;max-width:760px;margin:64px auto;padding:0 20px;color:#171717}
input,select,button{font:inherit;padding:10px;margin:4px 0}input{width:70%}button{cursor:pointer}
pre{background:#f5f5f5;padding:16px;white-space:pre-wrap;border-radius:8px}.muted{color:#666}
</style></head><body><h1>OpenAgentRelay</h1>
<p class="muted">Share what your agent can do—not its code, environment, or secrets.</p>
<select id="cap"></select><br><input id="prompt" placeholder="What should the agent do?">
<button onclick="submitTask()">Submit</button><pre id="out">Ready.</pre>
<script>
async function load(){let r=await fetch('/v1/capabilities');let d=await r.json();cap.innerHTML=d.items.map(x=>`<option>${x.name}</option>`).join('')}
async function submitTask(){let r=await fetch('/v1/tasks',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({capability:cap.value,input:prompt.value})});let d=await r.json();out.textContent=JSON.stringify(d,null,2);if(d.id) poll(d.id)}
async function poll(id){let r=await fetch('/v1/tasks/'+id);let d=await r.json();out.textContent=JSON.stringify(d,null,2);if(!['completed','failed','cancelled'].includes(d.status))setTimeout(()=>poll(id),1000)}
load();
</script></body></html>"""


class RelayServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], store: InMemoryStore | None = None):
        self.store = store or InMemoryStore()
        super().__init__(address, RelayHandler)


class RelayHandler(BaseHTTPRequestHandler):
    server: RelayServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

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
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/v1/capabilities":
            items = [item.to_dict() for item in self.server.store.list_capabilities()]
            self._send_json(HTTPStatus.OK, {"items": items})
            return
        if path.startswith("/v1/tasks/"):
            task_id = path.rsplit("/", 1)[-1]
            try:
                self._send_json(HTTPStatus.OK, self.server.store.get(task_id).to_dict())
            except NotFound as exc:
                self._error(HTTPStatus.NOT_FOUND, "TASK_NOT_FOUND", str(exc))
            return
        self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
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
                task = Task(
                    capability=data["capability"],
                    input=data.get("input"),
                    requester=data.get("requester", "anonymous"),
                )
                self._send_json(HTTPStatus.CREATED, self.server.store.submit(task).to_dict())
                return
            if path == "/v1/runners/claim":
                task = self.server.store.claim(data["capability"])
                if task is None:
                    self.send_response(HTTPStatus.NO_CONTENT)
                    self.end_headers()
                else:
                    self._send_json(HTTPStatus.OK, task.to_dict())
                return
            if path.startswith("/v1/tasks/") and path.endswith("/complete"):
                task_id = path.split("/")[3]
                task = self.server.store.complete(task_id, data.get("result"))
                self._send_json(HTTPStatus.OK, task.to_dict())
                return
            if path.startswith("/v1/tasks/") and path.endswith("/fail"):
                task_id = path.split("/")[3]
                task = self.server.store.fail(task_id, str(data.get("error", "execution failed")))
                self._send_json(HTTPStatus.OK, task.to_dict())
                return
            self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")
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


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = RelayServer((host, port))
    print(f"OpenAgentRelay Hub listening on http://{host}:{port}")
    server.serve_forever()

