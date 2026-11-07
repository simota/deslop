"""detect.py: directory genres, rule selection, inline ignores and the Markdown diagnosis."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import common  # noqa: E402
import detect  # noqa: E402
import diagnosis  # noqa: E402
import snapshot  # noqa: E402


def run(module, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = module.main([*map(str, args)])
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)

    def write(self, rel, text):
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def scan_json(self, *args):
        out = self.tmp / "scan.json"
        code, stdout, stderr = run(detect, *args, "--out", out)
        self.assertNotEqual(code, 2, stderr)
        return code, json.loads(out.read_text(encoding="utf-8")), stdout, stderr


class DirectoryGenreTests(Workspace):
    def setUp(self):
        super().setUp()
        self.rules = common.load_rules()
        self.files = [self.write(p, "Text.\n") for p in
                      ("docs/api/a.md", "docs/api/v2/b.md", "docs/guide.md", "docs/api/README.md")]

    def genres(self, *values):
        return common.assign_genres(list(values), self.files, self.tmp, self.rules)

    def test_a_directory_genre_reaches_every_target_below_it(self):
        g = self.genres("docs/api=reference")
        self.assertEqual(g["docs/api/a.md"], "reference")
        self.assertEqual(g["docs/api/v2/b.md"], "reference")
        self.assertEqual(g["docs/api/README.md"], "reference")
        self.assertEqual(g["docs/guide.md"], "general")

    def test_the_deepest_directory_and_then_the_file_win_in_any_order(self):
        for order in (("docs=tutorial", "docs/api=reference", "docs/api/a.md=spec"),
                      ("docs/api/a.md=spec", "docs/api=reference", "docs=tutorial")):
            g = self.genres(*order)
            self.assertEqual(g["docs/api/a.md"], "spec")
            self.assertEqual(g["docs/api/v2/b.md"], "reference")
            self.assertEqual(g["docs/guide.md"], "tutorial")

    def test_a_directory_with_no_target_or_a_missing_path_is_refused(self):
        self.write("empty/x.txt.bak", "")
        for value in ("empty=reference", "nowhere=reference"):
            with self.assertRaisesRegex(ValueError, "neither a target document nor a directory"):
                self.genres(value)

    def test_snapshot_records_directory_genres(self):
        out = self.tmp / "run"
        code, _, err = run(snapshot, out, "--root", self.tmp / "docs", "--copy", "--genre", "docs/api=reference", "docs")
        self.assertEqual(code, 0, err)
        recorded = {f["path"]: f["genre"] for f in json.loads((out / "snapshot.json").read_text())["files"]}
        self.assertEqual(recorded["api/v2/b.md"], "reference")
        self.assertEqual(recorded["guide.md"], "general")


class SelectionTests(Workspace):
    def setUp(self):
        super().setUp()
        shutil.copyfile(EXAMPLES / "before.en.md", self.tmp / "guide.md")

    def test_select_a_tier_keeps_only_its_rules_and_records_the_selection(self):
        code, data, _, _ = self.scan_json("guide.md", "--select", "artifact")
        self.assertEqual(code, 1)
        self.assertEqual({h["tier"] for h in data["hits"]}, {"artifact"})
        self.assertEqual(data["selection"], {"select": ["artifact"]})

    def test_family_id_and_ignore_combine(self):
        _, full, _, _ = self.scan_json("guide.md")
        _, data, _, _ = self.scan_json("guide.md", "--select", "en,ART-01", "--ignore", "EN-04")
        rules = {h["rule"] for h in data["hits"]}
        self.assertIn("ART-01", rules)
        self.assertNotIn("EN-04", rules)
        self.assertNotIn("ART-03", rules)
        self.assertEqual(rules, {h["rule"] for h in full["hits"]
                                 if h["rule"].startswith("EN-") and h["rule"] != "EN-04"} | {"ART-01"})

    def test_ignoring_every_open_rule_passes(self):
        _, full, _, _ = self.scan_json("guide.md")
        families = sorted({h["rule"].split("-")[0] for h in full["hits"]})
        code, data, _, _ = self.scan_json("guide.md", "--ignore", ",".join(families))
        self.assertEqual((code, data["summary"]["open"]), (0, 0))

    def test_unknown_or_empty_selections_and_snapshot_scans_are_refused(self):
        self.assertEqual(run(detect, "guide.md", "--select", "EN-99")[0], 2)
        self.assertEqual(run(detect, "guide.md", "--select", "EN", "--ignore", "lexical")[0], 2)
        code, _, err = run(detect, "--snapshot", self.tmp, "--select", "EN")
        self.assertEqual(code, 2)
        self.assertIn("standalone", err)

    def test_list_rules_prints_the_catalogue_and_honours_the_selection(self):
        code, out, _ = run(detect, "--list-rules")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), len(common.load_rules()["rules"]))
        code, out, _ = run(detect, "--list-rules", "--select", "DEN-05")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn("heading_per_1000 max", out)
        self.assertIn("exempt in", out)
        self.assertIn("readme 8", out)


class InlineIgnoreTests(Workspace):
    DOC = """# Title

Robust statistics are robust here. <!-- deslop-ignore EN-04: "robust statistics" is the field's term -->

<!-- deslop-ignore EN-14: a product tagline quoted by legal -->
A comprehensive and seamless tool.

```md
<!-- deslop-ignore EN-04: shown as an example -->
robust example
```
"""

    def test_line_and_next_line_directives_exempt_only_their_line(self):
        self.write("doc.md", self.DOC)
        code, data, out, err = self.scan_json("doc.md")
        exempt = [(h["line"], h["rule"]) for h in data["hits"] if h.get("exempt_by") == "inline"]
        self.assertEqual(exempt, [(3, "EN-04"), (3, "EN-04"), (6, "EN-14")])
        self.assertEqual([(h["line"], h["rule"]) for h in data["hits"] if not h["exempt"]], [(6, "EN-04")])
        self.assertEqual(code, 1)
        self.assertEqual(data["summary"]["inline"], 3)
        self.assertIn("3 ignored inline", err)
        self.assertIn("[exempt: inline: a product tagline quoted by legal]", out)
        _, md, _ = run(detect, "doc.md", "--format", "markdown")
        self.assertIn("<details><summary>Exempt hits (3)</summary>", md)
        self.assertIn("| 6:3 | EN-14 | <code>comprehensive</code> | inline: a product tagline quoted by legal |", md)

    def test_a_directive_inside_code_does_nothing_and_its_reason_is_not_scanned(self):
        self.write("doc.md", self.DOC)
        _, data, _, _ = self.scan_json("doc.md")
        self.assertEqual(len(data["ignores"]), 2)
        # The reason on line 3 says "robust statistics", and no hit comes from inside a comment.
        self.assertFalse([h for h in data["hits"] if h["line"] == 3 and h["col"] > 40])

    def test_file_directive_covers_density_rules(self):
        body = "\n\n".join(f"## H{i}\n\nOne line of prose for section {i} that stays plain." for i in range(12))
        self.write("doc.md", body + "\n")
        _, before, _, _ = self.scan_json("doc.md")
        self.assertIn("DEN-08", {h["rule"] for h in before["hits"] if not h["exempt"]})
        self.write("doc.md", "<!-- deslop-ignore-file DEN-08: a glossary, one line per term -->\n\n" + body + "\n")
        code, after, _, _ = self.scan_json("doc.md")
        self.assertEqual([h["exempt_by"] for h in after["hits"] if h["rule"] == "DEN-08"], ["inline"])
        self.assertEqual(code, 0)

    def test_invalid_artifact_and_unused_directives_are_reported_without_effect(self):
        self.write("doc.md", "I hope this helps. <!-- deslop-ignore ART-03: it is our sign-off -->\n\n"
                             "<!-- deslop-ignore EN-04 forgot the colon -->\nIt is robust.\n\n"
                             "<!-- deslop-ignore-file EN-01, ZZ-01: typo -->\n"
                             "<!-- deslop-ignore-file EN-01: nothing delves here -->\n")
        code, data, out, err = self.scan_json("doc.md")
        self.assertEqual(code, 1)
        self.assertEqual(data["summary"]["open"], 2)
        errors = [d["error"] for d in data["ignores"] if "error" in d]
        self.assertEqual(len(errors), 3)
        self.assertIn("artifact rule", errors[0])
        self.assertIn("reason", errors[1])
        self.assertIn("unknown rule 'ZZ-01'", errors[2])
        self.assertEqual([d["unused"] for d in data["ignores"] if "unused" in d], [["EN-01"]])
        self.assertIn("doc.md:7 deslop-ignore unused: EN-01 covers no hit", out)
        self.assertIn("(1 unused and 3 invalid directives)", err)
        code, gh, _ = run(detect, "doc.md", "--format", "github")
        self.assertEqual(gh.count("::warning file=doc.md"), 4)

    def test_directives_can_be_disregarded_and_plain_text_files_never_read_them(self):
        self.write("doc.md", self.DOC)
        _, data, _, _ = self.scan_json("doc.md", "--no-inline-ignores")
        self.assertNotIn("ignores", data)
        self.assertNotIn("inline", data["summary"])
        self.assertFalse([h for h in data["hits"] if h.get("exempt_by") == "inline"])
        self.write("doc.txt", "It is robust. <!-- deslop-ignore EN-04: plain text has no comments -->\n")
        _, data, _, _ = self.scan_json("doc.txt")
        self.assertEqual(data["summary"]["open"], 1)

    def test_documents_without_directives_keep_the_previous_output(self):
        shutil.copyfile(EXAMPLES / "before.en.md", self.tmp / "guide.md")
        _, data, _, _ = self.scan_json("guide.md")
        self.assertNotIn("ignores", data)
        self.assertEqual(set(data["summary"]), {"files", "total", "open", "exempt", "by_rule", "cues"})

    def test_a_directive_for_an_unselected_rule_is_not_unused(self):
        self.write("doc.md", "It is robust. <!-- deslop-ignore EN-04: term -->\n")
        _, data, _, _ = self.scan_json("doc.md", "--select", "artifact")
        self.assertEqual(data["ignores"][0]["unused"], [])

    def test_snapshot_scans_never_apply_directives(self):
        self.write("docs/doc.md", self.DOC)
        out = self.tmp / "run"
        self.assertEqual(run(snapshot, out, "--root", self.tmp / "docs", "--copy", "docs/doc.md")[0], 0)
        _, data, _, _ = self.scan_json("--snapshot", out)
        self.assertNotIn("ignores", data)
        self.assertFalse([h for h in data["hits"] if h.get("exempt_by") == "inline"])


class MarkdownDiagnosisTests(Workspace):
    def test_hits_are_placed_in_their_section_without_the_document_title(self):
        self.write("doc.md", "# Guide\n\nIntro is robust.\n\n## Install\n\n### Linux\n\nA seamless step.\n\n"
                             "## Use\n\nIt is | robust | here.\n")
        code, out, _ = run(detect, "doc.md", "--format", "markdown")
        self.assertEqual(code, 1)
        self.assertIn("| 3:10 | Guide | EN-04 | <code>robust</code> |", out)
        self.assertIn("| 9:3 | Install › Linux | EN-04 | <code>seamless</code> |", out)
        self.assertIn("| 13:", out)
        self.assertIn("| Use | EN-04 |", out)
        self.assertTrue(out.startswith("# deslop diagnosis\n"))

    def test_cells_cannot_break_the_table(self):
        self.assertEqual(diagnosis.code("a|b <c>"), "<code>a&#124;b &lt;c&gt;</code>")
        self.assertEqual(diagnosis.cell("x | y\nz <b>"), "x \\| y z &lt;b&gt;")

    def test_section_paths_follow_heading_levels(self):
        outline = [(1, 2, "A"), (3, 3, "B"), (5, 2, "C"), (7, 4, "D")]
        self.assertEqual(diagnosis.section_at(outline, 4), "A › B")
        self.assertEqual(diagnosis.section_at(outline, 8), "C › D")
        self.assertEqual(diagnosis.section_at(outline, 0), "")
        self.assertEqual(diagnosis.section_at([(1, 1, "T"), (2, 2, "S")], 3), "S")
        self.assertEqual(diagnosis.section_at([(1, 1, "T"), (2, 1, "U")], 3), "U")

    def test_density_exempt_cues_and_baseline_are_reported_separately(self):
        shutil.copyfile(EXAMPLES / "before.en.md", self.tmp / "README.md")
        base = self.tmp / "base.json"
        run(detect, "README.md", "--out", base)
        with (self.tmp / "README.md").open("a", encoding="utf-8") as f:
            f.write("\nA new and robust line.\n")
        code, out, _ = run(detect, "README.md", "--baseline", base, "--format", "markdown")
        self.assertEqual(code, 1)
        self.assertIn("accepted by the baseline and not listed", out)
        self.assertEqual(out.count("| EN-04 | <code>robust</code>"), 1)
        self.assertIn("### Where to read for perspectives", out)
        self.assertIn("| 23 | Conclusion | STR-02 Closing that restates the body |", out)
        self.assertNotIn("<details>", out)

    def test_density_section_and_clean_documents(self):
        body = "\n\n".join(f"## H{i}\n\nOne line of prose for section {i} that stays plain." for i in range(12))
        self.write("doc.md", body + "\n")
        self.write("clean.md", "Plain words.\n")
        _, out, _ = run(detect, "doc.md", "clean.md", "--format", "markdown")
        self.assertIn("### Density across the document", out)
        self.assertIn("| DEN-08 | <code>length_cv=0.0 (min 0.3)</code> |", out)
        self.assertIn("No hits and no cues.", out)

    def test_snapshot_scans_render_too(self):
        self.write("docs/doc.md", (EXAMPLES / "before.ja.md").read_text(encoding="utf-8"))
        out = self.tmp / "run"
        self.assertEqual(run(snapshot, out, "--root", self.tmp / "docs", "--copy", "docs/doc.md")[0], 0)
        code, text, _ = run(detect, "--snapshot", out, "--format", "markdown")
        self.assertEqual(code, 1)
        self.assertIn("## <code>doc.md</code>", text)
        self.assertIn("### Open hits by section", text)


if __name__ == "__main__":
    unittest.main()
