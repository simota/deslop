"""Diagnostic hashes must identify the exact bytes used for their analysis."""
import copy
import unittest
from unittest.mock import patch

from test_run_validation import RunFixture

import common
import comparison
import detect
import findings
import preserve_check


class ReadConsistencyTests(RunFixture):
    def test_detection_hash_describes_the_scanned_bytes_when_the_file_changes(self):
        source = self.docs / "guide.md"
        original = source.read_bytes()
        scan_text = detect.scan_text

        def scan_and_change(*args, **kwargs):
            result = scan_text(*args, **kwargs)
            source.write_bytes(b"We leverage a robust solution.\n")
            return result

        with patch.object(detect, "scan_text", scan_and_change):
            result = detect.scan([source], self.docs, common.load_rules(), [])
        self.assertEqual(result["hits"], [])
        self.assertEqual(result["files"][0]["sha256"], common.sha256_bytes(original))
        self.assertNotEqual(result["files"][0]["sha256"], common.sha256_file(source))

    def test_preservation_hash_describes_the_compared_bytes_when_the_file_changes(self):
        self.make_run()
        working = self.out / "rewritten" / "guide.md"
        original = working.read_bytes()
        facts = preserve_check.facts
        count = 0

        def facts_and_change(*args, **kwargs):
            nonlocal count
            result = facts(*args, **kwargs)
            count += 1
            if count == 2:
                working.write_bytes(b"Cache entries expire after 60 seconds.\n")
            return result

        with patch.object(preserve_check, "facts", facts_and_change):
            result = preserve_check.check(self.out)
        self.assertEqual(result["unacknowledged"], 0)
        self.assertEqual(result["files"][0]["sha256"], common.sha256_bytes(original))
        self.assertNotEqual(result["files"][0]["sha256"], common.sha256_file(working))

    def test_report_stamp_describes_the_rendered_record_when_the_record_changes(self):
        self.make_run()
        original_digest = common.sha256_file(self.record)
        changed = copy.deepcopy(common.load_json(self.record))
        changed["meta"]["assessor"] = "Changed during report generation"
        scan_snapshot = detect.scan_snapshot

        def scan_and_change(*args, **kwargs):
            common.write_json(self.record, changed)
            return scan_snapshot(*args, **kwargs)

        with patch.object(detect, "scan_snapshot", scan_and_change):
            report, _ = findings.build_report(self.out)
        self.assertIn(f"deslop:findings-sha256={original_digest}", report)
        self.assertIn("assessor: test", report)
        self.assertNotIn(changed["meta"]["assessor"], report)

    def test_final_copy_must_match_the_candidate_bytes_that_were_reviewed(self):
        self.make_run()
        original = (self.out / "original/guide.md").read_bytes()
        changed = b"Cache entries expire after 60 seconds.\n"
        candidates = []
        for identity in comparison.CANDIDATE_IDS:
            path = self.out / "candidates" / identity / "guide.md"
            path.parent.mkdir(parents=True)
            path.write_bytes(original)
            candidates.append({
                "id": identity, "sha256": common.sha256_bytes(original), "eligible": True,
                "approach": f"Candidate {identity} retains the original order.",
                "strengths": "Keeps the cache expiry claim.",
                "weaknesses": "The transition could be shorter.",
                "review_note": "Compared every claim with the saved original.",
                "scores": {key: {"score": maximum, "reason": f"Checked {key} against the original."}
                           for key, maximum in comparison.SCORE_LIMITS.items()},
            })
        data = common.load_json(self.record)
        data["comparisons"] = [{
            "path": "guide.md", "candidates": candidates, "selected": "A",
            "reason": "A keeps the original claim and its order.",
            "final_sha256": common.sha256_bytes(changed),
        }]
        selected = self.out / "candidates/A/guide.md"
        (self.out / "rewritten/guide.md").write_bytes(changed)
        scan = detect.scan

        def scan_and_change(files, *args, **kwargs):
            result = scan(files, *args, **kwargs)
            if files == [selected]:
                selected.write_bytes(changed)
            return result

        snap, work = common.load_snapshot(self.out)
        with patch.object(detect, "scan", scan_and_change):
            problems = comparison.problems(self.out, data, snap, work)
        self.assertEqual(problems, ["guide.md: working copy differs from selected candidate A"])
        self.assertEqual(selected.read_bytes(), changed)
        self.assertNotEqual(candidates[0]["sha256"], common.sha256_file(selected))

    def test_decoding_preserves_bom_and_universal_newline_behavior(self):
        source = self.docs / "guide.md"
        text = "Cache entries expire.\nRead fresh entries.\n"
        for bom in (b"", b"\xef\xbb\xbf"):
            for newline in ("\n", "\r\n", "\r"):
                with self.subTest(bom=bom, newline=newline):
                    content = bom + text.replace("\n", newline).encode("utf-8")
                    source.write_bytes(content)
                    self.assertEqual(common.read_text(source), text)
                    result = detect.scan([source], self.docs, common.load_rules(), [])
                    self.assertEqual(result["files"][0]["sha256"], common.sha256_bytes(content))
                    self.assertEqual(result["hits"], [])


if __name__ == "__main__":
    unittest.main()
