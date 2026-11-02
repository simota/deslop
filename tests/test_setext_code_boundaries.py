"""Setext headings end paragraphs before indented code and later references."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"))

import common
import contract_check
import detect
import findings
import preserve_check
from test_run_validation import RunFixture


def document(first="", continuation="", underline="===", newline="\n"):
    return newline.join((f"{first}Title", f"{continuation}{underline}",
                         f"{continuation}    echo stable", f"{continuation}[ref]: docs/old.md", ""))


class SetextCodeBoundaryTests(unittest.TestCase):
    def test_indented_code_after_setext_keeps_following_reference_visible(self):
        for first, continuation in (("", ""), ("> ", "> "), ("- ", "  "), ("> - ", ">   ")):
            for underline in ("===", "-", "--"):
                for newline in ("\n", "\r\n"):
                    source = document(first, continuation, underline, newline)
                    with self.subTest(source=source):
                        self.assertEqual(len(common.code_blocks(source)), 1)
                        before = preserve_check.facts(source)
                        self.assertEqual(sum(before["code_block"].values()), 1)
                        self.assertEqual(before["url"], {"docs/old.md": 1})
                        after = preserve_check.facts(source.replace("old.md", "new.md"))
                        self.assertEqual({(d["kind"], d["change"], d["value"])
                                          for d in preserve_check.compare(before, after, source)},
                                         {("url", "lost", "docs/old.md"), ("url", "added", "docs/new.md")})

    def test_code_artifacts_after_setext_are_masked(self):
        source = "Title\n===\n    I hope this helps\n    [fake]: docs/fake.md\n[ref]: docs/old.md\n"
        self.assertNotIn("I hope this helps", detect.mask_code(source))
        self.assertEqual(preserve_check.facts(source)["url"], {"docs/old.md": 1})

    def test_invalid_underlines_keep_indented_paragraph_text_visible(self):
        for underline in ("= =", "==-", "    ===", r"\==="):
            source = f"Title\n{underline}\n    I hope this helps\n[label]: `literal`\n"
            with self.subTest(underline=underline):
                self.assertEqual(common.code_blocks(source), [])
                self.assertIn("I hope this helps", detect.mask_code(source))
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"literal": 1})

    def test_lazy_underlines_keep_later_indented_text_in_the_paragraph(self):
        for source in (
            "> Title\n===\n>     I hope this helps\n> [label]: `literal`\n",
            "- Title\n ===\n      I hope this helps\n  [label]: `literal`\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(common.code_blocks(source), [])
                self.assertIn("I hope this helps", detect.mask_code(source))
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"literal": 1})


class SetextCodeContractTests(RunFixture):
    def test_changed_reference_after_heading_and_code_fails_contract(self):
        for index, (first, continuation) in enumerate((("", ""), ("> ", "> "), ("- ", "  "))):
            with self.subTest(first=first):
                source = document(first, continuation)
                self.out = self.base / f"run-{index}"
                (self.docs / "guide.md").write_text(source, encoding="utf-8")
                self.make_run()
                (self.out / "rewritten/guide.md").write_text(source.replace("old.md", "new.md"), encoding="utf-8")
                common.write_json(self.out / "detect.after.json", detect.scan_snapshot(self.out, common.load_rules(), []))
                common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
                findings.render(self.out)
                self.assertEqual(preserve_check.check(self.out)["unacknowledged"], 2)
                problems = contract_check.problems(self.out)
                self.assertEqual(sum("not acknowledged in preservation" in p for p in problems), 2, problems)


if __name__ == "__main__":
    unittest.main()
