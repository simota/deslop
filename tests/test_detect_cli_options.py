"""detect.py standalone options: stdin, baselines, GitHub annotations, notes."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import detect  # noqa: E402


class DetectOptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.docs = self.tmp / "docs"
        self.docs.mkdir()
        shutil.copyfile(EXAMPLES / "before.en.md", self.docs / "guide.md")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_detect(self, *args, stdin=b""):
        out, err = io.StringIO(), io.StringIO()
        fake = mock.Mock()
        fake.buffer = io.BytesIO(stdin)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch.object(sys, "stdin", fake):
            try:
                code = detect.main([*map(str, args)])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def edit(self, old, new):
        doc = self.docs / "guide.md"
        text = doc.read_text(encoding="utf-8")
        self.assertIn(old, text)
        doc.write_text(text.replace(old, new), encoding="utf-8")

    # stdin

    def test_stdin_scans_the_same_as_the_file(self):
        content = (EXAMPLES / "before.en.md").read_bytes()
        code, out, _ = self.run_detect("-", "--stdin-name", "guide.md", "--root", EXAMPLES, stdin=content)
        file_code, file_out, _ = self.run_detect(EXAMPLES / "before.en.md", "--root", EXAMPLES)
        self.assertEqual(code, 1)
        self.assertEqual((code, out.replace("guide.md", "before.en.md")), (file_code, file_out))

    def test_stdin_name_sets_the_genre_and_markdown_handling(self):
        out = self.tmp / "scan.json"
        self.run_detect("-", "--stdin-name", "CHANGELOG.md", "--out", out, stdin=b"# Changes\n\n- Fixed it.\n")
        self.assertEqual(json.loads(out.read_text())["files"][0]["genre"], "changelog")
        self.run_detect("-", "--out", out, stdin=b"plain text\n")
        self.assertEqual(json.loads(out.read_text())["files"][0]["path"], "stdin.md")

    def test_stdin_cannot_be_combined_and_needs_a_relative_name(self):
        code, _, err = self.run_detect("-", self.docs)
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined", err)
        for name in ("/etc/x.md", "../x.md"):
            self.assertEqual(self.run_detect("-", "--stdin-name", name, stdin=b"x")[0], 2)

    def test_stdin_that_is_not_utf8_exits_2(self):
        code, _, err = self.run_detect("-", stdin=b"\xff\xfe bad")
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", err)

    # baseline

    def baseline(self):
        base = self.tmp / "base.json"
        self.assertEqual(self.run_detect(self.docs, "--root", self.tmp, "--out", base)[0], 1)
        return base

    def test_an_unchanged_tree_passes_against_its_baseline(self):
        base = self.baseline()
        code, out, err = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base)
        self.assertEqual(code, 0)
        self.assertNotIn(" EN-04 ", out)  # accepted hits are counted, not listed
        self.assertIn("0 open", err)
        self.assertIn("22 in baseline", err)

    def test_only_new_hits_fail_and_repeats_count_one_for_one(self):
        base = self.baseline()
        # A second "I hope this helps" is new even though the first is accepted.
        self.edit("## Conclusion", "I hope this helps.\n\n## Conclusion")
        code, out, _ = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base)
        self.assertEqual(code, 1)
        new = [line for line in out.splitlines() if " ART-03 " in line]
        self.assertEqual(len(new), 1, out)
        self.assertNotIn("exempt", new[0])

    def test_density_hits_match_by_rule_when_their_value_moves(self):
        base = self.baseline()
        self.edit("Certainly!", "Certainly! Really!")
        out = self.tmp / "now.json"
        self.run_detect(self.docs, "--root", self.tmp, "--baseline", base, "--out", out)
        hit = next(h for h in json.loads(out.read_text())["hits"] if h["rule"] == "DEN-03")
        self.assertEqual(hit["exempt_by"], "baseline")

    def test_resolved_baseline_hits_are_reported(self):
        base = self.baseline()
        self.edit("seamless", "smooth")
        out = self.tmp / "now.json"
        code, _, err = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base, "--out", out)
        self.assertEqual(code, 0)
        self.assertIn("1 baseline hits gone", err)
        summary = json.loads(out.read_text())["summary"]
        self.assertEqual((summary["baseline"], summary["baseline_resolved"]), (21, 1))

    def test_rerunning_with_out_tightens_the_baseline_in_place(self):
        # The summary's advice: rerun with --out. Written over the baseline it
        # was checked against, the result must still accept the hits that
        # remain, and only those.
        base = self.baseline()
        self.edit("seamless", "smooth")
        code, _, err = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base, "--out", base)
        self.assertEqual(code, 0)
        self.assertIn("rerun with --out to tighten it", err)
        code, _, err = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base)
        self.assertEqual(code, 0, err)
        self.assertIn("21 in baseline", err)
        self.assertNotIn("baseline hits gone", err)
        self.edit("smooth", "seamless")  # the dropped hit is no longer accepted
        code, out, _ = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base)
        self.assertEqual(code, 1)
        self.assertIn("seamless", out)

    def test_hits_a_narrowed_scan_could_not_find_are_not_gone(self):
        # Tightening on the "gone" count would drop hits the scan never looked
        # for: those of rules left out, and those in files not read.
        base = self.baseline()
        (self.tmp / "notes").mkdir()
        (self.tmp / "notes" / "plain.md").write_text("Plain words.\n", encoding="utf-8")
        for narrowed in (("--select", "EN"), ("--ignore", "density"), ()):
            target = self.tmp / "notes" if not narrowed else self.docs
            code, _, err = self.run_detect(target, "--root", self.tmp, "--baseline", base, *narrowed)
            self.assertEqual(code, 0, err)
            self.assertNotIn("baseline hits gone", err)
        self.edit("seamless", "smooth")  # a selected rule's hit that did go still counts
        _, _, err = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base, "--select", "EN")
        self.assertIn("1 baseline hits gone", err)

    def test_exempt_baseline_hits_are_not_accepted(self):
        base = self.baseline()
        data = json.loads(base.read_text())
        for h in data["hits"]:
            h["exempt"] = "kept on purpose" if h["rule"] == "EN-04" else h["exempt"]
        base.write_text(json.dumps(data))
        code, out, _ = self.run_detect(self.docs, "--root", self.tmp, "--baseline", base)
        self.assertEqual(code, 1)
        self.assertEqual({line.split()[1] for line in out.splitlines() if ":" in line.split()[0] and "cue:" not in line},
                         {"EN-04"})

    def test_bad_baselines_and_snapshot_baselines_exit_2(self):
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"tool": "something-else", "hits": []}))
        code, _, err = self.run_detect(self.docs, "--baseline", bad)
        self.assertEqual(code, 2)
        self.assertIn("not a detect.py result", err)
        bad.write_text(json.dumps({"tool": "deslop-detect", "hits": [{"path": "x"}]}))
        self.assertEqual(self.run_detect(self.docs, "--baseline", bad)[0], 2)
        self.assertEqual(self.run_detect("--snapshot", self.tmp, "--baseline", bad)[0], 2)

    # output formats

    def test_github_format_annotates_open_hits_and_cues(self):
        code, out, _ = self.run_detect(self.docs, "--root", self.tmp, "--format", "github")
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertIn("::error file=docs/guide.md,line=3,col=1,title=deslop ART-01::"
                      "Chat reply opener left in the document: Certainly!", lines)
        self.assertTrue(any(line.startswith("::notice file=docs/guide.md,line=23,title=deslop STR-02 cue::")
                            for line in lines))
        self.assertTrue(all(line.startswith(("::error ", "::notice ")) for line in lines))

    def test_github_format_escapes_properties_and_messages(self):
        self.assertEqual(detect._gh_escape("a,b:c%\n", True), "a%2Cb%3Ac%25%0A")
        self.assertEqual(detect._gh_escape("a,b:c%\r\n"), "a,b:c%25%0D%0A")

    def test_github_format_skips_exempt_hits(self):
        base = self.baseline()
        code, out, _ = self.run_detect(self.docs, "--root", self.tmp, "--format", "github", "--baseline", base)
        self.assertEqual(code, 0)
        self.assertNotIn("::error", out)

    def test_explain_adds_rule_notes_and_default_output_is_unchanged(self):
        _, plain, _ = self.run_detect(self.docs, "--root", self.tmp)
        _, explained, _ = self.run_detect(self.docs, "--root", self.tmp, "--explain")
        self.assertIn("docs/guide.md:3:1 ART-01 Certainly!\n", plain)
        self.assertIn("docs/guide.md:3:1 ART-01 Certainly! -- Chat reply opener left in the document\n", explained)


if __name__ == "__main__":
    unittest.main()
