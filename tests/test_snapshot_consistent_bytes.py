"""Snapshot manifest hashes must describe the exact saved bytes."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"))
import common
import snapshot


class SnapshotConsistentBytesTests(unittest.TestCase):
    def test_source_changes_after_read_do_not_corrupt_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            docs = base / "docs"
            docs.mkdir()
            source = docs / "guide.md"
            original = b"Original content.\n"
            source.write_bytes(original)
            out = base / "run"
            real_read = Path.read_bytes
            changed = False

            def read_and_mutate(path):
                nonlocal changed
                data = real_read(path)
                if path == source and not changed:
                    changed = True
                    source.write_bytes(b"Modified during snapshot.\n")
                return data

            with patch.object(Path, "read_bytes", read_and_mutate):
                self.assertEqual(snapshot.main([
                    str(out), "--root", str(docs), "--copy", str(docs)
                ]), 0)
            self.assertTrue(changed)
            saved = common.load_json(out / "snapshot.json")
            self.assertEqual(saved["files"][0]["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual((out / "original/guide.md").read_bytes(), original)
            self.assertEqual((out / "rewritten/guide.md").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
