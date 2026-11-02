"""Directory read errors must not turn a partial inventory into a clean run."""
import contextlib
import errno
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check
import snapshot


def unreadable_directory(directory, error=errno.EACCES):
    """Inject a real scandir failure, including when tests run as root."""
    scandir = common.os.scandir

    def scan(path):
        if Path(path) == directory:
            raise OSError(error, "cannot read directory", str(directory))
        return scandir(path)

    return patch.object(common.os, "scandir", side_effect=scan)


def unreadable_entry(target, method):
    """Make a directory entry's type lookup fail without replacing its listing."""
    scandir = common.os.scandir

    class Entries:
        def __init__(self, path):
            self.entries = scandir(path)

        def __iter__(self):
            return self

        def __next__(self):
            entry = next(self.entries)
            if Path(entry.path) == target:
                proxy = Mock(wraps=entry)
                proxy.name, proxy.path = entry.name, entry.path
                getattr(proxy, method).side_effect = OSError(errno.EIO, "cannot read entry", str(target))
                return proxy
            return entry

        def __enter__(self):
            self.entries.__enter__()
            return self

        def __exit__(self, *args):
            return self.entries.__exit__(*args)

    return patch.object(common.os, "scandir", side_effect=Entries)


class InventoryErrorTests(RunFixture):
    def setUp(self):
        super().setUp()
        self.nested = self.docs / "nested"
        self.nested.mkdir()
        (self.nested / "other.md").write_text("Other notes.\n", encoding="utf-8")

    def test_document_inventory_propagates_root_and_nested_read_errors(self):
        for directory in (self.docs, self.nested):
            for error in (errno.EACCES, errno.EIO):
                with self.subTest(directory=directory, error=error):
                    with unreadable_directory(directory, error):
                        with self.assertRaises(OSError) as raised:
                            common.iter_docs([self.docs])
                    self.assertEqual(raised.exception.errno, error)
                    self.assertEqual(raised.exception.filename, str(directory))

    def test_document_inventory_propagates_entry_type_errors(self):
        for target, method in ((self.nested, "is_dir"), (self.docs / "guide.md", "is_file")):
            with self.subTest(target=target, method=method):
                with unreadable_entry(target, method), self.assertRaises(OSError) as raised:
                    common.iter_docs([self.docs])
                self.assertEqual(raised.exception.errno, errno.EIO)

    def test_original_inventory_propagates_entry_type_errors(self):
        self.make_run()
        for name, method in (("nested", "is_dir"), ("guide.md", "is_file")):
            target = self.out / "original" / name
            with self.subTest(target=target, method=method):
                with unreadable_entry(target, method), self.assertRaises(OSError) as raised:
                    common.load_snapshot(self.out)
                self.assertEqual(raised.exception.errno, errno.EIO)

    def test_original_inventory_cannot_ignore_entry_stat_errors(self):
        self.make_run()
        extra = self.out / "original/extra.md"
        extra.write_text("Other notes.\n", encoding="utf-8")
        stat = common.os.stat

        def unavailable(path, *args, **kwargs):
            if path == extra or path == str(extra):
                raise OSError(errno.EIO, "cannot stat file", str(path))
            return stat(path, *args, **kwargs)

        with patch.object(common.os, "stat", unavailable):
            # Python 3.14 Path.is_file() suppresses this error. Inventory must
            # still reject the unrecorded entry or propagate the lookup error.
            with self.assertRaises((OSError, ValueError)):
                common.load_snapshot(self.out)

    def test_snapshot_refuses_partial_inventory_before_writing(self):
        with unreadable_directory(self.nested):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    snapshot.main([str(self.out), "--root", str(self.docs), "--copy", str(self.docs)])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.out.exists())
        self.assertEqual((self.docs / "guide.md").read_text(), "Cache entries expire.\n")

    def test_detect_refuses_partial_inventory_without_replacing_output(self):
        output = self.base / "detect.json"
        output.write_text("previous result\n", encoding="utf-8")
        error = io.StringIO()
        with unreadable_directory(self.nested):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
                with self.assertRaises(SystemExit) as raised:
                    detect.main([str(self.docs), "--quiet", "--out", str(output)])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn(str(self.nested), error.getvalue())
        self.assertEqual(output.read_text(), "previous result\n")

    def test_unreadable_originals_cannot_hide_an_omitted_manifest_entry(self):
        self.make_run()
        saved = common.load_json(self.out / "snapshot.json")
        saved["files"] = [entry for entry in saved["files"] if entry["path"] != "nested/other.md"]
        common.write_json(self.out / "snapshot.json", saved)
        (self.out / "rewritten/nested/other.md").write_text("I hope this helps.\n", encoding="utf-8")
        original = self.out / "original/nested"
        report = (self.out / "report.md").read_bytes()
        with unreadable_directory(original):
            for reader in (lambda: common.load_snapshot(self.out),
                           lambda: detect.scan_snapshot(self.out, common.load_rules(), []),
                           lambda: preserve_check.check(self.out),
                           lambda: findings.render(self.out)):
                with self.subTest(reader=reader), self.assertRaises(OSError):
                    reader()
            errors = contract_check.problems(self.out)
        self.assertTrue(any("cannot check run" in error and str(original) in error for error in errors), errors)
        self.assertEqual((self.out / "report.md").read_bytes(), report)

    def test_run_cli_reports_unreadable_originals_as_failure(self):
        self.make_run()
        original = self.out / "original/nested"
        with unreadable_directory(original):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                for command in (lambda: detect.main(["--snapshot", str(self.out), "--quiet"]),
                                lambda: preserve_check.main([str(self.out)])):
                    with self.subTest(command=command):
                        with self.assertRaises(SystemExit) as raised:
                            command()
                        self.assertEqual(raised.exception.code, 2)
                self.assertEqual(findings.main(["report", str(self.out)]), 2)
                self.assertEqual(contract_check.main([str(self.out)]), 1)

    def test_input_inventory_still_skips_tool_directories(self):
        skipped = self.docs / "node_modules"
        skipped.mkdir()
        (skipped / "hidden.md").write_text("I hope this helps.\n", encoding="utf-8")
        with unreadable_directory(skipped):
            files = common.iter_docs([self.docs])
        self.assertEqual({f.relative_to(self.docs).as_posix() for f in files}, {"guide.md", "nested/other.md"})

    def test_input_inventory_handles_explicit_symlinks_without_following_nested_directories(self):
        root_alias = self.base / "docs-alias"
        root_alias.symlink_to(self.docs, target_is_directory=True)
        file_alias = self.base / "guide-alias.md"
        file_alias.symlink_to(self.docs / "guide.md")
        external = self.base / "external"
        external.mkdir()
        (external / "extra.md").write_text("Other notes.\n", encoding="utf-8")
        (self.docs / "external").symlink_to(external, target_is_directory=True)
        with unreadable_directory(self.docs / "external"):
            files = common.iter_docs([root_alias, file_alias])
        self.assertEqual({f.resolve() for f in files}, {self.docs / "guide.md", self.nested / "other.md"})

    def test_original_inventory_still_ignores_broken_symlinks(self):
        self.make_run()
        (self.out / "original/broken.md").symlink_to("absent.md")
        self.assertEqual(common.load_snapshot(self.out)[0], common.load_json(self.out / "snapshot.json"))

    def test_original_inventory_does_not_skip_tool_named_directories(self):
        self.make_run()
        unrecorded = self.out / "original/node_modules/extra.md"
        unrecorded.parent.mkdir()
        unrecorded.write_text("Other notes.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "original/node_modules/extra.md is not recorded"):
            common.load_snapshot(self.out)


if __name__ == "__main__":
    unittest.main()
