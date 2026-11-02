"""Regression coverage for contradictory perspective records and safe merging."""
import contextlib
import copy
import io
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import contract_check  # noqa: E402
import findings  # noqa: E402
from test_run_validation import RunFixture  # noqa: E402


class PerspectiveRecordTests(RunFixture):
    def duplicate_record(self):
        data = common.load_json(self.record)
        first = data["perspectives"][0]
        first.update(result="not checked", note="This perspective was not read.")
        data["perspectives"].append({**first, "result": "applied", "note": "An older assessment."})
        return data

    def test_record_rejects_identical_and_conflicting_duplicate_perspectives(self):
        self.make_run()
        good = common.load_json(self.record)
        for result in ("N/A", "applied", "not checked"):
            with self.subTest(result=result):
                data = copy.deepcopy(good)
                data["perspectives"].append({**data["perspectives"][0], "result": result})
                with self.assertRaisesRegex(findings.RecordError, "perspectives.*unique"):
                    findings.check_record(data)

    def test_check_cli_rejects_duplicate_perspectives_without_changing_record(self):
        self.make_run()
        common.write_json(self.record, self.duplicate_record())
        before = self.record.read_bytes()
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            result = findings.main(["check", str(self.record)])
        self.assertEqual(result, 2)
        self.assertIn("unique", error.getvalue())
        self.assertEqual(self.record.read_bytes(), before)

    def test_contract_reports_duplicate_perspectives_before_collapsing_them(self):
        self.make_run()
        common.write_json(self.record, self.duplicate_record())
        problems = contract_check.problems(self.out)
        self.assertTrue(any("findings.json" in p and "perspectives" in p and "unique" in p
                            for p in problems), problems)

    def test_report_refuses_to_render_contradictory_perspectives(self):
        self.make_run()
        common.write_json(self.record, self.duplicate_record())
        before = (self.out / "report.md").read_bytes()
        with self.assertRaisesRegex(findings.RecordError, "perspectives.*unique"):
            findings.render(self.out)
        self.assertEqual((self.out / "report.md").read_bytes(), before)

    def test_merge_rejects_existing_duplicates_even_when_fragment_updates_the_id(self):
        self.make_run()
        duplicate = self.duplicate_record()
        for fragment in ({"meta": {"assessor": "updated"}},
                         {"perspectives": [{"id": duplicate["perspectives"][0]["id"],
                                            "result": "applied", "note": "New assessment."}]}):
            with self.subTest(fragment=fragment):
                common.write_json(self.record, duplicate)
                before = self.record.read_bytes()
                with self.assertRaisesRegex(findings.RecordError, "perspectives.*unique"):
                    findings.merge(self.record, [self.fragment(fragment)])
                self.assertEqual(self.record.read_bytes(), before)

    def test_merge_rejects_duplicate_fragment_without_writing_partial_updates(self):
        self.make_run()
        before = self.record.read_bytes()
        fragment = {"meta": {"assessor": "must not be saved"}, "perspectives": [
            {"id": "STR-01", "result": "not checked", "note": "Not read yet."},
            {"id": "STR-01", "result": "applied", "note": "Conflicting assessment."},
        ]}
        with self.assertRaisesRegex(findings.RecordError, "perspectives.*unique"):
            findings.merge(self.record, [self.fragment(fragment)])
        self.assertEqual(self.record.read_bytes(), before)

    def test_merge_cli_rejects_duplicate_fragment_and_preserves_record(self):
        self.make_run()
        before = self.record.read_bytes()
        perspective = {"id": "STR-01", "result": "applied", "note": "Read."}
        fragment = self.fragment({"perspectives": [perspective, perspective]})
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            result = findings.main(["merge", str(self.record), str(fragment)])
        self.assertEqual(result, 2)
        self.assertIn("unique", error.getvalue())
        self.assertEqual(self.record.read_bytes(), before)

    def test_separate_fragments_still_update_perspectives_by_id(self):
        self.make_run()
        count = len(common.load_json(self.record)["perspectives"])
        for note in ("First assessment.", "Updated assessment."):
            findings.merge(self.record, [self.fragment({"perspectives": [
                {"id": "STR-01", "result": "applied", "note": note},
            ]})])
            data = common.load_json(self.record)
            self.assertEqual(len(data["perspectives"]), count)
            matches = [p for p in data["perspectives"] if p["id"] == "STR-01"]
            self.assertEqual(matches, [{"id": "STR-01", "result": "applied", "note": note}])
        findings.render(self.out)
        self.assertEqual(contract_check.problems(self.out), [])


if __name__ == "__main__":
    unittest.main()
