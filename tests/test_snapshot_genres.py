"""Every run command rejects invalid snapshot genres at its input boundary."""
import contextlib
import io
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check


class SnapshotGenreTests(RunFixture):
    def test_invalid_genres_fail_closed_in_every_run_reader(self):
        self.make_run()
        saved = common.load_json(self.out / "snapshot.json")
        for genre in ([], {}, None, True, 1, "", "poem"):
            with self.subTest(genre=genre):
                saved["files"][0]["genre"] = genre
                common.write_json(self.out / "snapshot.json", saved)
                for reader in (lambda: common.load_snapshot(self.out),
                               lambda: detect.scan_snapshot(self.out, common.load_rules(), []),
                               lambda: preserve_check.check(self.out),
                               lambda: findings.build_report(self.out)):
                    with self.assertRaisesRegex(ValueError, "unknown genre"):
                        reader()
                errors = contract_check.problems(self.out)
                self.assertTrue(any("unknown genre" in error for error in errors), errors)

    def test_invalid_genre_is_a_usage_error_in_run_commands(self):
        self.make_run()
        saved = common.load_json(self.out / "snapshot.json")
        saved["files"][0]["genre"] = []
        common.write_json(self.out / "snapshot.json", saved)
        for command in (lambda: detect.main(["--snapshot", str(self.out), "--quiet"]),
                        lambda: preserve_check.main([str(self.out)])):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    command()
            self.assertEqual(raised.exception.code, 2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(findings.main(["report", str(self.out)]), 2)
            self.assertEqual(contract_check.main([str(self.out)]), 1)

    def test_legacy_snapshot_without_genre_still_loads(self):
        (self.docs / "README.md").write_text("Cache entries expire.\n", encoding="utf-8")
        self.make_run()
        saved = common.load_json(self.out / "snapshot.json")
        for entry in saved["files"]:
            del entry["genre"]
        common.write_json(self.out / "snapshot.json", saved)
        self.assertEqual(common.load_snapshot(self.out)[0], saved)
        result = detect.scan_snapshot(self.out, common.load_rules(), [])
        self.assertEqual({entry["path"]: entry["genre"] for entry in result["files"]},
                         {"README.md": "readme", "guide.md": "general"})
        self.assertEqual(preserve_check.check(self.out)["unacknowledged"], 0)
        self.assertEqual(contract_check.problems(self.out), [])


if __name__ == "__main__":
    unittest.main()
