"""Inline destinations stay protected when a quoted paragraph wraps."""
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


class QuotedInlineLinkTests(unittest.TestCase):
    def assert_target_change(self, source, target="docs/old.md"):
        before = preserve_check.facts(source)
        changed = target.replace("old", "new")
        after = preserve_check.facts(source.replace(target, changed))
        self.assertEqual(before["url"], {target: 1})
        self.assertEqual({(diff["kind"], diff["change"], diff["value"])
                          for diff in preserve_check.compare(before, after, source)},
                         {("url", "lost", target), ("url", "added", changed)})

    def test_destination_can_follow_the_opening_parenthesis_in_a_quote(self):
        for newline in ("\n", "\r\n"):
            for first, continuation in (("> ", "> "), ("> > ", "> > "),
                                        ("- > ", "  > "), ("> - ", ">   "),
                                        ("10. > ", "\t> ")):
                for target in ("docs/old.md", "<docs/old.md>"):
                    source = f"{first}Read [guide]({newline}{continuation}{target}).{newline}"
                    with self.subTest(source=source):
                        self.assert_target_change(source)

    def test_wrapped_titles_and_closing_parentheses_preserve_the_target(self):
        for newline in ("\n", "\r\n"):
            for title in ('"Edition 2"', "'Edition 2'", "(Edition 2)"):
                for body in (
                    f"[guide](docs/old.md{newline}> {title})",
                    f"[guide](<docs/old.md>{newline}> {title})",
                    f"[guide](docs/old.md {title}{newline}> )",
                    f"[guide](docs/old.md{newline}> {title}{newline}> )",
                ):
                    source = f"> {body}. Read `command` in 2026.{newline}"
                    with self.subTest(source=source):
                        self.assert_target_change(source)
                        facts = preserve_check.facts(source)
                        self.assertEqual(facts["number"], {"2": 1, "2026": 1})
                        self.assertEqual(facts["inline_code"], {"command": 1})

    def test_wrapped_destinations_preserve_literal_and_escaped_delimiters(self):
        for target in ("docs/a(b(c))/old.md", r"docs/a\)b/old.md",
                       "docs/old file.md", r"docs/a\>b/old.md", "docs/a>b/old.md"):
            angle = f"<{target}>" if " " in target or r"\>" in target else target
            source = f"> Read [guide](\n> {angle}\n> " + '"Edition 2").\n'
            with self.subTest(target=target):
                self.assert_target_change(source, target)
                self.assertEqual(preserve_check.facts(source)["number"], {"2": 1})

    def test_lazy_continuations_keep_the_same_quote_context(self):
        for source in (
            "> Read [guide](\ndocs/old.md).\n",
            "> > Read [guide](\n> docs/old.md).\n",
            "> Read this\n[guide](\n> docs/old.md).\n",
        ):
            with self.subTest(source=source):
                self.assert_target_change(source)

    def test_a_masked_fence_keeps_the_container_for_the_following_link(self):
        source = "- - ```\n    sample\n    ```\n\n    > [guide](\n    > docs/old.md).\n"
        self.assert_target_change(source)

    def test_quote_prefixes_cannot_join_links_across_block_boundaries(self):
        for source in (
            "> [guide](\n>\n> docs/old.md)\n",
            "> [guide](\n> > docs/old.md)\n",
            '> [guide](docs/old.md "Title\n>\n> ends")\n',
            '> [guide](docs/old.md "Title\n> # Heading\n> ends")\n',
            '> [guide](docs/old.md "Title\n> - new item\n> ends")\n',
        ):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["url"], {})

    def test_link_syntax_inside_quoted_code_stays_code(self):
        for source in (
            "> Run `[guide](docs/old.md)`.\n",
            "> ```\n> [guide](\n> docs/old.md)\n> ```\n",
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(sum(facts["inline_code"].values()) + sum(facts["code_block"].values()), 1)

    def test_destination_backticks_do_not_consume_following_prose_or_code(self):
        rules = common.load_rules()
        compiled = detect.compile_rules(rules)
        for source in (
            "> [guide](\n> docs/`literal) I hope this helps. `command`.\n",
            '> [guide](docs/`literal\n> "Edition 2") I hope this helps. `command`.\n',
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {"docs/`literal": 1})
                self.assertEqual(facts["inline_code"], {"command": 1})
                hits = detect.scan_text(source, compiled, rules["min_chars"])[2]
                artifact = [hit for hit in hits if hit["rule"] == "ART-03"]
                self.assertEqual(len(artifact), 1)
                hit = artifact[0]
                self.assertEqual(source.splitlines()[hit["line"] - 1][hit["col"] - 1:],
                                 "I hope this helps. `command`.")


class QuotedInlineLinkContractTests(RunFixture):
    def test_changed_quoted_destination_fails_even_with_a_fresh_report(self):
        source = "> Read [guide](\n> docs/old.md).\n"
        (self.docs / "guide.md").write_text(source, encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text(
            source.replace("old.md", "new.md"), encoding="utf-8")
        rules = common.load_rules()
        common.write_json(self.out / "detect.after.json", detect.scan_snapshot(self.out, rules, []))
        result = preserve_check.check(self.out)
        common.write_json(self.out / "preserve.json", result)
        findings.render(self.out)
        self.assertEqual(result["unacknowledged"], 2)
        problems = contract_check.problems(self.out)
        self.assertTrue(any("lost url 'docs/old.md'" in problem for problem in problems), problems)
        self.assertTrue(any("added url 'docs/new.md'" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
