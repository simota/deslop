"""Facts whose punctuation carries meaning must survive the rewrite."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"))

import preserve_check  # noqa: E402


class NumericFactsTests(unittest.TestCase):
    def test_signs_and_leading_decimal_points_are_not_discarded(self):
        for before, after in (("-10", "10"), ("+10", "-10"), (".5", "5"),
                              ("-.5", ".5"), ("1e-3", "1e3")):
            with self.subTest(before=before, after=after):
                original = f"The limit is {before}.\n"
                changed = f"The limit is {after}.\n"
                diffs = preserve_check.compare(preserve_check.facts(original),
                                               preserve_check.facts(changed), original)
                self.assertEqual({(d["change"], d["kind"], d["value"]) for d in diffs},
                                 {("lost", "number", before), ("added", "number", after)})

    def test_full_width_numbers_and_unicode_minus_keep_their_value(self):
        self.assertEqual(preserve_check.facts("温度は－１０度、倍率は．５です。\n")["number"],
                         {"-10": 1, ".5": 1})
        self.assertEqual(preserve_check.facts("Temperature: −10 °C\n")["number"], {"-10": 1})

    def test_date_and_range_separators_are_not_negative_signs(self):
        self.assertEqual(preserve_check.facts("2026-10-31; 10-20 seconds; v2.1.\n")["number"],
                         {"2026": 1, "10": 2, "31": 1, "20": 1, "2.1": 1})


class LinkDestinationTests(unittest.TestCase):
    def test_explicit_destinations_keep_trailing_punctuation(self):
        for suffix in (".", ",", ";", ":"):
            target = "https://example.com/path" + suffix
            for source in (f"[guide]({target})\n", f"[guide](<{target}>)\n",
                           f"[guide]: {target}\n", f"[guide]: <{target}>\n", f"<{target}>\n"):
                with self.subTest(source=source):
                    self.assertEqual(preserve_check.facts(source)["url"], {target: 1})

    def test_removing_punctuation_from_a_relative_target_is_reported(self):
        original = "Read [guide](docs/release.).\n"
        changed = "Read [guide](docs/release).\n"
        diffs = preserve_check.compare(preserve_check.facts(original),
                                       preserve_check.facts(changed), original)
        self.assertIn({"kind": "url", "change": "lost", "value": "docs/release.", "count": 1}, diffs)

    def test_sentence_punctuation_after_a_bare_url_remains_ignored(self):
        self.assertEqual(preserve_check.facts("Read https://example.com/guide.\n")["url"],
                         {"https://example.com/guide": 1})


class InlineCodeFactsTests(unittest.TestCase):
    def test_multiline_code_changes_are_reported_as_code(self):
        original = "Run `read\nsource 300` here.\n"
        changed = "Run `write\nsource 300` here.\n"
        diffs = preserve_check.compare(preserve_check.facts(original),
                                       preserve_check.facts(changed), original)
        self.assertEqual({(d["change"], d["kind"], d["value"]) for d in diffs},
                         {("lost", "inline_code", "read source 300"),
                          ("added", "inline_code", "write source 300")})
        self.assertEqual(preserve_check.facts(original)["number"], {})

    def test_unequal_delimiters_do_not_hide_prose_values(self):
        facts = preserve_check.facts("The literal is `300`` here.\n")
        self.assertEqual(facts["inline_code"], {})
        self.assertEqual(facts["number"], {"300": 1})

    def test_removing_a_span_does_not_join_separate_numbers(self):
        self.assertEqual(preserve_check.facts("1`identifier`2\n")["number"], {"1": 1, "2": 1})


class FencedCodeFactsTests(unittest.TestCase):
    def test_mixed_fence_characters_do_not_close_a_block(self):
        for opener, false_closer in (("```", "```~"), ("~~~", "~~~`")):
            with self.subTest(opener=opener):
                original = f"{opener}\nstart\n{false_closer}\nkeep this\n{opener}\n"
                changed = original.replace("keep this", "changed this")
                diffs = preserve_check.compare(preserve_check.facts(original),
                                               preserve_check.facts(changed), original)
                self.assertEqual({(d["change"], d["kind"]) for d in diffs},
                                 {("lost", "code_block"), ("added", "code_block")})


if __name__ == "__main__":
    unittest.main()
