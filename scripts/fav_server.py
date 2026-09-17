"""Favorites-backed static server.

Serves repo root on port 8765 plus a small JSON API:
  GET  /api/favs -> {favs: [...]}
  POST /api/favs {favs: [...]} -> {ok: true, favs: [...]}
All other paths serve static files. Stdlib only.
"""
import json
import os
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "state" / "favorites.json"
PORT = 8765


def load_favs():
    try:
        if not STATE_FILE.exists():
            return []
        raw = STATE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("favs"), list):
            data = data["favs"]
        if not isinstance(data, list):
            return []
        return [x for x in data if isinstance(x, str) and x]
    except Exception:
        return []


def save_favs(favs):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(STATE_FILE.parent), prefix=".favorites.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(favs, f)
            f.write("\n")
        os.replace(tmp, STATE_FILE)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass
    return favs


class FavHandler(SimpleHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/favs":
            self._send_json({"favs": load_favs()})
            return
        super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/favs":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        try:
            raw = self.rfile.read(length) if length > 0 else b""
            payload = json.loads(raw.decode("utf-8") if raw else "{}")
        except Exception:
            self._send_json({"ok": False, "error": "invalid json"}, status=400)
            return
        favs = payload.get("favs") if isinstance(payload, dict) else None
        if not isinstance(favs, list) or any(not isinstance(x, str) or not x for x in favs):
            self._send_json({"ok": False, "error": "favs must be array of strings"}, status=400)
            return
        save_favs(favs)
        self._send_json({"ok": True, "favs": favs})


def main():
    # Create empty store if missing (do not clobber existing).
    if not STATE_FILE.exists():
        save_favs([])
    handler = partial(FavHandler, directory=str(REPO_ROOT))
    with ThreadingHTTPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"serving {REPO_ROOT} on port {PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
