"""Regression checks for references, numeric ranges and detector CLI errors."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import detect  # noqa: E402

RULES = common.load_rules()
COMPILED = detect.compile_rules(RULES)


def hits_for(text, rule):
    return [hit for hit in detect.scan_text(text, COMPILED, RULES["min_chars"])[2]
            if hit["rule"] == rule]


class ReferencePlaceholderReviewTests(unittest.TestCase):
    def test_non_definitions_do_not_exempt_a_placeholder(self):
        for definition in (
            "```md\n[Your Name]: person.md\n```\n",
            "~~~md\n[Your Name]: person.md\n~~~\n",
            "<div>\n[Your Name]: person.md\n</div>\n",
            "[Your Name]: person.md unquoted words\n",
            "A paragraph continues.\n[Your Name]: person.md\n",
            "`literal\n[Your Name]: person.md\ntext`\n",
        ):
            with self.subTest(definition=definition):
                text = "Signed, [Your Name]\n\n" + definition
                self.assertEqual([(h["line"], h["text"]) for h in hits_for(text, "ART-07")],
                                 [(1, "[Your Name]")])

    def test_front_matter_definition_does_not_resolve_a_body_placeholder(self):
        text = "---\n[Your Name]: person.md\n---\nSigned, [Your Name]\n"
        self.assertEqual([(h["line"], h["text"]) for h in hits_for(text, "ART-07")],
                         [(4, "[Your Name]")])

    def test_complete_definitions_resolve_shortcut_links(self):
        for definition in (
            "[Your Name]: person.md\n",
            "[Your Name]:\n  person.md\n",
            "> [Your Name]: person.md\n",
            "- [Your Name]: person.md\n",
            ">\t[Your Name]: person.md\n",
            "- item\n\n\t[Your Name]: person.md\n",
            "1. item\n\n\t[Your Name]: person.md\n",
            "[your    name]: person.md\n",
            "[YOUR\tNAME]: person.md\n",
        ):
            with self.subTest(definition=definition):
                self.assertEqual(hits_for("See [Your Name].\n\n" + definition, "ART-07"), [])

    def test_escaped_shortcut_stays_a_placeholder(self):
        for prefix, expected in (("\\", 1), ("\\\\", 0), ("\\\\\\", 1)):
            with self.subTest(prefix=prefix):
                text = f"Signed, {prefix}[Your Name]\n\n[Your Name]: person.md\n"
                self.assertEqual(len(hits_for(text, "ART-07")), expected)

    def test_inline_destination_cannot_define_a_reference_label(self):
        text = "Signed, [Name]\n\n[other]([Name]:person.md)\n"
        self.assertEqual([(h["line"], h["text"]) for h in hits_for(text, "ART-07")],
                         [(1, "[Name]")])


class StatisticRangeReviewTests(unittest.TestCase):
    def test_spaced_ranges_are_not_single_statistical_claims(self):
        for number in ("73-80%", "73 - 80%", "73% - 80%", "73  –  80%",
                       "73 percent - 80 percent", "７３ 〜 ８０％", "2倍 ~ 3倍"):
            with self.subTest(number=number):
                self.assertEqual(hits_for(f"About {number} of teams use it.\n", "CNT-01"), [])

    def test_a_range_does_not_hide_a_separate_statistic(self):
        text = "About 73 - 80% of teams use it, and 90% of users keep it.\n"
        self.assertEqual([h["text"] for h in hits_for(text, "CNT-01")], ["90%"])

    def test_a_dash_without_a_preceding_number_is_not_a_range(self):
        for text in ("Most teams — about 73% — use it.\n", "Teams adopt it - 73% do.\n",
                     "Teams use v2 - 73% adopted it.\n"):
            with self.subTest(text=text):
                self.assertEqual([h["text"] for h in hits_for(text, "CNT-01")], ["73%"])


class StatisticParagraphReviewTests(unittest.TestCase):
    def test_a_different_markdown_block_cannot_supply_the_source(self):
        for text in (
            "73% of teams use it.\n## Details\n[Reference](report.md)\n",
            "- 73% of teams use it.\n- [Reference](report.md)\n",
            "73% of teams use it.\n> [Reference](report.md)\n",
            "73% of teams use it.\n***\n[Reference](report.md)\n",
            "> 73% of teams use it.\n>\n> [Reference](report.md)\n",
        ):
            with self.subTest(text=text):
                self.assertEqual([h["text"] for h in hits_for(text, "CNT-01")], ["73%"])

    def test_continuations_in_the_same_block_still_supply_the_source(self):
        for text in (
            "73% of teams use it.\n[Reference](report.md)\n",
            "- 73% of teams use it.\n  [Reference](report.md)\n",
            "> 73% of teams use it.\n> [Reference](report.md)\n",
            "> 73% of teams use it.\n[Reference](report.md)\n",
            "73% of teams use `one\ntwo\nthree` ([Reference](report.md)).\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(hits_for(text, "CNT-01"), [])

    def test_an_html_block_does_not_make_an_uncited_claim_disappear(self):
        text = "<div>\n73% of teams use it.\n</div>\n"
        self.assertEqual([h["text"] for h in hits_for(text, "CNT-01")], ["73%"])


class DetectorURLReviewTests(unittest.TestCase):
    def test_bare_urls_with_balanced_parentheses_and_mixed_case_schemes_are_masked(self):
        for url in ("https://example.com/a(b)/robust", "https://example.com/a(b(c)d)e/robust",
                    "HTTPS://example.com/robust", "hTtPs://example.com/robust"):
            with self.subTest(url=url):
                self.assertEqual(hits_for(f"Read {url} here.\n", "EN-04"), [])

    def test_parenthesized_url_does_not_hide_following_prose(self):
        text = "Read (https://example.com/a(b)/robust). The cache is robust.\n"
        self.assertEqual([(h["col"], h["text"]) for h in hits_for(text, "EN-04")],
                         [(text.rindex("robust") + 1, "robust")])

    def test_overlapping_explicit_and_bare_urls_preserve_offsets(self):
        for link in ("[guide](HTTPS://example.com/a(b)/robust)",
                     "<HTTPS://example.com/a(b)/robust>"):
            text = f"Read {link}. The cache is robust.\n"
            with self.subTest(link=link):
                self.assertEqual([(h["col"], h["text"]) for h in hits_for(text, "EN-04")],
                                 [(text.rindex("robust") + 1, "robust")])

    def test_url_tracking_artifacts_remain_visible(self):
        text = "Read HTTPS://example.com/a(b)/robust?utm_source=chatgpt.com here.\n"
        self.assertEqual(hits_for(text, "EN-04"), [])
        self.assertEqual(len(hits_for(text, "ART-06")), 1)


class SetextHeadingReviewTests(unittest.TestCase):
    def cue_rows(self, text):
        lang, metrics, _ = detect.scan_text(text, COMPILED, RULES["min_chars"])
        return [(cue["line"], cue["perspective"]) for cue in
                detect.perspective_cues(text, lang, metrics["chars"], RULES["min_chars"])]

    def test_setext_title_question_and_summary_keep_their_original_lines(self):
        text = ("Tile cache\n==========\n\nThis guide explains how the tile cache works.\n\n"
                "Why cache?\n----------\n\nIt stores each tile on disk.\n\n"
                "Summary\n-------\n\nThe disk holds each tile.\n")
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=newline):
                self.assertEqual(self.cue_rows(text.replace("\n", newline)),
                                 [(4, "STR-01"), (6, "STR-14"), (11, "STR-02")])

    def test_setext_and_atx_have_the_same_density_metrics(self):
        body = "The tile cache reads one file for each request.\n"
        atx = "# Tile cache\n\n" + body + "\n## Why cache?\n\n" + body
        setext = "Tile cache\n==========\n\n" + body + "\nWhy cache?\n----------\n\n" + body
        self.assertEqual(detect.metrics(setext, "en"), detect.metrics(atx, "en"))

    def test_a_multiline_setext_heading_counts_once_and_is_not_a_sentence(self):
        text = "Why cache?\nWhy keep tiles?\n----------------\n\nThe disk holds tiles.\n"
        metrics = detect.metrics(text, "en")
        self.assertEqual(metrics["sentences"], 1)
        self.assertEqual(metrics["heading_per_1000"], 1000 / len("The disk holds tiles."))
        self.assertEqual(self.cue_rows(text), [(1, "STR-14")])

    def test_setext_headings_end_a_japanese_sentence_ending_run(self):
        text = "設定を保存します。値を削除します。\n\n次の手順\n--------\n\nログを出力します。結果を確認します。\n"
        self.assertEqual(detect.metrics(text, "ja")["ending_run"], 2)

    def test_masked_inline_code_keeps_the_original_setext_block_boundary(self):
        text = "`hidden`\n    Why cache?\n---\n\nIt stores tiles.\n"
        _, metrics, _ = detect.scan_text(text, COMPILED, RULES["min_chars"])
        self.assertEqual(metrics["heading_per_1000"], 1000 / len("It stores tiles."))
        self.assertEqual(self.cue_rows(text), [(2, "STR-14")])

    def test_separators_and_code_do_not_become_setext_headings(self):
        text = "The disk holds tiles.\n\n---\n\nThe cache reads them.\n"
        self.assertEqual(detect.metrics(text, "en")["hr_count"], 1)
        self.assertEqual(detect.metrics(text, "en")["heading_per_1000"], 0)
        for code in ("```\nWhy cache?\n---\n```\n", "    Why cache?\n    ---\n"):
            with self.subTest(code=code):
                self.assertEqual(self.cue_rows(code), [])


class DetectorOutputReviewTests(unittest.TestCase):
    def test_unwritable_output_is_a_usage_error_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "guide.md"
            document.write_text("The file contains settings.\n", encoding="utf-8")
            output = root / "output"
            output.mkdir()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    detect.main([str(document), "--out", str(output), "--quiet"])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("error:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertEqual(list(output.iterdir()), [])

    def test_a_genre_path_symlink_loop_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / "guide.md"
            document.write_text("The file contains settings.\n", encoding="utf-8")
            loop = root / "loop"
            loop.symlink_to(loop)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    detect.main([str(document), "--genre", f"{loop}=message", "--quiet"])
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("error:", stderr.getvalue())
            self.assertIn("loop", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
