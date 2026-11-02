"""Regression tests for run input validation and file boundaries."""
import contextlib
import copy
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import contract_check  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
import preserve_check  # noqa: E402
import snapshot  # noqa: E402


class RunFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.docs, self.out = self.base / "docs", self.base / "run"
        self.docs.mkdir()
        (self.docs / "guide.md").write_text("Cache entries expire.\n", encoding="utf-8")

    def make_snapshot(self, copy_mode=True, paths=None):
        args = [str(self.out), "--root", str(self.docs), *map(str, paths or [self.docs])]
        if copy_mode:
            args.append("--copy")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snapshot.main(args), 0)
        return common.load_json(self.out / "snapshot.json")

    def make_run(self):
        self.make_snapshot()
        data = {
            "schema_version": 1,
            "meta": {"target": str(self.docs), "lang": "en", "mode": "copy",
                     "assessor": "test", "date": "2026-10-30"},
            "voice": {"source": "inferred", "rules": ["Use direct statements."]},
            "perspectives": [{"id": p["id"], "result": "N/A", "note": "Checked; absent."}
                             for p in common.load_rules()["perspectives"]],
        }
        self.record = self.out / "findings.json"
        findings.merge(self.record, [self.fragment(data)])
        result = detect.scan_snapshot(self.out, common.load_rules(), [])
        for name in ("detect.before.json", "detect.after.json"):
            common.write_json(self.out / name, result)
        common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
        findings.render(self.out)
        self.assertEqual(contract_check.problems(self.out), [])

    def fragment(self, data):
        path = self.base / "fragment.json"
        common.write_json(path, data)
        return path


class SnapshotValidationTests(RunFixture):
    def test_generated_copy_and_in_place_snapshots_load(self):
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.out = self.base / ("copy" if copy_mode else "in-place")
                saved = self.make_snapshot(copy_mode)
                loaded, work = common.load_snapshot(self.out)
                self.assertEqual(loaded, saved)
                self.assertEqual(work, self.out / "rewritten" if copy_mode else self.docs)

    def test_snapshot_may_target_only_part_of_the_document_root(self):
        (self.docs / "other.md").write_text("Other notes.\n", encoding="utf-8")
        for copy_mode in (True, False):
            with self.subTest(copy=copy_mode):
                self.out = self.base / ("copy" if copy_mode else "in-place")
                saved = self.make_snapshot(copy_mode, [self.docs / "guide.md"])
                loaded, _ = common.load_snapshot(self.out)
                self.assertEqual(loaded, saved)
                self.assertEqual([entry["path"] for entry in loaded["files"]], ["guide.md"])
                self.assertEqual(detect.scan_snapshot(self.out, common.load_rules(), [])["summary"]["files"], 1)

    def test_original_inventory_does_not_follow_symlink_directories(self):
        saved = self.make_snapshot()
        external = self.base / "external"
        external.mkdir()
        (external / "other.md").write_text("Other notes.\n", encoding="utf-8")
        (self.out / "original" / "external").symlink_to(external, target_is_directory=True)
        self.assertEqual(common.load_snapshot(self.out)[0], saved)

    def test_invalid_manifest_fields_raise_value_error(self):
        saved = self.make_snapshot()
        mutations = [
            [],
            {**saved, "tool": "other"},
            {**saved, "root": []},
            {**saved, "root": "docs"},
            {**saved, "work": None},
            {**saved, "mode": []},
            {**saved, "files": []},
            {**saved, "files": {}},
            {**saved, "files": [None]},
            {**saved, "files": [{"path": "guide.md"}]},
            {**saved, "files": [{"path": "guide.md", "sha256": "bad"}]},
        ]
        for bad in mutations:
            with self.subTest(snapshot=bad):
                common.write_json(self.out / "snapshot.json", bad)
                with self.assertRaises(ValueError):
                    common.load_snapshot(self.out)

    def test_manifest_paths_are_canonical_relative_and_unique(self):
        saved = self.make_snapshot()
        for path in ("", ".", "../guide.md", "/guide.md", "./guide.md",
                     "nested/../guide.md", "nested//guide.md", "guide.md/", []):
            with self.subTest(path=path):
                bad = copy.deepcopy(saved)
                bad["files"][0]["path"] = path
                common.write_json(self.out / "snapshot.json", bad)
                with self.assertRaises(ValueError):
                    common.load_snapshot(self.out)
        saved["files"].append(dict(saved["files"][0]))
        common.write_json(self.out / "snapshot.json", saved)
        with self.assertRaises(ValueError):
            common.load_snapshot(self.out)

    def test_manifest_work_matches_mode(self):
        saved = self.make_snapshot()
        for mode, work in (("copy", self.out / "original"), ("in-place", self.out / "rewritten")):
            with self.subTest(mode=mode):
                common.write_json(self.out / "snapshot.json", {**saved, "mode": mode, "work": str(work)})
                with self.assertRaises(ValueError):
                    common.load_snapshot(self.out)

    def test_manifest_cannot_recast_originals_as_in_place_targets(self):
        saved = self.make_snapshot()
        saved.update(mode="in-place", root=str(self.out / "original"), work=str(self.out / "original"))
        common.write_json(self.out / "snapshot.json", saved)
        with self.assertRaises(ValueError):
            common.load_snapshot(self.out)

    def test_resolved_files_cannot_escape_run_roots(self):
        self.make_snapshot()
        outside = self.base / "outside.md"
        outside.write_text("Cache entries expire.\n", encoding="utf-8")
        for directory in ("original", "rewritten"):
            with self.subTest(directory=directory):
                target = self.out / directory / "guide.md"
                target.unlink()
                target.symlink_to(outside)
                try:
                    with self.assertRaises(ValueError):
                        common.load_snapshot(self.out)
                finally:
                    target.unlink()
                    target.write_text(outside.read_text(encoding="utf-8"), encoding="utf-8")

    def test_snapshot_deduplicates_resolved_input_files(self):
        (self.docs / "alias.md").symlink_to("guide.md")
        saved = self.make_snapshot()
        self.assertEqual([entry["path"] for entry in saved["files"]], ["guide.md"])
        self.assertEqual(detect.scan_snapshot(self.out, common.load_rules(), [])["summary"]["files"], 1)

    def test_snapshot_checks_all_boundaries_before_copying(self):
        outside = self.base / "outside.md"
        outside.write_text("Outside.\n", encoding="utf-8")
        (self.docs / "z.md").symlink_to(outside)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            self.make_snapshot()
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.out.exists())

    def test_snapshot_root_must_be_a_directory(self):
        target = self.docs / "guide.md"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                snapshot.main([str(self.out), "--root", str(target), str(target), "--copy"])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.out.exists())


class ContractValidationTests(RunFixture):
    def test_omitted_manifest_file_does_not_hide_open_hits(self):
        (self.docs / "other.md").write_text("Other notes.\n", encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text("I hope this helps.\n", encoding="utf-8")
        saved = common.load_json(self.out / "snapshot.json")
        saved["files"] = [entry for entry in saved["files"] if entry["path"] != "guide.md"]
        common.write_json(self.out / "snapshot.json", saved)
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            self.assertEqual(findings.main(["report", str(self.out)]), 2)
        self.assertIn("original/guide.md", error.getvalue())
        self.assertTrue(any("original/guide.md" in problem for problem in contract_check.problems(self.out)))

    def test_redirected_manifest_does_not_hide_open_hits(self):
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text("I hope this helps.\n", encoding="utf-8")
        saved = common.load_json(self.out / "snapshot.json")
        saved["work"] = str(self.out / "original")
        common.write_json(self.out / "snapshot.json", saved)
        self.assertTrue(contract_check.problems(self.out))

    def test_invalid_snapshot_is_a_reported_contract_failure(self):
        self.make_run()
        for invalid in ("{", "[]", '{"files": []}'):
            with self.subTest(snapshot=invalid):
                (self.out / "snapshot.json").write_text(invalid, encoding="utf-8")
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(contract_check.main([str(self.out)]), 1)

    def test_invalid_record_is_a_reported_contract_failure(self):
        self.make_run()
        data = common.load_json(self.record)
        data["voice"]["source"] = []
        common.write_json(self.record, data)
        problems = contract_check.problems(self.out)
        self.assertTrue(any("voice.source" in problem for problem in problems))


class RecordValidationTests(RunFixture):
    def test_scalar_fields_are_checked_before_set_or_dict_lookups(self):
        self.make_run()
        before = self.record.read_bytes()
        finding = {"id": "T-001", "path": "guide.md", "rule": "EN-04", "occurrences": 1,
                   "action": "deleted", "before": "robust"}
        fragments = [
            {"voice": {"source": []}},
            {"findings": [{**finding, "id": []}]},
            {"findings": [{**finding, "rule": []}]},
            {"findings": [{**finding, "action": {}}]},
            {"perspectives": [{"id": [], "result": "N/A", "note": "Absent."}]},
            {"perspectives": [{"id": "CON-01", "result": {}, "note": "Absent."}]},
            {"exemptions": [{"path": "guide.md", "rule": [], "reason": "Quotation."}]},
            {"preservation": [{"path": "guide.md", "kind": {}, "value": "3", "reason": "Removed."}]},
        ]
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                with self.assertRaises(findings.RecordError):
                    findings.merge(self.record, [self.fragment(fragment)])
                self.assertEqual(self.record.read_bytes(), before)

    def test_merge_checks_the_existing_record_shape(self):
        self.make_run()
        valid = common.load_json(self.record)
        for invalid in ([], {**valid, "meta": []}, {**valid, "findings": ["T-001"]},
                        {**valid, "findings": [{"id": []}]}):
            with self.subTest(record=invalid):
                common.write_json(self.record, invalid)
                before = self.record.read_bytes()
                with self.assertRaises(findings.RecordError):
                    findings.merge(self.record, [self.fragment({"meta": {"assessor": "updated"}})])
                self.assertEqual(self.record.read_bytes(), before)

    def test_malformed_scalar_is_a_usage_error_from_merge_cli(self):
        self.make_run()
        fragment = self.fragment({"voice": {"source": []}})
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            result = findings.main(["merge", str(self.record), str(fragment)])
        self.assertEqual(result, 2)
        self.assertIn("voice.source", error.getvalue())


if __name__ == "__main__":
    unittest.main()
