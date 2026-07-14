from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Callable
from hmac import compare_digest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .runner import CommandFailed
from .conversations import ConversationForbidden, ConversationNotFound, ConversationStore


class RequestProblem(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OpenAgentRelay</title><style>
body{font:16px system-ui;max-width:760px;margin:64px auto;padding:0 20px;color:#171717}
input,button,textarea{font:inherit;padding:10px;margin:4px 0;box-sizing:border-box}textarea{width:100%;min-height:120px}
input{width:100%}button{cursor:pointer}pre{background:#f5f5f5;padding:16px;white-space:pre-wrap;border-radius:8px}.muted{color:#666}
</style></head><body><h1 id="name">OpenAgentRelay</h1><p id="description" class="muted"></p>
<label>Access key<input id="key" type="password" autocomplete="off"></label>
<label>Request<textarea id="prompt" placeholder="What should this agent do?"></textarea></label>
<button onclick="invoke()">Run</button><pre id="out">Ready.</pre>
<script>
async function load(){let r=await fetch('/.well-known/agent-card.json');let d=await r.json();name.textContent=d.name;description.textContent=d.description||''}
async function invoke(){out.textContent='Running…';let r=await fetch('/v1/invoke',{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+key.value},body:JSON.stringify({input:prompt.value})});let d=await r.json();out.textContent=r.ok?String(d.result):JSON.stringify(d,null,2)}
load();
</script></body></html>"""


class DirectServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        name: str,
        description: str,
        executor: Callable[[object], object],
        access_key: str,
        execution_timeout: int = 600,
        max_request_bytes: int = 1_048_576,
        max_concurrency: int = 4,
        conversation_ttl: int = 3600,
    ) -> None:
        self.capability_name = name
        self.description = description
        self.executor = executor
        self.access_key = access_key
        self.execution_timeout = execution_timeout
        self.max_request_bytes = max_request_bytes
        self.execution_slots = threading.BoundedSemaphore(max_concurrency)
        self.conversations = ConversationStore(ttl_seconds=conversation_ttl)
        super().__init__(address, DirectHandler)


class DirectHandler(BaseHTTPRequestHandler):
    server: DirectServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _authorized(self) -> bool:
        expected = f"Bearer {self.server.access_key}"
        return compare_digest(self.headers.get("authorization", ""), expected)

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
        if path == "/.well-known/agent-card.json":
            self._send_json(
                HTTPStatus.OK,
                {
                    "name": self.server.capability_name,
                    "description": self.server.description,
                    "transport": "openagentrelay-direct-v1",
                    "authentication": "bearer",
                    "sessions": "relay-managed",
                    "limits": {
                        "execution_timeout_seconds": self.server.execution_timeout,
                        "max_request_bytes": self.server.max_request_bytes,
                    },
                },
            )
            return
        self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/v1/invoke":
            self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "route not found")
            return
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "a valid access key is required")
            return
        try:
            data = self._json_body()
            if "input" not in data:
                self._error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "missing field: input")
                return
            new_conversation = data.get("new_conversation", False)
            conversation_id = data.get("conversation_id")
            if not isinstance(new_conversation, bool):
                raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "new_conversation must be a boolean")
            if new_conversation and conversation_id:
                raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "choose new_conversation or conversation_id, not both")
            caller_id = self.headers.get("x-relay-caller-id", "")
            conversation = None
            if new_conversation:
                conversation = self.server.conversations.create(caller_id)
            elif conversation_id:
                if not isinstance(conversation_id, str):
                    raise RequestProblem(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "conversation_id must be a string")
                conversation = self.server.conversations.get(conversation_id, caller_id)

            lock = conversation.lock if conversation else threading.Lock()
            with lock:
                effective_input = (
                    self.server.conversations.render(conversation, data["input"])
                    if conversation
                    else data["input"]
                )
                if not self.server.execution_slots.acquire(blocking=False):
                    raise RequestProblem(HTTPStatus.TOO_MANY_REQUESTS, "BUSY", "agent concurrency limit reached")
                try:
                    result = self.server.executor(effective_input)
                finally:
                    self.server.execution_slots.release()
                if conversation:
                    self.server.conversations.append(conversation, data["input"], result)
            payload = {"capability": self.server.capability_name, "result": result}
            if conversation:
                payload["conversation_id"] = conversation.id
            self._send_json(
                HTTPStatus.OK,
                payload,
            )
        except RequestProblem as exc:
            self._error(exc.status, exc.code, exc.message)
        except json.JSONDecodeError:
            self._error(HTTPStatus.BAD_REQUEST, "INVALID_JSON", "request body must be valid JSON")
        except ConversationNotFound as exc:
            self._error(HTTPStatus.NOT_FOUND, exc.code, str(exc))
        except ConversationForbidden as exc:
            self._error(HTTPStatus.FORBIDDEN, exc.code, str(exc))
        except subprocess.TimeoutExpired:
            self._error(HTTPStatus.GATEWAY_TIMEOUT, "EXECUTION_TIMEOUT", "agent execution timed out")
        except CommandFailed as exc:
            print(f"Agent command failed locally: {exc.detail}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "EXECUTION_FAILED", str(exc))
        except Exception as exc:
            print(f"Agent execution failed locally: {exc}")
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "EXECUTION_FAILED", "agent execution failed")


def serve(
    host: str,
    port: int,
    *,
    name: str,
    description: str,
    executor: Callable[[object], object],
    access_key: str,
    execution_timeout: int = 600,
    max_request_bytes: int = 1_048_576,
    max_concurrency: int = 4,
    conversation_ttl: int = 3600,
) -> None:
    server = DirectServer(
        (host, port),
        name=name,
        description=description,
        executor=executor,
        access_key=access_key,
        execution_timeout=execution_timeout,
        max_request_bytes=max_request_bytes,
        max_concurrency=max_concurrency,
        conversation_ttl=conversation_ttl,
    )
    print(f"Serving {name} on http://{host}:{port}")
    server.serve_forever()
