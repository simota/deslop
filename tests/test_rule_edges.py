"""Rule patterns match what reference/patterns.md documents, and no more."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deslop" / "scripts"))

import detect  # noqa: E402
from common import load_rules, read_text  # noqa: E402

RULES = load_rules()
COMPILED = detect.compile_rules(RULES)


def rules_of(text):
    return {h["rule"] for h in detect.scan_text(text, COMPILED, RULES["min_chars"])[2]}


class RuleEdgeTests(unittest.TestCase):
    def test_japanese_response_framing_with_matomeru(self):
        for text in ("以下に手順をまとめました。", "以下にまとめます。", "以下は設定を修正したものです。"):
            self.assertIn("ART-09", rules_of(text), text)

    def test_ai_self_reference_needs_the_model_speaking(self):
        for text in ("As an AI language model, I cannot browse.", "As an AI, I cannot browse.",
                     "As an AI developed by a lab, I cannot browse.", "As an AI model, I cannot help.",
                     "As an AI chatbot, I cannot browse.", "As an AI system, I do not have feelings."):
            self.assertIn("ART-05", rules_of(text), text)
        for text in ("As an AI researcher, I have reviewed many papers.",
                     "The tool runs as an AI agent, I think."):
            self.assertNotIn("ART-05", rules_of(text), text)

    def test_wrap_up_after_a_sentence_on_the_same_line(self):
        self.assertIn("EN-08", rules_of("The tests pass. In conclusion, the fix works."))
        self.assertNotIn("EN-08", rules_of("The result was overall, fine."))
        self.assertNotIn("EN-08", rules_of("Some tools, e.g. Overall, are named so."))

    def test_a_pivotal_role_is_importance_asserted(self):
        self.assertIn("EN-05", rules_of("It has a pivotal role in the system."))
        self.assertNotIn("EN-14", rules_of("It has a pivotal role in the system."))

    def test_claim_words_match_whole_words(self):
        for text in ("利用規約の第5条で、消費税は10%と定める。", "予約の手数料は5%です。", "Lessons: the fee is 5%."):
            self.assertNotIn("CNT-01", rules_of(text), text)
        for text in ("約30%の企業が導入した。", "処理は約 2倍になった。", "It is about 30% cheaper.",
                     "Users saw 40% less waiting.", "The cache saved 30% of the load.",
                     "Builds were cutting 20% of the time.", "コストを約半分、つまり50%にした。",
                     "The cache lessens load by 30%."):
            self.assertIn("CNT-01", rules_of(text), text)

    def test_english_quoting_some_japanese_stays_english(self):
        quote = "> 設定ファイルを読み込んでから、サーバーを起動してください。\n\n"
        prose = "The service reads its settings — then it starts — and it logs a line. " * 12
        lang, metrics, hits = detect.scan_text(quote + prose, COMPILED, RULES["min_chars"])
        self.assertEqual(lang, "en")
        self.assertIn("DEN-02", {h["rule"] for h in hits})

    def test_latin_product_names_do_not_outvote_a_japanese_sentence(self):
        self.assertEqual(detect.language("Next.js と React と Node.js が重要です。"), "ja")
        self.assertIn("JA-03", rules_of("Next.js と React と Node.js が重要です。"))
        self.assertEqual(detect.language("中文 text"), "en")

    def test_byte_order_mark_is_not_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.md"
            path.write_bytes("\ufeff---\ntitle: We leverage robust tools\n---\nCertainly! Here is the plan.\n".encode())
            text = read_text(path)
        self.assertFalse(text.startswith("\ufeff"))
        found = {(h["line"], h["rule"]) for h in detect.scan_text(text, COMPILED, RULES["min_chars"])[2]}
        self.assertIn((4, "ART-01"), found)
        self.assertFalse({rule for line, rule in found if line == 2})

    def test_decode_error_counts_the_byte_order_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.md"
            path.write_bytes(b"\xef\xbb\xbfa\xff")
            with self.assertRaisesRegex(ValueError, "at byte 4"):
                detect.scan([path], Path(tmp).resolve(), RULES, [])


if __name__ == "__main__":
    unittest.main()
