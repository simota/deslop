"""A snapshot's logical paths and genres survive aliases within its roots."""
import contextlib
import io
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check
import snapshot


RULES = common.load_rules()
LIST_PROSE = "".join(
    f"- {noun} entries expire" + " when the worker finishes reading from disk" * (i % 4 + 2) + ".\n"
    for i, noun in enumerate(("Map", "Tile", "Cache", "Image", "Layer", "Route",
                              "Query", "Page", "Record", "Index", "Session", "State"))
)


class SnapshotIdentityTests(RunFixture):
    def start_run(self, source, copy_mode, genre=None, name="guide.md"):
        # Each subtest has its own root, since in-place mode edits that root.
        number = len(list(self.base.glob("docs-*")))
        self.docs, self.out = self.base / f"docs-{number}", self.base / f"run-{number}"
        self.docs.mkdir()
        (self.docs / name).write_text(source, encoding="utf-8")
        args = [str(self.out), "--root", str(self.docs), str(self.docs)]
        if copy_mode:
            args.append("--copy")
        if genre:
            args.extend(("--genre", genre))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snapshot.main(args), 0)
        self.work = self.out / "rewritten" if copy_mode else self.docs
        self.record = self.out / "findings.json"
        common.write_json(self.record, {
            "schema_version": 1,
            "meta": {"target": str(self.docs), "lang": "en",
                     "mode": "copy" if copy_mode else "in-place",
                     "assessor": "test", "date": "2026-10-31"},
            "voice": {"source": "inferred", "rules": ["Use direct statements."]},
            "perspectives": [{"id": p["id"], "result": "applied", "note": "Read."}
                             for p in RULES["perspectives"]],
        })

    def alias_working_copy(self, name="guide.md", target="moved.md"):
        path = self.work / name
        path.rename(self.work / target)
        path.symlink_to(target)

    def render_run(self):
        exemptions = common.load_json(self.record).get("exemptions", [])
        common.write_json(self.out / "detect.before.json",
                          detect.scan_snapshot(self.out, RULES, exemptions, originals=True))
        common.write_json(self.out / "detect.after.json", detect.scan_snapshot(self.out, RULES, exemptions))
        common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
        findings.render(self.out)

    def test_internal_alias_keeps_explicit_genre_and_contract(self):
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.start_run("Let me know if you have any questions.\n", copy_mode, "message")
                self.alias_working_copy()
                result = detect.scan_snapshot(self.out, RULES, [])
                self.assertEqual([(f["path"], f["genre"]) for f in result["files"]],
                                 [("guide.md", "message")])
                self.assertEqual(result["summary"]["open"], 0)
                self.render_run()
                self.assertEqual(contract_check.problems(self.out), [])
                report = (self.out / "report.md").read_text(encoding="utf-8")
                self.assertIn("`guide.md`", report)
                self.assertNotIn("`moved.md`", report)

    def test_internal_alias_cannot_gain_a_filename_genre_exemption(self):
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.start_run("Cache entries expire.\n", copy_mode, "general")
                (self.work / "guide.md").write_text(LIST_PROSE, encoding="utf-8")
                self.alias_working_copy(target="README.md")
                self.render_run()
                problems = contract_check.problems(self.out)
                self.assertTrue(any(p.startswith("open hit guide.md:") and "DEN-06" in p
                                    for p in problems), problems)
                result = detect.scan_snapshot(self.out, RULES, [])
                hit = next(h for h in result["hits"] if h["rule"] == "DEN-06")
                self.assertEqual(hit["path"], "guide.md")
                self.assertFalse(hit["exempt"])
                self.assertEqual(result["files"][0]["genre"], "general")

    def test_internal_alias_keeps_path_exemptions_and_cues(self):
        source = "Use robust regression.\n\n## Why cache?\n\nIt caches tiles.\n"
        exemption = {"path": "guide.md", "rule": "EN-04", "text": "robust regression",
                     "reason": "Term of art."}
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.start_run(source, copy_mode)
                record = common.load_json(self.record)
                record["exemptions"] = [exemption]
                common.write_json(self.record, record)
                self.alias_working_copy()
                result = detect.scan_snapshot(self.out, RULES, [exemption])
                hit = next(h for h in result["hits"] if h["rule"] == "EN-04")
                self.assertEqual((hit["path"], hit["exempt"]), ("guide.md", "Term of art."))
                cue = next(c for c in result["cues"] if c["perspective"] == "STR-14")
                self.assertEqual(cue["path"], "guide.md")
                self.render_run()
                self.assertEqual(contract_check.problems(self.out), [])

    def test_legacy_genre_is_inferred_from_the_recorded_filename(self):
        for copy_mode in (True, False):
            for name, target, genre in (("README.md", "moved.md", "readme"),
                                        ("guide.md", "README.md", "general")):
                with self.subTest(copy=copy_mode, name=name):
                    self.start_run("Cache entries expire.\n", copy_mode, name=name)
                    saved = common.load_json(self.out / "snapshot.json")
                    del saved["files"][0]["genre"]
                    common.write_json(self.out / "snapshot.json", saved)
                    self.alias_working_copy(name, target)
                    result = detect.scan_snapshot(self.out, RULES, [])
                    self.assertEqual([(f["path"], f["genre"]) for f in result["files"]], [(name, genre)])

    def test_aliases_keep_separate_recorded_identities_in_each_scan(self):
        source = "Let me know if you have any questions.\n"
        for originals in (True, False):
            with self.subTest(originals=originals):
                self.start_run(source, True, "message")
                # Add a second, independently recorded file before making the alias.
                saved = common.load_json(self.out / "snapshot.json")
                for base in (self.out / "original", self.work):
                    (base / "other.md").write_text(source, encoding="utf-8")
                saved["files"].append({**saved["files"][0], "path": "other.md", "genre": "general"})
                common.write_json(self.out / "snapshot.json", saved)
                base = self.out / "original" if originals else self.work
                (base / "guide.md").unlink()
                (base / "guide.md").symlink_to("other.md")
                result = detect.scan_snapshot(self.out, RULES, [], originals=originals)
                self.assertEqual([(f["path"], f["genre"]) for f in result["files"]],
                                 [("guide.md", "message"), ("other.md", "general")])
                self.assertEqual([(h["path"], bool(h["exempt"])) for h in result["hits"]],
                                 [("guide.md", True), ("other.md", False)])

    def test_external_aliases_are_still_rejected(self):
        outside = self.base / "outside.md"
        outside.write_text("Cache entries expire.\n", encoding="utf-8")
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.start_run("Cache entries expire.\n", copy_mode)
                path = self.work / "guide.md"
                path.unlink()
                path.symlink_to(outside)
                with self.assertRaisesRegex(ValueError, "resolves outside"):
                    detect.scan_snapshot(self.out, RULES, [])

    def test_standalone_scan_still_uses_resolved_path_identity(self):
        target = self.docs / "README.md"
        target.write_text(LIST_PROSE, encoding="utf-8")
        alias = self.docs / "alias.md"
        alias.symlink_to(target.name)
        result = detect.scan([alias], self.docs, RULES, [])
        self.assertEqual([(f["path"], f["genre"]) for f in result["files"]], [("README.md", "readme")])
        self.assertTrue(next(h for h in result["hits"] if h["rule"] == "DEN-06")["exempt"])


if __name__ == "__main__":
    unittest.main()
