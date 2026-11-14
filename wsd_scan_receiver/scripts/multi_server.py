#!/usr/bin/env python3
"""Small HTTP control endpoint for multi-page scans (stdlib only).

POST /multi?pages=N  -> arms a batch: scan_trigger.py --pages N runs in the
background; the run.sh mover merges the arriving scans/*.jpg into ONE PDF once
N pages arrived (or on timeout) and delivers that single file to Paperless.
GET  /status         -> current pending batch (for debugging).
"""
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PENDING = "/data/multi_pending.json"
PORT = 18125


def _arm(pages: int) -> dict:
    state = {"pages": pages, "armed": int(time.time())}
    with open(PENDING, "w") as fh:
        json.dump(state, fh)
    subprocess.Popen(
        ["python3", "/app/scripts/scan_trigger.py", "--pages", str(pages)],
        stdout=open("/data/scan.log", "a"),
        stderr=subprocess.STDOUT,
    )
    return state


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/status":
            try:
                pending = json.load(open(PENDING))
            except Exception:
                pending = None
            self._send(200, json.dumps({"pending": pending}).encode())
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self) -> None:
        u = urlparse(self.path)
        if u.path == "/multi":
            pages = int(parse_qs(u.query).get("pages", ["0"])[0])
            if 1 <= pages <= 20:
                if pages == 1:
                    subprocess.Popen(
                        ["python3", "/app/scripts/scan_trigger.py"],
                        stdout=open("/data/scan.log", "a"),
                        stderr=subprocess.STDOUT,
                    )
                    self._send(200, b'{"ok":true,"mode":"single"}')
                    return
                state = _arm(pages)
                self._send(200, json.dumps({"ok": True, "armed": state}).encode())
                return
            self._send(400, b'{"error":"pages must be 1..20"}')
        else:
            self._send(404, b'{"error":"not found"}')

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
