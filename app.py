import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from chatbot import answer_question
from db import init_db
from fuel_service import FuelFinderClient

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class AppHandler(BaseHTTPRequestHandler):
    client = FuelFinderClient(
        base_url=os.environ.get("FUEL_FINDER_BASE_URL", "https://api.fuelfinder.example.com/v1"),
        public_key=os.environ.get("FUEL_FINDER_PUBLIC_KEY", ""),
        secret_key=os.environ.get("FUEL_FINDER_SECRET_KEY", ""),
    )

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, filepath: Path, content_type: str) -> None:
        if not filepath.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = filepath.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        if parsed.path == "/app.js":
            self._send_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
            return

        if parsed.path == "/api/health":
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/stations":
            query = parse_qs(parsed.query)
            lat = float(query.get("lat", ["0"])[0])
            lon = float(query.get("lon", ["0"])[0])
            radius_km = float(query.get("radius_km", ["10"])[0])

            try:
                rows = self.client.fetch_and_store(lat=lat, lon=lon, radius_km=radius_km)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._send_json({"count": len(rows), "stations": rows})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_len)

        try:
            payload = json.loads(body or "{}")
            question = payload["question"]
            lat = float(payload["lat"])
            lon = float(payload["lon"])
            radius_km = float(payload.get("radius_km", 10))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._send_json({"error": "Invalid request payload"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            self.client.fetch_and_store(lat=lat, lon=lon, radius_km=radius_km)
            answer = answer_question(question=question, lat=lat, lon=lon, radius_km=radius_km)
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return

        self._send_json(answer)


def run() -> None:
    init_db()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
