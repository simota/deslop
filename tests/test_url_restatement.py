"""Restating a complete URL must not authorize one of its substrings."""
from pathlib import Path
import subprocess
import sys
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check


class UrlRestatementTests(unittest.TestCase):
    def restatement_diffs(self, original, target):
        after = original + f"\nRead [guide](<{target}>).\n"
        return preserve_check.compare(preserve_check.facts(original),
                                      preserve_check.facts(after), original)

    def assert_added(self, original, target):
        self.assertEqual(self.restatement_diffs(original, target),
                         [{"kind": "url", "change": "added", "value": target, "count": 1}])

    def test_absolute_url_prefixes_are_new_values(self):
        for suffix in ("/guide", ".evil/guide", "?tenant=private", "#private"):
            source = f"See https://example.com{suffix}.\n"
            with self.subTest(source=source):
                self.assert_added(source, "https://example.com")

    def test_relative_path_prefixes_and_suffixes_are_new_values(self):
        for source, target in (
            ("See docs/internal/guide.md.\n", "guide.md"),
            ("See docs/guide.md.old.\n", "docs/guide.md"),
            ("See internal/docs/guide.md.\n", "docs/guide.md"),
        ):
            with self.subTest(source=source, target=target):
                self.assert_added(source, target)

    def test_url_fragments_inside_code_are_new_values(self):
        for source in (
            "Use `https://example.com/guide`.\n",
            '```sh\ncurl "https://example.com/guide"\n```\n',
        ):
            with self.subTest(source=source):
                self.assert_added(source, "https://example.com")
        self.assert_added("Use `docs/release.`.\n", "docs/release")

    def test_complete_values_in_code_can_be_restated(self):
        for target in ("https://example.com/guide", "docs/guide.md", "docs/a b.md"):
            for source in (f"Use `{target}`.\n", f'```sh\nopen "{target}"\n```\n'):
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, target), [])

    def test_complete_plain_relative_paths_can_be_restated(self):
        for source in (
            "See docs/guide.md\n",
            "See docs/guide.md.\n",
            "See docs/guide.md, then continue.\n",
            "See (docs/guide.md).\n",
            'The file is "docs/guide.md".\n',
            "The file is 'docs/guide.md'.\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])

    def test_repeating_an_existing_url_does_not_change_facts(self):
        for source, target in (
            ("See https://example.com/guide.\n", "https://example.com/guide"),
            ("Read [guide](docs/guide.md).\n", "docs/guide.md"),
            ("[guide]: docs/guide.md\n", "docs/guide.md"),
        ):
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, target), [])

    def test_explicit_destination_punctuation_is_part_of_the_value(self):
        for suffix in (".", ",", ";", ":"):
            for target in ("docs/release", "https://example.com/release"):
                full = target + suffix
                sources = (f"Read [guide]({full}).\n", f"Read [guide](<{full}>).\n",
                           f"[guide]: {full}\n", f"[guide]: <{full}>\n")
                if target.startswith("https:"):
                    sources += (f"<{full}>\n",)
                for source in sources:
                    with self.subTest(source=source):
                        self.assert_added(source, target)

    def test_an_independent_complete_occurrence_still_allows_restatement(self):
        for source, target in (
            ("See https://example.com/guide.\nUse `https://example.com`.\n",
             "https://example.com"),
            ("Read [guide](internal/docs/guide.md).\nThe file is docs/guide.md.\n",
             "docs/guide.md"),
            ("Read [guide](docs/release.).\nThe file is docs/release.\n", "docs/release"),
        ):
            with self.subTest(source=source, target=target):
                self.assertEqual(self.restatement_diffs(source, target), [])

    def test_protected_spans_cannot_create_independent_literal_tokens(self):
        for source in (
            "Read docs/guide.md`literal`.\n",
            "Read `literal`docs/guide.md.\n",
            "Read prefixhttps://example.com/guide.\n",
        ):
            target = "prefix" if "prefix" in source else "docs/guide.md"
            with self.subTest(source=source):
                self.assert_added(source, target)

    def test_deep_outer_punctuation_keeps_the_complete_literal(self):
        source = "Read " + "(" * 4000 + "docs/guide.md" + ")" * 4000 + ".\n"
        self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])

    def test_complete_quoted_prose_values_can_be_restated(self):
        for opening, closing in (("\"", "\""), ("'", "'"), ("“", "”"),
                                 ("‘", "’"), ("「", "」"), ("『", "』")):
            for target in ("docs/guide.md", "docs/a b.md", "https://example.com/guide"):
                source = f"Read {opening}{target}{closing}.\n"
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, target), [])

    def test_complete_emphasized_prose_values_can_be_restated(self):
        for marker in ("*", "**", "***", "_", "__"):
            for target in ("docs/guide.md", "https://example.com/guide"):
                source = f"Read {marker}{target}{marker}.\n"
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, target), [])

    def test_quoted_values_in_japanese_sentences_can_be_restated(self):
        for opening, closing in (("「", "」"), ("『", "』"), ("“", "”")):
            for target in ("docs/guide.md", "docs/a b.md", "https://example.com/guide"):
                for template in ("{}。\n", "参照先は{}です。\n"):
                    source = template.format(opening + target + closing)
                    with self.subTest(source=source):
                        self.assertEqual(self.restatement_diffs(source, target), [])
                        self.assert_added(source, "guide.md")

    def test_emphasis_inside_prose_quotes_keeps_a_complete_value(self):
        for target in ("docs/guide.md", "https://example.com/guide", "docs/release.",
                       "https://example.com/guide)"):
            for marker in ("**", "_"):
                source = f"Read “{marker}{target}{marker}”.\n"
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, target), [])

    def test_quotes_inside_a_url_do_not_create_independent_literals(self):
        for opening, closing in (("「", "」"), ("“", "”"), ('"', '"')):
            source = f"Read https://example.com/{opening}docs/guide.md{closing}.\n"
            with self.subTest(source=source):
                self.assert_added(source, "docs/guide.md")

    def test_prose_quotes_after_code_or_another_quote_have_their_own_boundaries(self):
        for prefix in ('URLは`https://example.com`、',
                       'URLは「https://example.com」、',
                       'URLは"https://example.com"、',
                       'URLは[home](https://example.com)、'):
            source = prefix + '参照先は「docs/guide.md」です。\n'
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])
                self.assert_added(source, "guide.md")
        source = 'URLは「https://example.com」、https://example.com/「docs/guide.md」。\n'
        self.assert_added(source, "docs/guide.md")

    def test_emphasis_has_its_own_prose_boundaries(self):
        for marker in ("*", "**", "***", "_", "__", "___"):
            source = f"Read {marker}https://example.com/my_file{marker}、参照先は「docs/guide.md」です。\n"
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])
                self.assert_added(source, "guide.md")
        for marker in ("*", "**", "***"):
            source = f"参照先は{marker}docs/guide.md{marker}です。\n"
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])
                self.assert_added(source, "guide.md")

    def test_emphasis_inside_a_url_does_not_create_independent_literals(self):
        for marker in ("*", "**", "_", "__"):
            source = f"Read https://example.com/{marker}docs/guide.md{marker}.\n"
            with self.subTest(source=source):
                self.assert_added(source, "docs/guide.md")

    def test_quoted_literals_inside_emphasized_sentences_can_be_restated(self):
        for marker in ("*", "**", "***", "_", "__", "___"):
            source = f"{marker}参照先は「docs/guide.md」です。{marker}\n"
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])
                self.assert_added(source, "guide.md")
        for source in ('**Read *the 「docs/guide.md」 file* again.**\n',
                       '**Read `https://example.com`、参照先は「docs/guide.md」です。**\n'):
            with self.subTest(source=source):
                self.assertEqual(self.restatement_diffs(source, "docs/guide.md"), [])

    def test_quotes_inside_emphasized_urls_do_not_create_independent_values(self):
        for marker in ("*", "**", "***", "_", "__", "___"):
            source = f"{marker}Read https://example.com/「docs/guide.md」 now.{marker}\n"
            with self.subTest(source=source):
                self.assert_added(source, "docs/guide.md")

    def test_prose_wrappers_do_not_authorize_url_fragments(self):
        for opening, closing in (("\"", "\""), ("“", "”"), ("「", "」"),
                                 ("**", "**"), ("_", "_")):
            for full, target in (("docs/guide.md.old", "docs/guide.md"),
                                 ("internal/docs/guide.md", "docs/guide.md"),
                                 ("https://example.com/guide", "https://example.com"),
                                 ("https://example.com?tenant=private", "https://example.com")):
                source = f"Read {opening}{full}{closing}.\n"
                with self.subTest(source=source, target=target):
                    self.assert_added(source, target)

    def test_quoted_code_values_keep_their_inner_delimiters(self):
        target = "docs/guide.md"
        for opening, closing in (("(", ")"), ("[", "]"), ("'", "'"),
                                 ("*", "*"), ("_", "_")):
            full = opening + target + closing
            for source in (f'```sh\nopen "{full}"\n```\n', f'Use `open "{full}"`.\n'):
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, full), [])
                    self.assert_added(source, target)
        self.assert_added('```sh\nopen "<docs/guide.md>"\n```\n', target)

    def test_emphasis_markers_in_code_are_literal(self):
        for marker in ("*", "**", "_", "__"):
            full = marker + "docs/guide.md" + marker
            for source in (f"Use `{full}`.\n", f"```sh\nopen {full}\n```\n"):
                with self.subTest(source=source):
                    self.assertEqual(self.restatement_diffs(source, full), [])
                    self.assert_added(source, "docs/guide.md")

    def test_sentence_punctuation_cannot_be_added_to_a_bare_url(self):
        for punctuation in (".", ",", ";", ":"):
            full = "https://example.com/guide" + punctuation
            with self.subTest(punctuation=punctuation):
                self.assert_added(f"See {full}\n", full)

    def test_prose_closing_delimiters_cannot_be_added_to_a_bare_url(self):
        for opening, closing in (("(", ")"), ("[", "]")):
            for source in (f"For details {opening}see https://example.com/guide{closing}.\n",
                           f"Read *https://example.com/guide{closing}*.\n"):
                with self.subTest(source=source):
                    self.assert_added(source, "https://example.com/guide" + closing)

    def test_unclosed_prose_quotes_do_not_hide_new_values(self):
        source = "「word " * 4000 + "\n"
        self.assert_added(source, "docs/new.md")

    def test_unclosed_underscore_emphasis_has_a_bounded_running_time(self):
        # A few hundred characters previously triggered exponential backtracking.
        # Isolate the case so a regression fails instead of hanging the whole suite.
        script = '''
import preserve_check as p
original = "__" + "a_" * 128 + "z\\n"
after = original + "\\nRead [guide](docs/new.md).\\n"
diffs = p.compare(p.facts(original), p.facts(after), original)
assert diffs == [{"kind": "url", "change": "added", "value": "docs/new.md", "count": 1}], diffs
'''
        try:
            result = subprocess.run([sys.executable, "-c", script],
                                    cwd=Path(preserve_check.__file__).parent,
                                    capture_output=True, text=True, timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("A short unclosed emphasis value exceeded the five-second safety budget")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_escaped_or_concatenated_quotes_cannot_create_code_literals(self):
        for command, target in (
            ('open "a\\\" \'docs/b\' c"', "docs/b"),
            ('open "docs/""guide.md"', 'docs/""guide.md'),
            ('url="a \'docs/b\' c"', "docs/b"),
            ('open "a\n \'docs/b\' c"', "docs/b"),
        ):
            source = f"```sh\n{command}\n```\n"
            with self.subTest(source=source):
                self.assert_added(source, target)


class UrlRestatementContractTests(RunFixture):
    def test_quoted_code_restatement_checks_the_complete_literal_with_a_fresh_report(self):
        source = '```sh\nopen "(docs/guide.md)"\n```\n'
        (self.docs / "guide.md").write_text(source, encoding="utf-8")
        self.make_run()
        for target, unacknowledged in (("(docs/guide.md)", 0), ("docs/guide.md", 1)):
            with self.subTest(target=target):
                (self.out / "rewritten" / "guide.md").write_text(
                    source + f"\nRead [guide](<{target}>).\n", encoding="utf-8")
                common.write_json(self.out / "detect.after.json",
                                  detect.scan_snapshot(self.out, common.load_rules(), []))
                result = preserve_check.check(self.out)
                common.write_json(self.out / "preserve.json", result)
                findings.render(self.out)
                self.assertEqual(result["unacknowledged"], unacknowledged)
                problems = contract_check.problems(self.out)
                if unacknowledged:
                    self.assertTrue(any("added url 'docs/guide.md'" in problem for problem in problems),
                                    problems)
                else:
                    self.assertEqual(problems, [])

    def test_adding_a_url_prefix_fails_even_with_a_fresh_report(self):
        source = "See https://example.com/guide.\n"
        (self.docs / "guide.md").write_text(source, encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text(
            source + "\nRead [home](https://example.com).\n", encoding="utf-8")
        common.write_json(self.out / "detect.after.json",
                          detect.scan_snapshot(self.out, common.load_rules(), []))
        result = preserve_check.check(self.out)
        common.write_json(self.out / "preserve.json", result)
        findings.render(self.out)
        self.assertEqual(result["unacknowledged"], 1)
        problems = contract_check.problems(self.out)
        self.assertTrue(any("added url 'https://example.com'" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
