#!/usr/bin/env python3
"""Zero-dependency HTTP server for the deslop landing page and live detector API.

Serves static files from site/ and exposes:
  POST /api/detect   {"text": str, "genre": str, "markdown": bool}

It answers 200 with the scan, 400 for a body that is not a UTF-8 JSON object
or has a bad Content-Length, 404 for other paths, 413 above MAX_BODY bytes
and 500, logged to stderr, when the detector itself fails.

Uses the Python 3.10+ standard library and skills/deslop/scripts/detect.py.
"""
import argparse
import http.server
import json
import mimetypes
import sys
import traceback
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detect  # noqa: E402
from common import genre_table, load_rules  # noqa: E402

MAX_BODY = 512_000
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
        """Requests are not logged; errors are, through log_error."""

    def log_error(self, fmt, *args):
        sys.stderr.write(f"deslop LP server: {fmt % args}\n")

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
        length = self.headers.get("Content-Length", "0")
        if not (length.isascii() and length.isdigit()):
            self._send_json(400, {"error": "Content-Length must be a non-negative integer"})
            return
        if int(length) > MAX_BODY:
            self._send_json(413, {"error": "payload too large"})
            return
        try:
            raw = self.rfile.read(int(length)).decode("utf-8")
            payload = json.loads(raw) if raw else {}
        except (UnicodeDecodeError, ValueError):
            self._send_json(400, {"error": "request body must be UTF-8 JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "request body must be a JSON object"})
            return
        text = str(payload.get("text", ""))
        genre = str(payload.get("genre", "general"))
        markdown = bool(payload.get("markdown", True))
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:  # a lone surrogate escaped in the JSON
            self._send_json(400, {"error": "text must be valid Unicode"})
            return
        try:
            result = run_detection(text, genre, markdown)
        except Exception:  # an internal fault, not the client's: report it without detail
            self.log_error("detection failed:\n%s", traceback.format_exc())
            self._send_json(500, {"error": "internal error"})
            return
        self._send_json(200, result)


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
