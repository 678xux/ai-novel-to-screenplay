from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .analyzer import analyze_novel_input
from .ai_adapter import convert_novel_to_screenplay_optional_ai, get_public_ai_config

ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT_DIR / "public"


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        if self.path == "/api/analyze":
            try:
                self.send_json(200, analyze_novel_input(self.read_json()))
            except Exception as exc:  # noqa: BLE001 - API returns user-facing errors.
                self.send_json(400, {"ok": False, "error": str(exc) or "分析失败"})
            return
        if self.path != "/api/convert":
            self.send_error(404)
            return
        try:
            result = convert_novel_to_screenplay_optional_ai(self.read_json())
            self.send_json(200, result)
        except Exception as exc:  # noqa: BLE001 - API returns user-facing errors.
            self.send_json(400, {"ok": False, "error": str(exc) or "转换失败"})

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(200, {"ok": True, "ai": get_public_ai_config()})
            return
        self.serve_static(parsed.path)

    def serve_static(self, url_path: str) -> None:
        requested = "/index.html" if url_path == "/" else unquote(url_path)
        safe_parts = [part for part in Path(requested.lstrip("/")).parts if part not in {"..", ".", ""}]
        file_path = PUBLIC_DIR.joinpath(*safe_parts)
        if not file_path.exists() or not file_path.is_file() or PUBLIC_DIR not in file_path.resolve().parents:
            self.send_error(404)
            return
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or file_path.suffix in {".js", ".json", ".yaml", ".yml", ".md"}:
            content_type = f"{content_type}; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 4173) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"AI novel-to-screenplay tool running at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
