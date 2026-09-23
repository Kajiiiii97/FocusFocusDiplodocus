"""Tiny local HTTP server the Firefox extension reports to. Only listens on 127.0.0.1."""

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED_ORIGINS = ("moz-extension://", "chrome-extension://")


def make_handler(watcher):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _allowed(self):
            # The custom header forces a CORS preflight (which we never answer), so ordinary
            # web pages can't fake reports. Extensions with host permission skip CORS.
            if self.headers.get("X-Focus-Cat") != "1":
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin.startswith(ALLOWED_ORIGINS)

        def do_GET(self):
            if self.path == "/ping":
                self._send(200, {"ok": True, "app": "focus-cat"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/report":
                self._send(404, {"error": "not found"})
                return
            if not self._allowed():
                self._send(403, {"error": "forbidden"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > 65536:
                self._send(413, {"error": "bad length"})
                return
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:
                self._send(400, {"error": "bad json"})
                return
            close = watcher.report(
                url=str(data.get("url") or ""),
                tab_id=data.get("tabId"),
                focused=bool(data.get("focused")),
            )
            self._send(200, {"close": close, "mood": watcher.status()["mood"]})

        def log_message(self, *args):
            pass

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    if sys.platform == "win32":
        # SO_REUSEADDR on Windows lets a second copy bind the same port, which would hide
        # "already running". Claim the port exclusively instead.
        allow_reuse_address = False

        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
            super().server_bind()


class ReportServer:
    def __init__(self, watcher, port, host="127.0.0.1"):
        # Raises OSError if the port is taken (usually: Focus Cat is already running).
        self.httpd = _Server((host, port), make_handler(watcher))
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
