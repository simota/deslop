"""Finding IDs identify one entry per fragment, while later fragments update it."""
import contextlib
import io
import unittest

from test_run_validation import RunFixture

import common
import findings


class FindingRecordTests(RunFixture):
    def finding(self, **fields):
        return {"id": "T-001", "path": "guide.md", "rule": "EN-04", "occurrences": 1,
                "action": "deleted", "before": "robust", **fields}

    def test_merge_rejects_identical_and_conflicting_duplicate_finding_ids(self):
        self.make_run()
        before = self.record.read_bytes()
        for second in (self.finding(), self.finding(rule="EN-07", before="delve")):
            with self.subTest(second=second):
                fragment = {"meta": {"assessor": "must not be saved"},
                            "findings": [self.finding(), second]}
                with self.assertRaisesRegex(findings.RecordError, "findings.*unique"):
                    findings.merge(self.record, [self.fragment(fragment)])
                self.assertEqual(self.record.read_bytes(), before)

    def test_duplicate_finding_fragment_cannot_create_a_record(self):
        self.make_run()
        data = common.load_json(self.record)
        data["findings"] = [self.finding(), self.finding(before="different occurrence")]
        new_record = self.base / "new-findings.json"
        with self.assertRaisesRegex(findings.RecordError, "findings.*unique"):
            findings.merge(new_record, [self.fragment(data)])
        self.assertFalse(new_record.exists())

    def test_merge_cli_rejects_duplicates_without_writing_partial_updates(self):
        self.make_run()
        before = self.record.read_bytes()
        fragment = self.fragment({"findings": [self.finding(), self.finding()]})
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            result = findings.main(["merge", str(self.record), str(fragment)])
        self.assertEqual(result, 2)
        self.assertIn("findings", error.getvalue())
        self.assertIn("unique", error.getvalue())
        self.assertEqual(self.record.read_bytes(), before)

    def test_duplicate_existing_record_is_rejected_before_merge(self):
        self.make_run()
        data = common.load_json(self.record)
        data["findings"] = [self.finding(), self.finding(before="different occurrence")]
        for fragment in ({"meta": {"assessor": "updated"}}, {"findings": [self.finding()]}):
            with self.subTest(fragment=fragment):
                common.write_json(self.record, data)
                before = self.record.read_bytes()
                with self.assertRaisesRegex(findings.RecordError, "findings.*unique"):
                    findings.merge(self.record, [self.fragment(fragment)])
                self.assertEqual(self.record.read_bytes(), before)

    def test_separate_fragments_can_update_a_finding_in_one_merge(self):
        self.make_run()
        first = self.base / "first.json"
        second = self.base / "second.json"
        common.write_json(first, {"findings": [self.finding(), self.finding(id="T-002", rule="EN-07", before="delve")]})
        updated = self.finding(occurrences=2, action="rewritten", after="The cache rejects stale entries.")
        common.write_json(second, {"findings": [updated]})
        findings.merge(self.record, [first, second])
        saved = common.load_json(self.record)
        self.assertEqual(saved["findings"], [updated, self.finding(id="T-002", rule="EN-07", before="delve")])

    def test_separate_merges_can_update_a_finding(self):
        self.make_run()
        for occurrences in (1, 2):
            updated = self.finding(occurrences=occurrences)
            findings.merge(self.record, [self.fragment({"findings": [updated]})])
            self.assertEqual(common.load_json(self.record)["findings"], [updated])


if __name__ == "__main__":
    unittest.main()
