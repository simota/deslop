"""Markdown destinations survive intact without swallowing prose or titles."""
import sys
import tracemalloc
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"))

import preserve_check  # noqa: E402


class LinkDestinationBoundaryTests(unittest.TestCase):
    def test_nested_destination_is_kept_whole_and_changes_are_reported(self):
        for depth in (1, 2, 12):
            target = "docs/" + "a(" * depth + "section" + ")" * depth + "/old.md"
            changed = target.replace("old.md", "new.md")
            before = f"Read [guide]({target}).\n"
            after = f"Read [guide]({changed}).\n"
            with self.subTest(depth=depth):
                self.assertEqual(preserve_check.facts(before)["url"], {target: 1})
                diffs = preserve_check.compare(preserve_check.facts(before),
                                               preserve_check.facts(after), before)
                self.assertEqual({(d["kind"], d["change"], d["value"]) for d in diffs},
                                 {("url", "lost", target), ("url", "added", changed)})

    def test_inline_and_reference_forms_agree_for_nested_and_escaped_targets(self):
        for target in ("docs/a(b(c))/guide.md", r"docs/a\)b/guide.md",
                       r"docs/a\(b\)/guide.md", r"docs/a\\(b)/guide.md"):
            with self.subTest(target=target):
                inline = f"Read [guide]({target}).\n"
                reference = f"Read [guide][ref].\n\n[ref]: {target}\n"
                self.assertEqual(preserve_check.facts(inline)["url"], {target: 1})
                self.assertEqual(preserve_check.facts(inline)["url"],
                                 preserve_check.facts(reference)["url"])

    def test_titles_and_following_prose_keep_their_numbers(self):
        for title in ('"Revenue 100"', "'Revenue 100'", "(Revenue 100)",
                      r'"Revenue \"100\""'):
            with self.subTest(title=title):
                source = f"Read [guide](docs/a(b(c))/guide.md {title}). Limit 200.\n"
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {"docs/a(b(c))/guide.md": 1})
                self.assertEqual(facts["number"], {"100": 1, "200": 1})

    def test_angle_destinations_keep_spaces_and_escaped_closing_delimiters(self):
        for target in ("docs/a b(c).md", r"docs/a\>b.md"):
            with self.subTest(target=target):
                source = f"[guide](<{target}> \"Edition 2\")\n"
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {target: 1})
                self.assertEqual(facts["number"], {"2": 1})

    def test_autolinks_keep_literal_link_syntax_and_report_tail_changes(self):
        target = "https://example.com/[part](ignored)/old"
        changed = target.replace("/old", "/new")
        for source in (f"<{target}>\n", f"Read <{target}>.\n",
                       f"\\<{target}>\n",
                       f'[guide](<{target}> "Edition 2")\n',
                       f'[guide]({target} "Edition 2")\n'):
            with self.subTest(source=source):
                before = preserve_check.facts(source)
                after = preserve_check.facts(source.replace(target, changed))
                self.assertEqual(before["url"], {target: 1})
                diffs = preserve_check.compare(before, after, source)
                self.assertEqual({(d["kind"], d["change"], d["value"]) for d in diffs},
                                 {("url", "lost", target), ("url", "added", changed)})
                if "Edition 2" in source:
                    self.assertEqual(before["number"], {"2": 1})

    def test_absolute_angle_destination_retains_escaped_delimiters(self):
        target = r"https://example.com/a\>b/[part](ignored)/guide.md"
        source = f'[guide](<{target}> "Edition 2")\n'
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {target: 1})
        self.assertEqual(facts["number"], {"2": 1})

    def test_backticks_in_destinations_are_url_content(self):
        for target in ("https://example.com/`part`/old", "docs/`part`/old"):
            sources = (f"[guide]({target})\n", f"[guide](<{target}>)\n",
                       f"[guide][ref]\n\n[ref]: {target}\n",
                       f"[guide][ref]\n\n[ref]: <{target}>\n")
            if target.startswith("https:"):
                sources += (f"<{target}>\n",)
            for source in sources:
                with self.subTest(source=source):
                    before = preserve_check.facts(source)
                    after = preserve_check.facts(source.replace("/old", "/new"))
                    self.assertEqual(before["url"], {target: 1})
                    self.assertEqual(before["inline_code"], {})
                    diffs = preserve_check.compare(before, after, source)
                    self.assertEqual({(d["kind"], d["change"], d["value"]) for d in diffs},
                                     {("url", "lost", target),
                                      ("url", "added", target.replace("/old", "/new"))})

    def test_code_spans_keep_link_and_autolink_literals_as_code(self):
        for content, delimiter in (("<https://example.com/old>", "`"),
                                   ("[guide](docs/old.md)", "`"),
                                   ("<https://example.com/`part`/old>", "``")):
            with self.subTest(content=content):
                facts = preserve_check.facts(f"Run {delimiter}{content}{delimiter}.\n")
                self.assertEqual(facts["inline_code"], {content: 1})
                self.assertEqual(facts["url"], {})

    def test_link_labels_keep_their_code_spans(self):
        for content in ("guide", "](literal)!"):
            source = f'[`{content}`](docs/guide.md "Edition 2")\n'
            with self.subTest(content=content):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["inline_code"], {content: 1})
                self.assertEqual(facts["url"], {"docs/guide.md": 1})
                self.assertEqual(facts["number"], {"2": 1})

    def test_link_titles_keep_literal_backticks_and_numbers(self):
        for source in ('[guide](docs/guide.md "Edition `2`").\n',
                       '[guide][ref]\n\n[ref]: docs/guide.md "Edition `2`"\n'):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["inline_code"], {})
                self.assertEqual(facts["url"], {"docs/guide.md": 1})
                self.assertEqual(facts["number"], {"2": 1})

    def test_backticks_in_urls_or_titles_do_not_consume_later_code(self):
        for prefix, target, numbers in (
                ("<https://example.com/`literal>", "https://example.com/`literal", {}),
                ('[guide](docs/guide.md "Edition `2")', "docs/guide.md", {"2": 1})):
            source = prefix + " and `[fake](code.md)`.\n"
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {target: 1})
                self.assertEqual(facts["inline_code"], {"[fake](code.md)": 1})
                self.assertEqual(facts["number"], numbers)

    def test_code_that_starts_before_an_autolink_takes_precedence(self):
        source = "`<https://example.com/`part>`\n"
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {})
        self.assertEqual(facts["inline_code"], {"<https://example.com/": 1})

    def test_whitespace_around_a_destination_does_not_hide_it(self):
        source = "[guide](\n docs/a(b(c))/guide.md\n 'Edition 2' )\n"
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {"docs/a(b(c))/guide.md": 1})
        self.assertEqual(facts["number"], {"2": 1})

    def test_incomplete_or_escaped_links_are_not_destinations(self):
        for source in ("[guide](docs/a(b(c))/guide.md\n",
                       "[guide](docs/a(b(c)/guide.md)\n",
                       "[guide](docs/guide.md arbitrary 300)\n",
                       '[guide](docs/guide.md "Title 300)\n',
                       r"\[guide](docs/guide.md)",
                       "guide](docs/guide.md)\n"):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["url"], {})
                if "300" in source:
                    self.assertEqual(preserve_check.facts(source)["number"], {"300": 1})

    def test_many_unclosed_destinations_stay_literal(self):
        self.assertEqual(list(preserve_check.protected_inline_spans("[guide](" * 8000)), [])

    def test_overlapping_code_candidates_do_not_copy_every_candidate_body(self):
        for count in (200, 400):
            runs = ["`" * width for width in range(1, count + 1)]
            source = " ".join(runs + runs)
            with self.subTest(count=count):
                tracemalloc.start()
                try:
                    spans = list(preserve_check.protected_inline_spans(source))
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
                self.assertEqual([span[0] for span in spans], ["inline_code"])
                self.assertLess(peak, 20 * len(source))


if __name__ == "__main__":
    unittest.main()
