"""Single-pass masking, shared views and cached parses give the old results."""
import random
import re
import sys
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import common  # noqa: E402
import cues  # noqa: E402
import detect  # noqa: E402
import markdown_spans  # noqa: E402
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


def naive_quotation_spans(prose):
    """inline_quotation_spans read one character at a time."""
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’", "「": "」", "『": "』"}
    stack, spans, open_by_closer, escaped = [], [], {}, False
    for i, char in enumerate(prose):
        if char in "\r\n":
            stack.clear()
            open_by_closer.clear()
            escaped = False
            continue
        if char == "\\":
            escaped = not escaped
            continue
        if escaped:
            escaped = False
            continue
        before, after = prose[i - 1:i] if i else "", prose[i + 1:i + 2]
        if char in ("'", "’") and before.isalnum() and after.isalnum():
            continue
        matching = open_by_closer.get(char)
        if matching:
            closing = matching[-1]
            _, start = stack[closing]
            while len(stack) > closing:
                opening, _ = stack.pop()
                open_by_closer[pairs[opening]].pop()
            spans.append((start + 1, i))
        elif char in pairs and not (char == "'" and before.isalnum()):
            open_by_closer.setdefault(pairs[char], []).append(len(stack))
            stack.append((char, i))
    return spans


def naive_bare_destination_ends(text):
    """_bare_destination_ends filled one offset at a time, right to left."""
    ends = [len(text)] * (len(text) + 1)
    for pos in range(len(text) - 1, -1, -1):
        char = text[pos]
        if markdown_spans._escaped_character(text, pos):
            ends[pos] = ends[pos + 2]
        elif char == "(":
            close = ends[pos + 1]
            ends[pos] = ends[close + 1] if 0 <= close < len(text) and text[close] == ")" else -1
        elif char == ")" or char.isspace() or ord(char) < 32 or char == "<":
            ends[pos] = pos
        else:
            ends[pos] = ends[pos + 1]
    return ends


def naive_number_text(text):
    """_number_text with every character's decomposition looked up in turn."""
    marked, previous = [], ""
    for c in text:
        tag = unicodedata.decomposition(c).partition(" ")[0]
        script = tag if tag in ("<super>", "<sub>") else ""
        if script != previous:
            marked.append("^")
        marked.append(c)
        previous = script
    return unicodedata.normalize("NFKC", "".join(marked)).replace("\u2212", "-")


def random_texts(seed, alphabet, count, length):
    rng = random.Random(seed)
    for _ in range(count):
        yield "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, length)))


MARKDOWN_PIECES = [
    "a", "b", " ", "\t", "\n", "\r", "\\", "(", ")", "<", ">", "[", "]", "`", "*", "!", '"', "'", ":",
    "\u3000", "\x01", "http://x.y", "https://e.x/a_(b)", "<https://a.b>", "[r]: ", "> ", "- ", "1. ",
    "```", "    ", "#", "=", "---", "<!--", "-->", "<div>", "[^1]", "「", "」",
]


class SkipAheadScanTests(unittest.TestCase):
    """Scans that jump between the characters they act on, or index each
    distinct character once, give exactly the character-by-character result."""

    def test_quotation_spans_match_reading_every_character(self):
        alphabet = list("ab1 .\\\r\n\"'“”‘’「」『』")
        for text in random_texts(3, alphabet, 5000, 30):
            self.assertEqual(detect.inline_quotation_spans(text), naive_quotation_spans(text), repr(text))
        for path in DOCS:
            prose = detect.masked_views(common.read_text(path), common.is_markdown(path))[1]
            self.assertEqual(detect.inline_quotation_spans(prose), naive_quotation_spans(prose), path)

    def test_enclosing_span_test_matches_checking_every_span(self):
        rng = random.Random(5)
        for _ in range(5000):
            spans = []
            for _ in range(rng.randrange(0, 8)):
                lo = rng.randrange(0, 20)
                spans.append((lo, rng.randrange(lo, 25)))
            holds = detect.enclosed_by(list(spans))
            for _ in range(5):
                start = rng.randrange(0, 25)
                end = rng.randrange(start, 26)
                self.assertEqual(holds(start, end), any(lo <= start and end <= hi for lo, hi in spans),
                                 (spans, start, end))

    def test_destination_whitespace_class_is_str_isspace(self):
        every = "".join(map(chr, range(0x110000)))
        self.assertEqual(re.findall(r"\s", every), [char for char in every if char.isspace()])

    def test_protected_spans_match_stepping_through_every_offset(self):
        texts = [
            # A definition indented under a line end starts on a space, not on a structural character.
            "Read [guide][ref].\n\n  [ref]: https://x.y/(a)\n", "x\n\n [r]: <a b>\n",
            "[a]\n\n   [ref]: docs/old.md \"T\"\n", "\\`a` `b` <https://e.x/`c`> [d](<e f> 'g')\r\n\r\n[h]",
            *random_texts(13, MARKDOWN_PIECES, 600, 40), *(common.read_text(path) for path in DOCS)]
        found = {}
        for step in (False, True):
            original = markdown_spans.STRUCTURAL
            if step:
                # Every offset is then a stop, as in a character-by-character loop.
                markdown_spans.STRUCTURAL = re.compile(r"[\s\S]")
            try:
                for index, text in enumerate(texts):
                    for markdown in (True, False):
                        titles = []
                        spans = list(markdown_spans.protected_inline_spans(text, markdown=markdown, title_spans=titles))
                        found.setdefault((index, markdown), []).append((spans, titles))
            finally:
                markdown_spans.STRUCTURAL = original
        for (index, markdown), (skipping, stepping) in found.items():
            self.assertEqual(skipping, stepping, (texts[index][:80], markdown))

    def test_bare_destination_ends_match_filling_every_offset(self):
        for text in random_texts(11, MARKDOWN_PIECES, 3000, 40):
            self.assertEqual(markdown_spans._bare_destination_ends(text), naive_bare_destination_ends(text), repr(text))
        for path in DOCS:
            text = common.read_text(path)
            self.assertEqual(markdown_spans._bare_destination_ends(text), naive_bare_destination_ends(text), path)

    def test_number_text_matches_looking_up_every_character(self):
        alphabet = list("ab1 .,-+^\ne") + ["²", "³", "¹", "⁰", "ⁿ", "₂", "₁", "ₐ", "０", "１", "−", "﹣", "－",
                                            "½", "ｈ", "ⅷ", "①", "ᵃ", "\u3000"]
        for text in random_texts(2, alphabet, 5000, 25):
            self.assertEqual(preserve_check._number_text(text), naive_number_text(text), repr(text))
        for path in DOCS:
            text = common.read_text(path)
            self.assertEqual(preserve_check._number_text(text), naive_number_text(text), path)


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
