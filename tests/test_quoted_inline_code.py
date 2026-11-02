"""Quoted paragraphs must preserve and mask their wrapped inline code."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contract_check  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
import preserve_check  # noqa: E402
import snapshot  # noqa: E402
from common import load_rules, write_json  # noqa: E402
from span_helpers import inline_code_spans  # noqa: E402
from test_run_validation import RunFixture

RULES = load_rules()
COMPILED = detect.compile_rules(RULES)


class QuotedInlineCodeTests(unittest.TestCase):
    def test_quote_continuations_preserve_content_and_original_offsets(self):
        for newline in ("\n", "\r\n"):
            for first, continuation in (("> ", "> "), ("> > ", "> > "),
                                        ("> > ", "> "), ("> ", ""),
                                        ("- > ", "  > "), ("> - ", ">   "),
                                        ("10. > ", "    > "), ("10. > ", "\t> "),
                                        (">\t", ">\t")):
                source = first + "Run `old" + newline + continuation + "command`.\n"
                with self.subTest(first=first, continuation=continuation, newline=newline):
                    start = source.index("`")
                    stop = source.index("`", start + 1) + 1
                    indentation = "  " if first == "> - " else ""
                    self.assertEqual(inline_code_spans(source),
                                     [(start, stop, "old" + newline + indentation + "command")])
                    self.assertEqual(preserve_check.facts(source)["inline_code"],
                                     {"old command": 1})

    def test_quote_prefixes_do_not_change_code_when_the_paragraph_is_rewrapped(self):
        for source in ("> Run `old\n> command`.\n", "> > Run `old\n> > command`.\n",
                       "> Run `old\ncommand`.\n", "- > Run `old\n  > command`.\n"):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["inline_code"],
                                 preserve_check.facts("> Run `old command`.\n")["inline_code"])

    def test_an_opener_on_a_lazy_quote_line_keeps_the_quote_context(self):
        for source in ("> Run this\ncommand: `old\n> command`.\n",
                       "10. > Run this\ncommand: `old\n    > command`.\n",
                       "10. > Run this\ncommand: `old\n\t> command`.\n"):
            with self.subTest(source=source):
                spans = inline_code_spans(source)
                self.assertEqual(len(spans), 1)
                self.assertEqual(spans[0][2], "old\ncommand")
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old command": 1})

    def test_a_masked_fence_keeps_the_enclosing_list_for_later_quoted_code(self):
        for fence in ("```", "~~~"):
            prefix = f"- - {fence}\n    sample\n    {fence}\n\n"
            original = prefix + "    > Run `old\n    > command`.\n"
            reflowed = prefix + "    > Run `old command`.\n"
            with self.subTest(fence=fence):
                before, after = preserve_check.facts(original), preserve_check.facts(reflowed)
                self.assertEqual(before["inline_code"], {"old command": 1})
                self.assertEqual(preserve_check.compare(before, after, original), [])

    def test_markers_in_fence_contents_do_not_change_later_quoted_code(self):
        for contents in ("    - > pretend\n", "    > - pretend\n", "    # heading\n"):
            source = "- - ```\n" + contents + "    ```\n\n    > Run `old\n    > command`.\n"
            with self.subTest(contents=contents):
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old command": 1})

    def test_markers_in_fence_contents_do_not_strip_literal_prose_characters(self):
        source = "~~~\n- - > pretend\n~~~\n\nRun `old\n    > command`.\n"
        self.assertEqual(preserve_check.facts(source)["inline_code"], {"old > command": 1})

    def test_html_contents_cannot_strip_literal_characters_from_later_code(self):
        for newline in ("\n", "\r\n"):
            for opening, closing in (("<pre>", "</pre>"), ("<!--", "-->"), ("<?target", "?>"),
                                     ("<!A", ">"), ("<![CDATA[", "]]>"), ("<div>", ""), ("<custom>", "")):
                source = newline.join((opening, "- - > pretend", closing,
                                       "Run `old", "    > command`.", ""))
                with self.subTest(opening=opening, newline=newline):
                    start, stop, content = inline_code_spans(source)[0]
                    self.assertEqual(source[start:stop], "`old" + newline + "    > command`")
                    self.assertEqual(content, "old" + newline + "    > command")
                    before = preserve_check.facts(source)
                    after = preserve_check.facts(source.replace("    > command", "      command"))
                    self.assertEqual(before["inline_code"], {"old > command": 1})
                    self.assertEqual({(d["change"], d["value"]) for d in preserve_check.compare(before, after, source)},
                                     {("lost", "old > command"), ("added", "old command")})

    def test_html_preserves_its_outer_containers_for_later_quoted_code(self):
        for first, continuation in (("> ", "> "), ("- ", "  "), ("- > ", "  > "),
                                    ("> - ", ">   "), ("10. > ", "    > ")):
            source = (first + "<pre>\n" + continuation + "- - > pretend\n"
                      + continuation + "</pre>\n" + continuation + "Run `old\n"
                      + continuation + "    > command`.\n")
            with self.subTest(first=first):
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old > command": 1})

    def test_inline_code_cannot_cross_an_html_block(self):
        for html in ("<pre>literal</pre>", "<!-- note -->", "<?target?>", "<!A>", "<![CDATA[x]]>",
                     "<div>\n\n"):
            for prefix in ("", "> "):
                source = "\n".join(prefix + line for line in
                                   ("Run `old\n" + html + "\nI hope this helps\ncommand`.\n").split("\n"))
                with self.subTest(html=html, prefix=prefix):
                    self.assertEqual(inline_code_spans(source), [])
                    self.assertEqual(preserve_check.facts(source)["inline_code"], {})
                    hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
                    self.assertIn("ART-03", {hit["rule"] for hit in hits})

    def test_html_body_delimiters_cannot_pair_with_the_following_paragraph(self):
        for html in ("<pre>`</pre>", "<!-- ` -->", "<?target ` ?>", "<!A ` >", "<![CDATA[`]]>"):
            source = html + "\nI hope this helps\ncommand`.\n"
            with self.subTest(html=html):
                self.assertEqual(inline_code_spans(source), [])
                hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
                self.assertIn("ART-03", {hit["rule"] for hit in hits})

    def test_html_stops_at_its_outer_container_boundary(self):
        for prefix, continuation in (("> ", "> "), ("- ", "  "), ("- > ", "  > ")):
            source = prefix + "<pre>\n" + continuation + "- - > pretend\nRun `old\n    > command`.\n"
            with self.subTest(prefix=prefix):
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old > command": 1})

    def test_inline_html_does_not_interrupt_inline_code(self):
        for content in ("<span>", "Text <!-- note -->", "Text <pre>literal</pre>", "<ſcript>"):
            source = "Run `old\n" + content + "\ncommand`.\n"
            with self.subTest(content=content):
                self.assertEqual(preserve_check.facts(source)["inline_code"],
                                 {"old " + content + " command": 1})

    def test_html_markers_inside_code_blocks_do_not_hide_later_inline_code(self):
        for prefix in ("```\n<pre>\n```\n", "    <pre>\n"):
            source = prefix + "Run `old\n    > command`.\n"
            with self.subTest(prefix=prefix):
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old > command": 1})

    def test_a_masked_fence_does_not_erase_later_quote_block_boundaries(self):
        for boundary in ("    > # Heading", "    >", "    > - item", "    > > item"):
            source = ("- - ```\n    sample\n    ```\n\n    > Run `old\n"
                      + boundary + "\n    > I hope this helps.\n    > command`.\n")
            with self.subTest(boundary=boundary):
                self.assertEqual(preserve_check.facts(source)["inline_code"], {})
                hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
                self.assertIn("ART-03", {hit["rule"] for hit in hits})

    def test_a_changed_quoted_command_is_a_fact_change(self):
        original = "> Run `old\n> command`.\n"
        after = original.replace("old", "new")
        diffs = preserve_check.compare(preserve_check.facts(original),
                                       preserve_check.facts(after), original)
        self.assertEqual({(d["change"], d["kind"], d["value"]) for d in diffs},
                         {("lost", "inline_code", "old command"),
                          ("added", "inline_code", "new command")})

    def test_quoted_code_is_not_scanned_and_prose_after_it_is_still_scanned(self):
        source = "> Run `old\n> I hope this helps\n> command`.\n\nI hope this helps.\n"
        hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
        self.assertEqual([(h["rule"], h["line"]) for h in hits], [("ART-03", 5)])
        masked = detect.mask_code(source)
        self.assertEqual(len(masked), len(source))
        self.assertEqual([i for i, c in enumerate(masked) if c == "\n"],
                         [i for i, c in enumerate(source) if c == "\n"])

    def test_separate_quote_blocks_do_not_join_unmatched_delimiters(self):
        boundaries = (
            "\n>\n> ", "\n\n> ", "\n> # ", "\n# ", "\n> - ", "\n- ",
            "\n> > ", "\n> ---\n> ", "\n> ===\n> ",
            "\n> ~~~\n> sample\n> ~~~\n> ",
        )
        for boundary in boundaries:
            source = "> Run `old" + boundary + "I hope this helps\n> command`.\n"
            with self.subTest(boundary=boundary):
                self.assertEqual(inline_code_spans(source), [])
                hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
                self.assertIn("ART-03", {h["rule"] for h in hits})

    def test_a_quoted_block_does_not_leak_context_to_the_next_paragraph(self):
        for prefix in ("> Earlier quote.\n\n", "> # Earlier heading\n",
                       "> Earlier quote.\n>\n"):
            source = prefix + "Run `old\n> I hope this helps\n> command`.\n"
            with self.subTest(prefix=prefix):
                self.assertEqual(inline_code_spans(source), [])
                hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
                self.assertIn("ART-03", {h["rule"] for h in hits})

    def test_a_quote_outside_a_list_does_not_continue_the_list_quote(self):
        source = "- > Run `old\n> I hope this helps\n> command`.\n"
        self.assertEqual(inline_code_spans(source), [])
        hits = detect.scan_text(source, COMPILED, RULES["min_chars"])[2]
        self.assertIn("ART-03", {h["rule"] for h in hits})

    def test_literal_greater_than_in_code_content_is_preserved(self):
        for source in ("> Run `old > command`.\n", "> Run `old\n>     > command`.\n"):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["inline_code"],
                                 {"old > command": 1})

    def test_plain_multiline_code_keeps_literal_indented_quote_markers(self):
        for indentation in ("    ", "\t"):
            source = "Run `old\n" + indentation + "> command`.\n"
            with self.subTest(indentation=indentation):
                self.assertEqual(inline_code_spans(source)[0][2], "old\n" + indentation + "> command")
                self.assertEqual(preserve_check.facts(source)["inline_code"], {"old > command": 1})

    def test_contract_rejects_a_changed_quoted_command_with_a_fresh_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs, out = root / "docs", root / "run"
            docs.mkdir()
            source = "> Run `old\n> command`.\n"
            (docs / "guide.md").write_text(source, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(snapshot.main([str(out), str(docs), "--root", str(docs), "--copy"]), 0)
                self.assertEqual(detect.main(["--snapshot", str(out), "--quiet",
                                              "--out", str(out / "detect.before.json")]), 0)
                fragment = root / "fragment.json"
                fragment.write_text(json.dumps({
                    "schema_version": 1,
                    "meta": {"target": str(docs), "lang": "en", "mode": "copy",
                             "assessor": "test", "date": "2026-10-31"},
                    "voice": {"source": "inferred", "rules": ["Keep quoted commands."]},
                    "perspectives": [{"id": p["id"], "result": "applied", "note": "Read in context."}
                                     for p in RULES["perspectives"]],
                }), encoding="utf-8")
                findings.merge(out / "findings.json", [fragment])
                self.assertEqual(detect.main(["--snapshot", str(out), "--quiet",
                                              "--out", str(out / "detect.after.json")]), 0)
                self.assertEqual(preserve_check.main([str(out)]), 0)
                findings.render(out)
                self.assertEqual(contract_check.problems(out), [])
                (out / "rewritten" / "guide.md").write_text(source.replace("old", "new"), encoding="utf-8")
                preserve_check.main([str(out)])
                findings.render(out)
                problems = contract_check.problems(out)
                self.assertTrue(any("lost inline_code 'old command'" in problem for problem in problems), problems)
                self.assertTrue(any("added inline_code 'new command'" in problem for problem in problems), problems)


class HtmlInlineCodeContractTests(RunFixture):
    def test_contract_rejects_losing_a_literal_marker_after_html(self):
        source = "<pre>\n- - > pretend\n</pre>\nRun `old\n    > command`.\n"
        (self.docs / "guide.md").write_text(source, encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text(
            source.replace("    > command", "      command"), encoding="utf-8")
        write_json(self.out / "detect.after.json", detect.scan_snapshot(self.out, RULES, []))
        result = preserve_check.check(self.out)
        write_json(self.out / "preserve.json", result)
        findings.render(self.out)
        self.assertEqual(result["unacknowledged"], 2)
        problems = contract_check.problems(self.out)
        self.assertTrue(any("lost inline_code 'old > command'" in problem for problem in problems), problems)
        self.assertTrue(any("added inline_code 'old command'" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
