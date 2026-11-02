"""Candidate initialization must publish complete copies of verified bytes."""
from pathlib import Path
from unittest.mock import patch
import unittest

from test_run_validation import RunFixture

import common
import comparison


class CandidateInitializationTests(RunFixture):
    def prepare(self):
        saved = self.make_snapshot()
        saved["workflow"] = "compare-three"
        common.write_json(self.out / "snapshot.json", saved)
        return self.out / "original" / "guide.md"

    def test_each_candidate_uses_the_bytes_that_passed_the_original_hash_check(self):
        original = self.prepare()
        expected = original.read_bytes()
        real_read = Path.read_bytes
        changed = False

        def read_and_change(path):
            nonlocal changed
            data = real_read(path)
            if path == original and not changed:
                changed = True
                original.write_bytes(b"Changed during candidate initialization.\n")
            return data

        with patch.object(Path, "read_bytes", read_and_change):
            comparison.init(self.out)
        self.assertTrue(changed)
        for identity in comparison.CANDIDATE_IDS:
            with self.subTest(candidate=identity):
                self.assertEqual((self.out / "candidates" / identity / "guide.md").read_bytes(), expected)

    def test_failed_initialization_leaves_no_partial_candidates_and_can_be_retried(self):
        original = self.prepare()
        expected_entries = set(self.out.iterdir())
        real_mkdir = Path.mkdir

        def fail_second_candidate(path, *args, **kwargs):
            if path.name == "B":
                raise PermissionError("candidate directory is not writable")
            return real_mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", fail_second_candidate):
            with self.assertRaisesRegex(PermissionError, "not writable"):
                comparison.init(self.out)
        self.assertEqual(set(self.out.iterdir()), expected_entries)
        comparison.init(self.out)
        for identity in comparison.CANDIDATE_IDS:
            self.assertEqual((self.out / "candidates" / identity / "guide.md").read_bytes(), original.read_bytes())

    def test_invalid_later_original_does_not_publish_or_leave_staging_files(self):
        (self.docs / "second.md").write_text("Read the cache.\n", encoding="utf-8")
        self.prepare()
        (self.out / "original" / "second.md").write_text("Changed after snapshot.\n", encoding="utf-8")
        expected_entries = set(self.out.iterdir())
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            comparison.init(self.out)
        self.assertEqual(set(self.out.iterdir()), expected_entries)


if __name__ == "__main__":
    unittest.main()
