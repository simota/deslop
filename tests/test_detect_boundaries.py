"""Regression checks for protected text and occurrence-level detection."""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detect  # noqa: E402
from common import load_rules  # noqa: E402
from span_helpers import inline_code_spans  # noqa: E402

RULES = load_rules()
COMPILED = detect.compile_rules(RULES)


def scan(text):
    return detect.scan_text(text, COMPILED, RULES["min_chars"])[2]


class CodeBoundaryTests(unittest.TestCase):
    def test_shared_spans_preserve_raw_content_and_offsets(self):
        text = "Before `` a\nb ` c `` after."
        self.assertEqual(inline_code_spans(text), [(7, 20, " a\nb ` c ")])

    def test_inline_delimiters_respect_backslash_context(self):
        for text, content in ((r"\``alpha`", "alpha"),
                              (r"\\`alpha`", "alpha"),
                              (r"`alpha\` tail`", "alpha\\")):
            with self.subTest(text=text):
                self.assertEqual([s[2] for s in inline_code_spans(text)], [content])

    def test_unmatched_opener_does_not_consume_a_later_code_span(self):
        text = "Run `first ``I hope this helps`` here.\n"
        self.assertEqual([s[2] for s in inline_code_spans(text)], ["I hope this helps"])

    def test_many_escaped_runs_without_matching_closers_stay_literal(self):
        self.assertEqual(inline_code_spans(r"\``literal " * 8000), [])

    def test_inline_code_may_wrap_without_exposing_its_content(self):
        text = "Run `foo\nI hope this helps\nbar` here.\n"
        self.assertEqual(scan(text), [])
        masked = detect.mask_code(text)
        self.assertEqual(len(masked), len(text))
        self.assertEqual([i for i, c in enumerate(masked) if c == "\n"],
                         [i for i, c in enumerate(text) if c == "\n"])

    def test_inline_code_closes_only_on_the_exact_delimiter_length(self):
        for text in ("Run `foo`` I hope this helps ` here.\n",
                     "Run ``foo``` I hope this helps `` here.\n"):
            with self.subTest(text=text):
                self.assertEqual(scan(text), [])

    def test_unmatched_delimiters_are_left_as_prose(self):
        text = "Run ``I hope this helps``` here.\n"
        self.assertEqual(detect.mask_code(text), text)
        self.assertIn("ART-03", {h["rule"] for h in scan(text)})

    def test_inline_code_does_not_join_separate_blocks(self):
        for boundary in ("\n\n", "\n \t\n", "\n# ", "\n- "):
            text = "Run `first." + boundary + "I hope this helps\nlast` here.\n"
            with self.subTest(boundary=boundary):
                self.assertIn("ART-03", {h["rule"] for h in scan(text)})

    def test_escaped_opener_does_not_hide_prose(self):
        text = "Run \\`I hope this helps` here.\n"
        self.assertIn("ART-03", {h["rule"] for h in scan(text)})

    def test_code_fence_ignores_overindented_closing_marker(self):
        for marker in ("    ```", "\t```", "    ~~~"):
            fence = "~~~" if "~" in marker else "```"
            text = f"{fence}text\n{marker}\nI hope this helps\n{fence}\n"
            with self.subTest(marker=marker):
                self.assertEqual(scan(text), [])

    def test_code_fence_accepts_a_longer_closing_marker(self):
        text = "```text\nI hope this helps\n  ````\nI hope this helps\n"
        hits = [h for h in scan(text) if h["rule"] == "ART-03"]
        self.assertEqual([(h["line"], h["text"]) for h in hits],
                         [(4, "I hope this helps")])


class QuoteExemptionTests(unittest.TestCase):
    def test_artifact_exemption_is_limited_to_the_quoted_occurrence(self):
        for opening, closing in (("\"", "\""), ("“", "”"), ("'", "'"), ("‘", "’")):
            text = f"The transcript says {opening}I hope this helps{closing}. I hope this helps.\n"
            hits = [h for h in scan(text) if h["rule"] == "ART-03"]
            exemptions = [{"path": "a.md", "rule": "ART-03", "text": "I hope this helps",
                           "reason": "quoted chatbot transcript"}]
            with self.subTest(quote=opening):
                self.assertEqual([h["context"] for h in hits], ["quote", "prose"])
                self.assertEqual([bool(detect.exemption_for(h, "a.md", exemptions, text))
                                  for h in hits], [True, False])

    def test_japanese_inline_quotation_can_be_exempted(self):
        for opening, closing in (("「", "」"), ("『", "』")):
            text = f"回答は{opening}お役に立てれば幸いです{closing}と締めていた。お役に立てれば幸いです。\n"
            hits = [h for h in scan(text) if h["rule"] == "ART-04"]
            exemptions = [{"path": "a.md", "rule": "ART-04", "text": "お役に立てれば幸いです",
                           "reason": "チャット回答からの引用"}]
            with self.subTest(quote=opening):
                self.assertEqual([bool(detect.exemption_for(h, "a.md", exemptions, text))
                                  for h in hits], [True, False])

    def test_incomplete_or_code_only_quote_does_not_exempt_prose(self):
        for text in ('The transcript says "I hope this helps.\n',
                     '`"` I hope this helps `"`\n',
                     'The log says \\"I hope this helps\\".\n'):
            with self.subTest(text=text):
                hits = [h for h in scan(text) if h["rule"] == "ART-03"]
                self.assertEqual([h["context"] for h in hits], ["prose"])

    def test_apostrophe_in_quoted_words_does_not_close_the_quote(self):
        text = "The transcript says 'I don't know. I hope this helps'.\n"
        hit = next(h for h in scan(text) if h["rule"] == "ART-03")
        self.assertEqual(hit["context"], "quote")

    def test_elided_words_do_not_prevent_the_outer_quote_from_closing(self):
        for beginning in ("Back in the '90s, ", "'Tis simple: "):
            text = f'The transcript says "{beginning}I hope this helps". I hope this helps.\n'
            hits = [h for h in scan(text) if h["rule"] == "ART-03"]
            exemptions = [{"path": "a.md", "rule": "ART-03", "text": "I hope this helps",
                           "reason": "quoted chatbot transcript"}]
            with self.subTest(beginning=beginning):
                self.assertEqual([bool(detect.exemption_for(h, "a.md", exemptions, text))
                                  for h in hits], [True, False])

    def test_elided_words_do_not_make_an_unclosed_outer_quote_valid(self):
        for beginning in ("Back in the '90s, ", "'Tis simple: "):
            text = f'The transcript says "{beginning}I hope this helps.\n'
            with self.subTest(beginning=beginning):
                hit = next(h for h in scan(text) if h["rule"] == "ART-03")
                self.assertEqual(hit["context"], "prose")


class MaskedProseTests(unittest.TestCase):
    def test_japanese_openers_do_not_include_masked_or_blank_prefixes(self):
        prefixes = ("\n", "---\ntitle: sample\n---\n\n", "```\nsample\n```\n\n")
        for prefix in prefixes:
            for phrase, rule in (("承知しました", "ART-02"),
                                 ("以下に修正しました", "ART-09")):
                text = prefix + "  " + phrase + "。\n"
                hit = next(h for h in scan(text) if h["rule"] == rule)
                with self.subTest(prefix=prefix, rule=rule):
                    self.assertEqual((hit["line"], hit["col"], hit["text"]),
                                     (prefix.count("\n") + 1, 3, phrase))

    def test_code_tokens_do_not_count_as_sources_for_a_prose_statistic(self):
        for code in ("https://example.com", "source ~/.profile", "[source](data.md)"):
            text = f"73% of teams use `{code}`.\n"
            with self.subTest(code=code):
                self.assertIn("CNT-01", {h["rule"] for h in scan(text)})

    def test_prose_citations_still_support_statistics(self):
        for text in ("73% of teams adopt it ([source](data.md)).\n",
                     "73% of teams adopt it: https://example.com/report\n",
                     "73% of teams adopt it, according to the report.\n"):
            with self.subTest(text=text):
                self.assertNotIn("CNT-01", {h["rule"] for h in scan(text)})

    def test_inline_code_does_not_split_a_sourced_paragraph(self):
        for text in ("73% of teams use `one\nthree\nfour` ([source](report.md)).\n",
                     "73% of teams use this command:\n`sample`\n([source](report.md)).\n"):
            with self.subTest(text=text):
                self.assertNotIn("CNT-01", {h["rule"] for h in scan(text)})

    def test_a_source_beyond_a_block_boundary_does_not_support_the_statistic(self):
        for separator in ("\n\n", "\n```\nsample\n```\n", "\n~~~\nsample\n~~~\n"):
            text = "73% of teams adopt it." + separator + "[source](report.md)\n"
            with self.subTest(separator=separator):
                self.assertIn("CNT-01", {h["rule"] for h in scan(text)})


if __name__ == "__main__":
    unittest.main()
