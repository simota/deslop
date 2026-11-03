"""Single-pass masking, shared views and cached parses give the old results."""
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import common  # noqa: E402
import cues  # noqa: E402
import detect  # noqa: E402
import preserve_check  # noqa: E402

RULES = common.load_rules()
DOCS = common.iter_docs([str(ROOT / "corpus"), str(ROOT / "examples")])


def blank_one_at_a_time(text, spans):
    for start, end in spans:
        text = text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]
    return text


def naive_sentences(prose, lang, markdown=True):
    pattern = detect.SENTENCE_JA if lang == "ja" else detect.SENTENCE_EN
    out = []
    for para in detect.paragraphs(prose, markdown):
        s = detect.join_lines(para, lang)
        out.extend(m.group(0).strip() for m in pattern.finditer(s) if len(m.group(0).strip()) > 3)
    return out


class BlankSpansTests(unittest.TestCase):
    def test_matches_blanking_each_span_in_turn_including_overlaps(self):
        rng = random.Random(7)
        alphabet = "ab \n\r\t「」。"
        for _ in range(500):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 40)))
            spans = []
            for _ in range(rng.randrange(0, 6)):
                start = rng.randrange(0, len(text) + 1)
                spans.append((start, rng.randrange(start, len(text) + 1)))
            self.assertEqual(detect.blank_spans(text, spans), blank_one_at_a_time(text, spans), (text, spans))

    def test_single_span_blank_keeps_its_meaning(self):
        self.assertEqual(detect.blank("ab\ncd", 1, 4), "a \n d")


class SentenceTests(unittest.TestCase):
    def test_paragraphs_without_terminal_marks_give_no_sentence(self):
        for lang in ("ja", "en"):
            self.assertEqual(detect.sentences("no terminal mark here, e.g. 1.5 or a「quote」\n", lang), [])

    def test_corpus_sentences_match_the_unshortcut_scan(self):
        for path in DOCS:
            prose = detect.masked_views(common.read_text(path), common.is_markdown(path))[1]
            for lang in ("ja", "en"):
                self.assertEqual(detect.sentences(prose, lang), naive_sentences(prose, lang), (path, lang))


class SharedViewTests(unittest.TestCase):
    def test_views_match_masking_the_document_directly(self):
        for path in DOCS:
            text, markdown = common.read_text(path), common.is_markdown(path)
            spans = []
            code_masked = detect.mask_code(text, markdown, url_spans=spans)
            expected = (code_masked, detect.mask_urls(code_masked, url_spans=spans))
            self.assertEqual(detect.masked_views(text, markdown), expected, path)
            # perspective_cues masks front matter first; the views must agree.
            self.assertEqual(detect.masked_views(detect.mask_front_matter(text), markdown), expected, path)

    def test_front_matter_document_views_agree(self):
        text = "---\ntitle: `x` https://e.x\n---\nWe `leverage` [it](https://e.x/a).\n"
        self.assertEqual(detect.masked_views(text), detect.masked_views(detect.mask_front_matter(text)))

    def test_scan_keeps_no_document_cached_after_it_finishes(self):
        detect.scan([DOCS[0]], ROOT, RULES, [])
        self.assertEqual(detect.masked_views.cache_info().currsize, 0)
        self.assertEqual(common._code_blocks.cache_info().currsize, 0)


class CodeBlockCacheTests(unittest.TestCase):
    def test_each_caller_gets_its_own_list(self):
        text = "```\ncode\n```\n"
        first = common.code_blocks(text)
        first.append("changed")
        self.assertEqual(common.code_blocks(text), [(0, 12, 4, 9)])
        self.assertIsInstance(common.code_blocks(text), list)

    def test_indented_flag_is_read_as_a_truth_value(self):
        text = "para\n\n    indented\n"
        self.assertEqual(common.code_blocks(text, 1), common.code_blocks(text, True))
        self.assertEqual(common.code_blocks(text, 0), common.code_blocks(text, False))
        self.assertNotEqual(common.code_blocks(text, True), common.code_blocks(text, False))


class LineCountTests(unittest.TestCase):
    def test_code_lines_match_counting_from_the_start(self):
        samples = [common.read_text(path) for path in DOCS] + [
            "```\n```", "a\n\n    x\n    y\n\n```\nz\n", "- item\n\n      code\n> ```\n> q\n", "",
        ]
        for text in samples:
            for markdown in (True, False):
                code = set()
                for start, end, _, _ in common.code_blocks(text, indented=markdown):
                    code.update(range(text.count("\n", 0, start), text.count("\n", 0, max(start, end - 1)) + 1))
                self.assertEqual(cues.code_lines(text, markdown), code, text[:60])

    def test_preserve_code_matches_blanking_each_block_in_turn(self):
        for path in DOCS:
            text = common.read_text(path)
            for markdown in (True, False):
                spans = common.code_blocks(text, indented=markdown)
                rest = text
                for start, end, _, _ in reversed(spans):
                    rest = rest[:start] + re.sub(r"[^\r\n]", " ", rest[start:end]) + rest[end:]
                self.assertEqual(preserve_check.code(text, markdown),
                                 ([text[b:e] for _, _, b, e in spans], rest), path)


if __name__ == "__main__":
    unittest.main()
