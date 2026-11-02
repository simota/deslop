#!/usr/bin/env python3
"""Zero-dependency HTTP server for the deslop landing page and live detector API.

Serves static files from site/ and exposes:
  POST /api/detect   {"text": str, "genre": str, "markdown": bool}

Uses the Python 3.10+ standard library and skills/deslop/scripts/detect.py.
"""
import argparse
import http.server
import json
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detect  # noqa: E402
from common import genre_table, load_rules  # noqa: E402

RULES = load_rules()
GENRES = genre_table(RULES)
RULE_NOTES = {r["id"]: r["note"] for r in RULES["rules"]}
PERSPECTIVE_NAMES = {p["id"]: p["name"] for p in RULES["perspectives"]}


def run_detection(text: str, genre_id: str = "general", markdown: bool = True) -> dict:
    """Scan with detect.scan, the same rules and exemptions as the CLI."""
    if genre_id not in GENRES:
        genre_id = "general"
    name = "input.md" if markdown else "input.txt"
    result = detect.scan([name], SITE, RULES, [], {name: genre_id}, paths=[name], contents=[text.encode("utf-8")])
    doc = result["files"][0]
    hits = [
        {**h, "exempt": bool(h["exempt"]), "exempt_reason": h["exempt"] or None, "note": RULE_NOTES.get(h["rule"], "")}
        for h in result["hits"]
    ]
    cues = [{**c, "name": PERSPECTIVE_NAMES.get(c["perspective"], "")} for c in result["cues"]]
    return {"lang": doc["lang"], "genre": doc["genre"], "metrics": doc["metrics"], "hits": hits, "cues": cues,
            "summary": result["summary"]}


class DeslopHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/detect":
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 512_000:
                self._send_json(413, {"error": "payload too large"})
                return
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw) if raw else {}
            text = str(payload.get("text", ""))
            genre = str(payload.get("genre", "general"))
            markdown = bool(payload.get("markdown", True))
            result = run_detection(text, genre, markdown)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})


def main(argv=None):
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    server = http.server.ThreadingHTTPServer((args.host, args.port), DeslopHandler)
    print(f"deslop LP server listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
