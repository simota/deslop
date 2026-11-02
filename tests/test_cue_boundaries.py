"""Regression checks for cue boundaries and the original-cue run contract."""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import contract_check  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
import preserve_check  # noqa: E402
from test_run_validation import RunFixture  # noqa: E402

RULES = common.load_rules()
COMPILED = detect.compile_rules(RULES)


def cue_rows(text):
    lang, metrics, _ = detect.scan_text(text, COMPILED, RULES["min_chars"])
    return [(cue["line"], cue["perspective"], cue["text"])
            for cue in detect.perspective_cues(text, lang, metrics["chars"], RULES["min_chars"])]


class CueBoundaryTests(unittest.TestCase):
    def test_front_matter_fences_do_not_hide_body_cues(self):
        body = ("# Tiles\n\nThis guide explains how tiles are cached.\n\n"
                "## Why cache?\n\nIt caches tiles.\n")
        for newline in ("\n", "\r\n"):
            for ending in ("---", "..."):
                for fence in ("```text", "~~~text"):
                    text = f"---\ndescription: |\n  {fence}\n{ending}\n\n" + body
                    with self.subTest(newline=newline, ending=ending, fence=fence):
                        self.assertEqual(cue_rows(text.replace("\n", newline)), [
                            (8, "STR-01", "This guide explains how tiles are cached."),
                            (10, "STR-14", "## Why cache?"),
                        ])

    def test_front_matter_does_not_change_body_code_boundaries(self):
        for fence in ("```", "~~~"):
            text = (f"---\ndescription: |\n  {fence}text\n---\n\n"
                    f"# Tiles\n\n{fence}text\n## Why inside code?\n{fence}\n\n"
                    "## Why cache?\n\nIt caches tiles.\n")
            with self.subTest(fence=fence):
                self.assertEqual(cue_rows(text), [(12, "STR-14", "## Why cache?")])

    def test_front_matter_and_unclosed_body_code_do_not_create_cues(self):
        text = ("---\ndescription: |\n  ```text\n  ## Why include this metadata?\n---\n\n"
                "# Tiles\n\n```text\n## Why inside code?\n")
        self.assertEqual(cue_rows(text), [])


class CueContractTests(RunFixture):
    def test_front_matter_cannot_bypass_the_original_cue_requirement(self):
        text = ("---\ndescription: |\n  ```text\n---\n\n"
                "# Tiles\n\n## Why cache?\n\nIt caches tiles.\n")
        (self.docs / "guide.md").write_text(text, encoding="utf-8")
        self.make_snapshot()
        record = self.out / "findings.json"
        data = {
            "schema_version": 1,
            "meta": {"target": str(self.docs), "lang": "en", "mode": "copy",
                     "assessor": "test", "date": "2026-10-31"},
            "voice": {"source": "inferred", "rules": ["Use direct statements."]},
            "perspectives": [{"id": p["id"], "result": "N/A" if p["id"] == "STR-14" else "applied",
                              "note": "Read the document."} for p in RULES["perspectives"]],
        }
        findings.merge(record, [self.fragment(data)])
        result = detect.scan_snapshot(self.out, RULES, [])
        self.assertEqual(result["summary"]["open"], 0)
        for name in ("detect.before.json", "detect.after.json"):
            common.write_json(self.out / name, result)
        common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
        findings.render(self.out)
        self.assertEqual(contract_check.problems(self.out), [
            "perspective STR-14 is N/A but detect.py cues it at guide.md:8",
        ])

        findings.merge(record, [self.fragment({"perspectives": [
            {"id": "STR-14", "result": "applied", "note": "Question heading checked; retained for navigation."},
        ]})])
        findings.render(self.out)
        self.assertEqual(contract_check.problems(self.out), [])


if __name__ == "__main__":
    unittest.main()
