#!/usr/bin/env python
"""实时状态可视化服务（仅标准库）。

  python frontend/server.py
  python frontend/server.py --port 8011 --state-file results/live_demo/state.json
  python frontend/server.py --quiet

端点：
  GET /        -> frontend/index.html
  GET /state   -> state.json（带 no-cache 头）
                  文件缺失、为空或正被写入（JSON 不完整）时返回 {"empty": true}

只读：本服务不修改任何状态文件。
"""
from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = Path(__file__).resolve().parent / "index.html"

NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def load_state(path: Path) -> dict:
    """读取状态文件；任何异常（缺失/空/半截 JSON/非对象）都退化为 {"empty": true}。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {"empty": True}
    if not raw.strip():
        return {"empty": True}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {"empty": True}
    if not isinstance(data, dict):
        return {"empty": True}
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = "DocoderView/1.0"
    protocol_version = "HTTP/1.1"
    state_file: Path = ROOT / "results/live/state.json"
    quiet: bool = False

    def log_message(self, fmt, *args):
        if not self.quiet:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, body: bytes, ctype: str, status=HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in NO_CACHE.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, obj, status=HTTPStatus.OK):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(body, "application/json; charset=utf-8", status)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                body = INDEX.read_bytes()
            except OSError:
                self._send(b"index.html not found", "text/plain; charset=utf-8",
                           HTTPStatus.NOT_FOUND)
                return
            self._send(body, "text/html; charset=utf-8")
        elif path == "/state":
            self._send_json(load_state(self.state_file))
        elif path == "/favicon.ico":
            self._send(b"", "image/x-icon", HTTPStatus.NO_CONTENT)
        else:
            self._send_json({"error": "not found", "path": path}, HTTPStatus.NOT_FOUND)

    do_HEAD = do_GET


def main():
    ap = argparse.ArgumentParser(description="多段并行生成 · 实时状态可视化服务")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8010)
    ap.add_argument("--state-file", default="results/live/state.json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    state_path = Path(args.state_file)
    if not state_path.is_absolute():
        state_path = ROOT / state_path

    Handler.state_file = state_path
    Handler.quiet = args.quiet

    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        sys.exit(f"[serve] 无法监听 {args.host}:{args.port} —— {exc}")
    httpd.daemon_threads = True

    if not args.quiet:
        print(f"[serve] http://{args.host}:{args.port}/   state={state_path}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n[serve] 已停止", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
