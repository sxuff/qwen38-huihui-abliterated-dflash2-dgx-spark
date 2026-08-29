#!/usr/bin/env python3
"""Bearer-auth reverse proxy from the Docker bridge to loopback SGLang."""
from __future__ import annotations

import hmac
import http.client
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = os.environ.get("QWEN38_PROXY_HOST", "172.17.0.1")
LISTEN_PORT = int(os.environ.get("QWEN38_PROXY_PORT", "8001"))
UPSTREAM_HOST = os.environ.get("QWEN38_UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("QWEN38_UPSTREAM_PORT", "8002"))
KEY_FILE = os.environ["QWEN38_PROXY_KEY_FILE"]
API_KEY = open(KEY_FILE, encoding="utf-8").read().strip()
if not API_KEY:
    raise SystemExit("proxy API key file is empty")
MAX_BODY = 128 * 1024 * 1024
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "qwen38-auth-proxy/1"

    def _authorized(self) -> bool:
        return hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {API_KEY}")

    def _json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": {"message": message, "type": "auth_error"}}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _proxy(self) -> None:
        if not self._authorized():
            self._json_error(401, "Unauthorized")
            return
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        if content_length > MAX_BODY:
            self._json_error(413, "Request body too large")
            return
        body = self.rfile.read(content_length) if content_length else None
        headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP_HEADERS and key.lower() not in {"host", "authorization", "content-length"}}
        headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
        headers["Accept-Encoding"] = "identity"
        if body is not None:
            headers["Content-Length"] = str(len(body))
        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=1800)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            streaming = "text/event-stream" in response.getheader("Content-Type", "").lower()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS and key.lower() != "content-length":
                    self.send_header(key, value)
            if streaming:
                self.send_header("Connection", "close")
                self.end_headers()
                while True:
                    chunk = response.read1(8192) if hasattr(response, "read1") else response.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            else:
                payload = response.read()
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
            self.close_connection = True
        except (ConnectionError, TimeoutError, OSError, http.client.HTTPException) as exc:
            self._json_error(502, f"Upstream unavailable: {type(exc).__name__}")
        finally:
            conn.close()

    do_GET = _proxy
    do_POST = _proxy
    do_DELETE = _proxy
    do_PUT = _proxy
    do_PATCH = _proxy
    do_OPTIONS = _proxy

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} {format % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"proxy_ready listen={LISTEN_HOST}:{LISTEN_PORT} upstream={UPSTREAM_HOST}:{UPSTREAM_PORT}", flush=True)
    server.serve_forever()

