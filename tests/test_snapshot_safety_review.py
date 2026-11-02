"""Snapshots publish complete runs and resolve explicit inputs unambiguously."""
import contextlib
import errno
import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import unittest
from unittest.mock import patch

from test_run_validation import RunFixture

import common
import detect
import snapshot


class SnapshotPublicationTests(RunFixture):
    def setUp(self):
        super().setUp()
        self.other = self.docs / "other.md"
        self.other.write_bytes(b"Other notes.\r\n")

    def command(self, copy_mode=True):
        return [str(self.out), "--root", str(self.docs), str(self.docs),
                *(["--copy"] if copy_mode else [])]

    def assert_usage_failure(self, copy_mode=True):
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as raised:
                snapshot.main(self.command(copy_mode))
        self.assertEqual(raised.exception.code, 2)
        self.assertNotIn("Traceback", error.getvalue())
        return error.getvalue()

    def assert_unpublished(self, existed=False):
        self.assertEqual(self.out.exists(), existed)
        if existed:
            self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(list(self.out.parent.glob(f".{self.out.name}.*")), [])
        self.assertEqual((self.docs / "guide.md").read_bytes(), b"Cache entries expire.\n")
        self.assertEqual(self.other.read_bytes(), b"Other notes.\r\n")

    def test_late_source_read_failure_leaves_the_destination_retryable(self):
        read_bytes = Path.read_bytes

        def unreadable(path):
            if path == self.other:
                raise OSError(errno.EIO, "cannot read document", str(path))
            return read_bytes(path)

        for copy_mode in (True, False):
            for existed in (True, False):
                with self.subTest(copy=copy_mode, existed=existed):
                    self.out = self.base / f"run-{copy_mode}-{existed}"
                    if existed:
                        self.out.mkdir()
                    with patch.object(Path, "read_bytes", unreadable):
                        error = self.assert_usage_failure(copy_mode)
                    self.assertIn(str(self.other), error)
                    self.assert_unpublished(existed)
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(snapshot.main(self.command(copy_mode)), 0)
                    common.load_snapshot(self.out)

    def test_copy_write_failure_removes_all_staged_files(self):
        write_bytes = Path.write_bytes

        def unwritable(path, data):
            if path.name == "other.md":
                raise OSError(errno.ENOSPC, "no space for document", str(path))
            return write_bytes(path, data)

        with patch.object(Path, "write_bytes", unwritable):
            self.assertIn("no space for document", self.assert_usage_failure())
        self.assert_unpublished()

    def test_manifest_failure_removes_all_staged_files(self):
        with patch.object(snapshot, "write_json", side_effect=OSError(errno.ENOSPC, "no space for manifest")):
            self.assertIn("no space for manifest", self.assert_usage_failure())
        self.assert_unpublished()

    def test_run_directory_listing_errors_are_usage_errors(self):
        self.out.mkdir()
        iterdir = Path.iterdir

        def unreadable(path):
            if path == self.out:
                raise OSError(errno.EACCES, "cannot list run directory", str(path))
            return iterdir(path)

        with patch.object(Path, "iterdir", unreadable):
            self.assertIn("cannot list run directory", self.assert_usage_failure())
        self.assert_unpublished(existed=True)

    def test_concurrent_destination_content_is_not_overwritten(self):
        write_json = snapshot.write_json

        def finish_and_compete(path, data):
            write_json(path, data)
            self.out.mkdir(exist_ok=True)
            (self.out / "keep.txt").write_bytes(b"Keep this competing output.\n")

        with patch.object(snapshot, "write_json", finish_and_compete):
            self.assert_usage_failure()
        self.assertEqual([p.name for p in self.out.iterdir()], ["keep.txt"])
        self.assertEqual((self.out / "keep.txt").read_bytes(), b"Keep this competing output.\n")
        self.assertEqual(list(self.base.glob(".run.*")), [])

    def test_success_uses_final_paths_and_preserves_existing_directory_mode(self):
        self.out.mkdir(mode=0o700)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snapshot.main([*self.command(), "--compare"]), 0)
        saved, work = common.load_snapshot(self.out)
        self.assertEqual(saved["workflow"], "compare-three")
        self.assertEqual(work, self.out / "rewritten")
        self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o700)
        self.assertEqual(list(self.base.glob(".run.*")), [])
        for entry in saved["files"]:
            original = self.out / "original" / entry["path"]
            self.assertEqual(original.read_bytes(), (self.docs / entry["path"]).read_bytes())
            self.assertEqual(original.read_bytes(), (work / entry["path"]).read_bytes())
            self.assertEqual(entry["sha256"], common.sha256_file(original))

    def test_long_valid_output_names_leave_room_for_the_staging_suffix(self):
        for existed in (False, True):
            with self.subTest(existed=existed):
                parent = self.base / f"long-{existed}"
                parent.mkdir()
                self.out = parent / ("r" * 250)
                if existed:
                    self.out.mkdir()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(snapshot.main(self.command()), 0)
                common.load_snapshot(self.out)
                self.assertEqual(list(parent.iterdir()), [self.out])


class GenrePathSafetyTests(RunFixture):
    def setUp(self):
        super().setUp()
        self.nested = self.docs / "nested"
        self.nested.mkdir()
        (self.nested / "guide.md").write_text("Let me know if you have any questions.\n", encoding="utf-8")
        self.files = [self.docs / "guide.md", self.nested / "guide.md"]
        self.rules = common.load_rules()

    @contextlib.contextmanager
    def nested_cwd(self):
        previous = Path.cwd()
        os.chdir(self.nested)
        try:
            yield
        finally:
            os.chdir(previous)

    def test_a_relative_genre_cannot_silently_exempt_two_documents(self):
        with self.nested_cwd():
            with self.assertRaisesRegex(ValueError, "ambiguous.*absolute path"):
                common.assign_genres(["guide.md=message"], self.files, self.docs, self.rules)

    def test_absolute_and_unique_root_relative_genres_keep_their_target(self):
        with self.nested_cwd():
            for name in (str(self.nested / "guide.md"), "nested/guide.md"):
                with self.subTest(path=name):
                    self.assertEqual(common.assign_genres([f"{name}=message"], self.files, self.docs, self.rules),
                                     {"guide.md": "general", "nested/guide.md": "message"})

    def test_identical_current_and_root_relative_targets_remain_valid(self):
        previous = Path.cwd()
        os.chdir(self.docs)
        try:
            assigned = common.assign_genres(["guide.md=message"], self.files, self.docs, self.rules)
        finally:
            os.chdir(previous)
        self.assertEqual(assigned, {"guide.md": "message", "nested/guide.md": "general"})

    def test_ambiguous_genre_is_rejected_before_snapshot_or_detection_output(self):
        output = self.base / "detect.json"
        output.write_bytes(b"Previous detection.\n")
        commands = (
            lambda: snapshot.main([str(self.out), "--root", str(self.docs), "--copy",
                                   "--genre", "guide.md=message", str(self.docs)]),
            lambda: detect.main([str(self.docs), "--root", str(self.docs), "--genre", "guide.md=message",
                                 "--quiet", "--out", str(output)]),
        )
        with self.nested_cwd():
            for command in commands:
                with self.subTest(command=command), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        command()
                    self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.out.exists())
        self.assertEqual(output.read_bytes(), b"Previous detection.\n")


@unittest.skipUnless(shutil.which("make"), "make is not installed")
class MakefilePathSafetyTests(RunFixture):
    def setUp(self):
        super().setUp()
        self.checkout = self.base / "checkout with spaces and 'quotes'"
        self.skill = self.checkout / "skills" / "deslop"
        self.skill.mkdir(parents=True)
        self.makefile = self.checkout / "Makefile"
        shutil.copyfile(Path(__file__).resolve().parents[1] / "Makefile", self.makefile)
        self.host = self.base / "host with spaces and 'quotes'"
        self.host.mkdir()

    def run_make(self, target, outside=False):
        args = ["make", "--no-print-directory"]
        if outside:
            args += ["-f", str(self.makefile)]
        args += [target, f"SKILLS_DIR={self.host}"]
        return subprocess.run(args, cwd=self.base if outside else self.checkout,
                              capture_output=True, text=True, timeout=10)

    def test_link_and_unlink_use_the_complete_checkout_path(self):
        for outside in (False, True):
            with self.subTest(outside=outside):
                result = self.run_make("link", outside)
                self.assertEqual(result.returncode, 0, result.stderr)
                installed = self.host / "deslop"
                self.assertTrue(installed.is_symlink())
                self.assertEqual(installed.readlink(), self.skill)
                self.assertTrue(installed.is_dir())
                result = self.run_make("status", outside)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(str(self.skill), result.stdout)
                result = self.run_make("unlink", outside)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(installed.is_symlink())

    def test_unlink_keeps_a_foreign_symlink(self):
        installed = self.host / "deslop"
        foreign = self.base / "other-skill"
        foreign.mkdir()
        installed.symlink_to(foreign)
        result = self.run_make("unlink")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(installed.readlink(), foreign)

    def test_multiple_makefiles_keep_the_complete_final_filename(self):
        prelude = self.base / "earlier makefile.mk"
        prelude.write_text("EXTRA_SETTING := one\n", encoding="utf-8")
        for target in ("link", "unlink"):
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "--no-print-directory", "-f", str(prelude), "-f", str(self.makefile),
                     target, f"SKILLS_DIR={self.host}"], cwd=self.base,
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                installed = self.host / "deslop"
                if target == "link":
                    self.assertEqual(installed.readlink(), self.skill)
                    self.assertTrue(installed.is_dir())
                else:
                    self.assertFalse(installed.is_symlink())

    def test_newline_checkout_paths_fail_before_creating_or_removing_links(self):
        checkout = self.base / "checkout\nwith newline"
        (checkout / "skills/deslop").mkdir(parents=True)
        makefile = checkout / "Makefile"
        shutil.copyfile(self.makefile, makefile)
        installed = self.host / "deslop"
        for outside in (False, True):
            for target in ("link", "unlink"):
                with self.subTest(outside=outside, target=target):
                    if target == "unlink":
                        installed.symlink_to(self.skill)
                    args = ["make", "--no-print-directory"]
                    if outside:
                        args += ["-f", str(makefile)]
                    result = subprocess.run([*args, target, f"SKILLS_DIR={self.host}"],
                                            cwd=self.base if outside else checkout,
                                            capture_output=True, text=True, timeout=10)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("newlines", result.stderr)
                    if target == "unlink":
                        self.assertEqual(installed.readlink(), self.skill)
                        installed.unlink()
                    else:
                        self.assertFalse(installed.is_symlink())

    def test_unresolved_makefile_paths_fail_before_creating_a_link(self):
        result = subprocess.run(["make", "--no-print-directory", "link", "MAKEFILE_LIST=missing.mk",
                                 f"SKILLS_DIR={self.host}"], cwd=self.checkout,
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot resolve", result.stderr)
        self.assertFalse((self.host / "deslop").is_symlink())


if __name__ == "__main__":
    unittest.main()
