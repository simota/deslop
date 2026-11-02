"""A fact that changes identity is reported even when a similar value survives."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import preserve_check  # noqa: E402
import common  # noqa: E402
import contract_check  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
from test_run_validation import RunFixture  # noqa: E402


def diff(before, after):
    return {(d["change"], d["kind"], d["value"], d.get("role"))
            for d in preserve_check.compare(preserve_check.facts(before), preserve_check.facts(after), before)}


class FootnoteTests(unittest.TestCase):
    def test_removing_a_reference_is_reported_while_its_definition_stays(self):
        self.assertEqual(diff("Claim.[^1]\n\n[^1]: Source.\n", "Claim.\n\n[^1]: Source.\n"),
                         {("lost", "footnote", "[^1]", None)})

    def test_removing_a_definition_is_reported_while_its_reference_stays(self):
        self.assertEqual(diff("Claim.[^1]\n\n[^1]: Source.\n", "Claim.[^1]\n"),
                         {("lost", "footnote", "[^1]", "definition")})

    def test_one_entry_acknowledges_a_footnote_removed_whole(self):
        found = diff("Claim.[^1]\n\n[^1]: Source.\n", "Claim.\n")
        self.assertEqual({(change, kind, value) for change, kind, value, _ in found},
                         {("lost", "footnote", "[^1]")})

    def test_moving_a_reference_is_not_a_change(self):
        self.assertEqual(diff("A.[^1] B.\n\n[^1]: S.\n", "A. B.[^1]\n\n[^1]: S.\n"), set())


class AddedValueTests(unittest.TestCase):
    def test_shorter_url_than_the_original_is_added(self):
        self.assertEqual(diff("See https://example.com/docs/v2 now.\n", "See https://example.com/docs now.\n"),
                         {("lost", "url", "https://example.com/docs/v2", None),
                          ("added", "url", "https://example.com/docs", None)})

    def test_url_from_the_originals_code_may_be_restated(self):
        before = "Run:\n\n```\ncurl https://example.com/api\n```\n"
        after = before + "\nThe endpoint is https://example.com/api.\n"
        self.assertEqual(diff(before, after), set())

    def test_url_quoted_in_the_originals_code_may_be_restated(self):
        for quote in ("'", '"'):
            before = f"Run:\n\n```\ncurl {quote}https://example.com/api{quote}\n```\n"
            self.assertEqual(diff(before, before + "\nThe endpoint is https://example.com/api.\n"), set(), quote)

    def test_url_only_inside_a_longer_code_url_is_added(self):
        before = "Run:\n\n```\ncurl https://example.com/api/v2\n```\n"
        after = before + "\nSee https://example.com/api.\n"
        self.assertEqual(diff(before, after), {("added", "url", "https://example.com/api", None)})

    def test_footnote_text_inside_prose_is_not_a_reference_already_present(self):
        self.assertEqual(diff("Use [^1] syntax? No.\n", "Use [^1] syntax? No.[^12]\n"),
                         {("added", "footnote", "[^12]", None)})


    def test_host_of_a_code_url_with_a_port_is_added(self):
        before = "Run:\n\n```\ncurl https://example.com:8080/v1\n```\n"
        self.assertEqual(diff(before, before + "\nSee https://example.com.\n"),
                         {("added", "url", "https://example.com", None)})

    def test_url_or_path_the_original_states_in_prose_may_become_a_link(self):
        self.assertEqual(diff("Use `https://example.com/api` as base.\n",
                              "Use `https://example.com/api` or https://example.com/api.\n"), set())
        self.assertEqual(diff("Edit docs/setup.md first.\n", "Edit [setup](docs/setup.md) first.\n"), set())
        self.assertEqual(diff("Edit docs/setup.md.bak first.\n", "Edit [setup](docs/setup.md) first.\n"),
                         {("added", "url", "docs/setup.md", None)})


class NumberTests(unittest.TestCase):
    def test_superscript_digits_are_not_plain_digits(self):
        self.assertEqual(diff("Area is 10² m.\n", "Area is 102 m.\n"),
                         {("lost", "number", "10", None), ("lost", "number", "2", None),
                          ("added", "number", "102", None)})
        self.assertEqual(diff("Area is 10² m.\n", "Area is 10³ m.\n"),
                         {("lost", "number", "2", None), ("added", "number", "3", None)})

    def test_full_width_digits_still_fold(self):
        self.assertEqual(diff("上限は１０件。\n", "上限は10件。\n"), set())
        self.assertEqual(diff("差は−5。\n", "差は-5。\n"), set())

    def test_superscript_sign_stays_with_its_exponent(self):
        self.assertIn("-3", preserve_check.facts("Use 10⁻³ s.\n")["number"])

    def test_script_transitions_separate_adjacent_numbers(self):
        for source, expected in (
                ("10²3", {"10": 1, "2": 1, "3": 1}),
                ("10₂3", {"10": 1, "2": 1, "3": 1}),
                ("SO₄²⁻", {"4": 1, "2": 1}),
                ("x²₃", {"2": 1, "3": 1}),
                ("10⁻³2", {"10": 1, "-3": 1, "2": 1})):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["number"], expected)

    def test_baseline_text_does_not_extend_a_raised_number(self):
        for source, expected in (("10³.5", {"10": 1, "3": 1, ".5": 1}),
                                 ("10³e5", {"10": 1, "3": 1, "5": 1})):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["number"], expected)

    def test_same_script_digits_and_signs_stay_together(self):
        for source, expected in (("10⁻³²", {"10": 1, "-32": 1}),
                                 ("x₋₁₂", {"-12": 1}),
                                 ("10⁺³", {"10": 1, "+3": 1}),
                                 ("SO₄₂⁻", {"42": 1})):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["number"], expected)

    def test_moving_digits_between_scripts_is_reported(self):
        self.assertEqual(diff("The ion is SO₄²⁻.\n", "The ion is SO₄₂⁻.\n"),
                         {("lost", "number", "4", None), ("lost", "number", "2", None),
                          ("added", "number", "42", None)})
        self.assertEqual(diff("Value: 10²3.\n", "Value: 10²³.\n"),
                         {("lost", "number", "2", None), ("lost", "number", "3", None),
                          ("added", "number", "23", None)})


class NumberScriptContractTests(RunFixture):
    def test_fresh_report_cannot_hide_a_script_transition(self):
        (self.docs / "guide.md").write_text("The ion is SO₄²⁻.\n", encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text("The ion is SO₄₂⁻.\n", encoding="utf-8")
        common.write_json(self.out / "detect.after.json",
                          detect.scan_snapshot(self.out, common.load_rules(), []))
        common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
        findings.render(self.out)
        self.assertEqual(set(contract_check.problems(self.out)), {
            "guide.md: lost number '2' not acknowledged in preservation",
            "guide.md: lost number '4' not acknowledged in preservation",
            "guide.md: added number '42' not acknowledged in preservation",
        })


if __name__ == "__main__":
    unittest.main()
