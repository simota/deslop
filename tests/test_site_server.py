"""The landing page's local API: site/serve.py answers like detect.py and fails safely."""
import http.client
import io
import json
import sys
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import detect  # noqa: E402
import serve  # noqa: E402
from common import load_rules  # noqa: E402

BEFORE = (ROOT / "examples" / "before.en.md").read_text(encoding="utf-8")


class SiteServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = serve.http.server.ThreadingHTTPServer(("127.0.0.1", 0), serve.DeslopHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            res = conn.getresponse()
            return res.status, res.getheader("Content-Type", ""), res.read()
        finally:
            conn.close()

    def post(self, payload, headers=None):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        status, _, data = self.request("POST", "/api/detect", body, {"Content-Type": "application/json", **(headers or {})})
        return status, json.loads(data)

    def test_scan_matches_the_command_line_detector(self):
        status, data = self.post({"text": BEFORE, "genre": "general", "markdown": True})
        self.assertEqual(status, 200)
        rules = load_rules()
        expected = detect.scan(["input.md"], serve.SITE, rules, [], {"input.md": "general"},
                               paths=["input.md"], contents=[BEFORE.encode()])
        self.assertEqual([(h["line"], h["col"], h["rule"]) for h in data["hits"]],
                         [(h["line"], h["col"], h["rule"]) for h in expected["hits"]])
        self.assertEqual(data["summary"]["open"], expected["summary"]["open"])
        self.assertTrue(all(h["note"] for h in data["hits"]))

    def test_scan_carries_the_markdown_diagnosis_and_honours_inline_ignores(self):
        status, data = self.post({"text": "# T\n\n## Part\n\nIt is robust.\n\n"
                                          "Robust statistics. <!-- deslop-ignore EN-04: the field's term -->\n"})
        self.assertEqual(status, 200)
        self.assertEqual([h["exempt_reason"] for h in data["hits"]], [None, "inline: the field's term"])
        self.assertTrue(data["diagnosis"].startswith("# deslop diagnosis\n"))
        self.assertIn("| 5:7 | Part | EN-04 | <code>robust</code> |", data["diagnosis"])

    def test_unknown_genre_falls_back_to_general(self):
        status, data = self.post({"text": BEFORE, "genre": "no-such-genre"})
        self.assertEqual((status, data["genre"]), (200, "general"))

    def test_client_errors_are_400_with_a_fixed_message(self):
        for body in (b"{not json", b"\xff\xfe", b"[1, 2]", b'"text"', b'{"text": "\\ud800"}'):
            with self.subTest(body=body):
                status, data = self.post(body)
                self.assertEqual(status, 400)
                self.assertNotIn("Traceback", data["error"])

    def test_bad_content_length_is_rejected_without_reading(self):
        for length in ("-1", "abc", "²"):
            with self.subTest(length=length):
                conn = http.client.HTTPConnection(*self.server.server_address, timeout=5)
                try:
                    conn.putrequest("POST", "/api/detect")
                    conn.putheader("Content-Length", length)
                    conn.endheaders()
                    res = conn.getresponse()
                    self.assertEqual(res.status, 400)
                    res.read()
                finally:
                    conn.close()

    def test_oversized_body_is_413(self):
        status, data = self.post(b" " * (serve.MAX_BODY + 1))
        self.assertEqual(status, 413)

    def test_other_paths_are_404(self):
        status, _, _ = self.request("POST", "/api/other", b"{}")
        self.assertEqual(status, 404)

    def test_detector_failure_is_500_logged_and_undisclosed(self):
        stderr = io.StringIO()
        with patch.object(serve, "run_detection", side_effect=RuntimeError("secret detail")), redirect_stderr(stderr):
            status, data = self.post({"text": "x"})
        self.assertEqual(status, 500)
        self.assertNotIn("secret", json.dumps(data))
        self.assertIn("secret detail", stderr.getvalue())

    def test_static_page_is_served(self):
        status, ctype, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b'<script src="app.js"></script>', body)


if __name__ == "__main__":
    unittest.main()
