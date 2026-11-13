"""status.py reports each step of a run and the next command, without writing."""
import contextlib
import io
import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_deslop  # noqa: E402
from test_deslop import EXAMPLES, load_json  # noqa: E402

import comparison  # noqa: E402
import detect  # noqa: E402
import snapshot  # noqa: E402
import status  # noqa: E402


def steps(result):
    return {s["step"]: s for s in result["steps"]}


def tree(path):
    return {p.relative_to(path).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(path.rglob("*")) if p.is_file()}


class StatusTests(unittest.TestCase):
    # Borrow the run helpers without importing the TestCase itself, so
    # discovery does not run RunContractTests a second time from this module.
    setUp = test_deslop.RunContractTests.setUp
    tearDown = test_deslop.RunContractTests.tearDown
    fragment = test_deslop.RunContractTests.fragment
    setUp_quiet = test_deslop.RunContractTests.setUp_quiet
    complete_run = test_deslop.RunContractTests.complete_run

    def snapshot(self, *extra):
        self.setUp_quiet()
        self.assertEqual(snapshot.main([str(self.out), str(self.docs), "--root", str(self.docs), "--copy", *extra]), 0)

    def main(self, *args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = status.main([str(self.out), *args])
        return code, stdout.getvalue()

    def test_a_fresh_snapshot_points_at_detection_first(self):
        self.snapshot()
        result = status.collect(self.out)
        self.assertFalse(result["complete"])
        self.assertTrue(steps(result)["snapshot"]["done"])
        self.assertEqual(result["next"]["step"], "detect.before")
        self.assertIn("detect.py --snapshot", result["next"]["do"])
        code, text = self.main()
        self.assertEqual(code, 1)
        self.assertIn("[todo] detect.before", text)
        self.assertIn("next: detect.before:", text)

    def test_unaccounted_hits_and_cued_perspectives_are_listed(self):
        self.snapshot()
        detect.main(["--snapshot", str(self.out), "--out", str(self.out / "detect.before.json"), "--quiet"])
        by_step = steps(status.collect(self.out))
        self.assertTrue(by_step["detect.before"]["done"])
        self.assertFalse(by_step["record"]["done"])
        accounting = by_step["accounting"]["todo"]
        self.assertTrue(any(item.startswith("guide.md JA-04 x3 at line 13, 14, 15") for item in accounting), accounting)
        perspectives = by_step["perspectives"]["todo"]
        self.assertEqual(len(perspectives), len(test_deslop.RULES["perspectives"]))
        self.assertTrue(any(p.startswith("STR-02 ") and "cannot be N/A" in p for p in perspectives))

    def test_detection_of_other_originals_is_not_current(self):
        self.snapshot()
        (self.out / "detect.before.json").write_text(json.dumps({"tool": "deslop-detect", "files": [
            {"path": "guide.md", "sha256": "0" * 64}]}), encoding="utf-8")
        self.assertFalse(steps(status.collect(self.out))["detect.before"]["done"])

    def test_a_complete_run_is_complete_and_status_writes_nothing(self):
        self.complete_run()
        before = tree(self.out)
        result = status.collect(self.out)
        self.assertEqual([s["step"] for s in result["steps"] if not s["done"]], [])
        self.assertTrue(result["complete"])
        self.assertIsNone(result["next"])
        code, text = self.main()
        self.assertEqual(code, 0)
        self.assertIn("complete: contract ok", text)
        self.assertEqual(tree(self.out), before)

    def test_a_removed_finding_reopens_accounting(self):
        self.complete_run()
        record = self.out / "findings.json"
        data = load_json(record)
        data["findings"] = [f for f in data["findings"] if f["rule"] != "JA-02"]
        record.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        result = status.collect(self.out)
        self.assertFalse(result["complete"])
        self.assertEqual(result["next"]["step"], "accounting")
        self.assertTrue(any(" JA-02 " in item for item in steps(result)["accounting"]["todo"]))
        self.assertIn("report.md is missing or differs", " ".join(steps(result)["outputs"]["todo"]))

    def test_a_later_edit_shows_open_hits_and_stale_outputs(self):
        self.complete_run()
        doc = self.out / "rewritten" / "guide.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n参考になれば幸いです。ヒット率は 95% 向上します。\n",
                       encoding="utf-8")
        by_step = steps(status.collect(self.out))
        verify = " ".join(by_step["verify"]["todo"])
        self.assertIn("ART-04", verify)
        self.assertIn("added number '95'", verify)
        outputs = " ".join(by_step["outputs"]["todo"])
        self.assertIn("detect.after.json is missing or older", outputs)
        self.assertIn("preserve.json is missing or older", outputs)

    def test_candidates_still_equal_to_the_original_are_todo(self):
        self.snapshot("--compare")
        detect.main(["--snapshot", str(self.out), "--out", str(self.out / "detect.before.json"), "--quiet"])
        result = status.collect(self.out)
        self.assertEqual(result["next"]["step"], "candidates")
        self.assertIn("comparison.py init", result["next"]["do"])
        comparison.init(self.out)
        candidates = steps(status.collect(self.out))["candidates"]
        self.assertEqual(candidates["todo"], [f"candidates/{c}/guide.md is still the original" for c in "ABC"])
        shutil.copyfile(EXAMPLES / "after.ja.md", self.out / "candidates" / "A" / "guide.md")
        by_step = steps(status.collect(self.out))
        self.assertEqual(len(by_step["candidates"]["todo"]), 2)
        self.assertEqual(by_step["comparisons"]["todo"], ["no comparison for guide.md"])

    def test_an_invalid_record_or_missing_working_copy_is_todo_not_unreadable(self):
        # contract_check reports both as failures; status must list them as
        # work to do (exit 1), not refuse the run (exit 2).
        self.complete_run()
        record = self.out / "findings.json"
        valid = record.read_bytes()
        data = load_json(record)
        data["voice"]["source"] = "guess"
        record.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        code, text = self.main()
        self.assertEqual(code, 1, text)
        self.assertIn("[todo] record        findings.json is invalid", text)
        self.assertIn("voice.source", text)

        record.write_bytes(valid)
        (self.out / "rewritten" / "guide.md").unlink()
        code, text = self.main()
        self.assertEqual(code, 1, text)
        self.assertIn("[todo] verify", text)
        self.assertIn("guide.md: working copy missing", text)

    def test_a_directory_that_is_not_a_run_exits_2(self):
        self.out.mkdir()
        self.assertEqual(self.main()[0], 2)

    def test_json_output_and_limit(self):
        self.snapshot()
        code, text = self.main("--json")
        self.assertEqual(code, 1)
        data = json.loads(text)
        self.assertEqual(data["tool"], "deslop-status")
        self.assertEqual(data["next"]["step"], "detect.before")
        _, text = self.main("--limit", "2")
        self.assertIn("more (--limit 0 shows all)", text)


if __name__ == "__main__":
    unittest.main()
