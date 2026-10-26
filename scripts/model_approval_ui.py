#!/usr/bin/env python3
"""Run the local model approval UI: python3 scripts/model_approval_ui.py."""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "config" / "model_registry.json"
FRONTEND_ROOT = PROJECT_ROOT / "frontend" / "model-approval"
sys.path.insert(0, str(PROJECT_ROOT))

from capcut.lib.model_approval import ApprovalError, create_approval

HOST = "127.0.0.1"
PORT = 8765
MAX_BODY_BYTES = 16_384

def load_registry() -> dict:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data.get("models"), list):
        raise ValueError("Local model registry must contain a models list")
    return data


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "CapCutModelApproval/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route in ("/", "/index.html"):
            self._send_static("index.html")
        elif route in ("/styles.css", "/app.js"):
            self._send_static(route.lstrip("/"))
        elif route == "/api/models":
            try:
                self._json(200, load_registry())
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._json(500, {"error": f"Cannot read local model registry: {exc}"})
        else:
            self._json(404, {"error": "Not found"})

    def _send_static(self, filename: str) -> None:
        if filename not in {"index.html", "styles.css", "app.js"}:
            self._json(404, {"error": "Not found"})
            return
        try:
            content = (FRONTEND_ROOT / filename).read_bytes()
        except OSError as exc:
            self._json(500, {"error": f"Cannot read frontend file {filename}: {exc}"})
            return
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        charset = "; charset=utf-8" if content_type.startswith(("text/", "application/javascript")) else ""
        self._send(200, content, content_type + charset)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/approve":
            self._json(404, {"error": "Not found"})
            return
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        if host not in (f"{HOST}:{PORT}", f"localhost:{PORT}") or origin not in (
            f"http://{HOST}:{PORT}",
            f"http://localhost:{PORT}",
        ):
            self._json(403, {"error": "Request must originate from this local panel"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Content-Type must be application/json"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BODY_BYTES:
                raise ValueError("Request body is empty or too large")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            artifact = create_approval(
                data.get("provider", ""),
                data.get("model_id", ""),
                data.get("task_scope", ""),
            )
            self._json(201, {
                "id": artifact["id"],
                "provider": artifact["provider"],
                "model_id": artifact["model_id"],
                "task_scope": artifact["task_scope"],
                "expires_at": artifact["expires_at"],
                "state": artifact["state"],
            })
        except (ApprovalError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except OSError as exc:
            self._json(500, {"error": f"Cannot write local approval artifact: {exc}"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[model-approval-ui] {fmt % args}", file=sys.stderr)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"Model approval UI: http://{HOST}:{PORT}/", flush=True)
    print("Press Ctrl+C to stop. This service does not generate media.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
