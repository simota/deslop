"""Only real link destinations are opaque to prose detection."""
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings


class DetectorURLMaskingTests(unittest.TestCase):
    def hits(self, text):
        rules = common.load_rules()
        return detect.scan_text(text, detect.compile_rules(rules), rules["min_chars"])[2]

    def test_complete_destinations_are_not_lexical_prose(self):
        for text in (
            "[guide]: docs/robust-cache.md\n",
            "[guide]:\n  docs/robust-cache.md\n",
            "> [guide]: docs/robust-cache.md\n",
            "- [guide]: docs/robust-cache.md\n",
            "[guide](docs/a(b)/robust.md)\n",
            r"[guide](docs/a\)/robust.md)" + "\n",
            "[guide](<docs/robust cache.md>)\n",
            "[guide](\n docs/robust-cache.md\n)\n",
            "<https://example.com/a(b)/robust>\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.hits(text), [])

    def test_invalid_and_escaped_link_syntax_remains_prose(self):
        for text in (
            "guide](leverage)\n",
            r"\[guide](leverage)" + "\n",
            "[guide](docs/leverage.md\n",
            "[guide](leverage arbitrary)\n",
            "[guide]: leverage arbitrary\n",
        ):
            with self.subTest(text=text):
                hits = [hit for hit in self.hits(text) if hit["rule"] == "EN-03"]
                self.assertEqual([hit["text"] for hit in hits], ["leverage"])

    def test_masked_code_cannot_turn_invalid_syntax_into_a_link(self):
        for text in (
            "[guide](leverage `x`)\n",
            "[guide](leverage `x` )\n",
            "> [guide](leverage `x`)\n",
            "[guide](leverage\n`x`)\n",
        ):
            with self.subTest(text=text):
                hits = [hit for hit in self.hits(text) if hit["rule"] == "EN-03"]
                self.assertEqual([hit["text"] for hit in hits], ["leverage"])

    def test_labels_titles_and_following_prose_stay_visible(self):
        text = '[robust](docs/robust-cache.md "robust") and robust.\n'
        hits = [hit for hit in self.hits(text) if hit["rule"] == "EN-04"]
        self.assertEqual([hit["col"] for hit in hits],
                         [text.index("robust") + 1,
                          text.index('"robust"') + 2,
                          text.rindex("robust") + 1])

    def test_reference_title_is_prose_but_its_destination_is_not(self):
        text = '[ref]: docs/robust-cache.md "robust"\n'
        hits = [hit for hit in self.hits(text) if hit["rule"] == "EN-04"]
        self.assertEqual([(hit["text"], hit["col"]) for hit in hits],
                         [("robust", text.index('"robust"') + 2)])

    def test_tracking_artifacts_in_destinations_remain_visible(self):
        for text in (
            "[guide](docs/robust.md?utm_source=chatgpt.com)\n",
            "[guide]: docs/robust.md?utm_source=chatgpt.com\n",
            "<https://example.com/a(b)/robust?utm_source=chatgpt.com>\n",
        ):
            with self.subTest(text=text):
                self.assertEqual({hit["rule"] for hit in self.hits(text)}, {"ART-06"})

    def test_code_and_bare_urls_keep_their_existing_protection(self):
        for text in (
            "`guide](leverage)`\n",
            "```\n[guide]: docs/robust.md\n```\n",
            "Read https://example.com/robust.\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.hits(text), [])

    def test_metadata_and_prior_code_do_not_change_reference_boundaries(self):
        for prefix in ("---\nkey: '`'\n---\n", "```\n- fake\n```\n", "<!-- note -->\n"):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.hits(prefix + "[guide]: docs/robust.md\n"), [])

    def test_url_content_does_not_inflate_prose_metrics(self):
        rules = common.load_rules()
        text = "[guide]: <docs/robust cache.md>\n"
        _, metrics, _ = detect.scan_text(text, detect.compile_rules(rules), rules["min_chars"])
        self.assertEqual(metrics["chars"], 0)

    def test_reference_only_documents_have_no_prose_or_bold_label_hits(self):
        rules = common.load_rules()
        source = "".join(f"[ref{i}]: docs/item{i}.md\n" for i in range(4000))
        _, metrics, hits = detect.scan_text(source, detect.compile_rules(rules), rules["min_chars"])
        self.assertEqual(metrics["chars"], 0)
        self.assertEqual(metrics["boldlead_items"], 0)
        self.assertEqual(hits, [])

    def test_bold_label_indentation_keeps_unicode_whitespace(self):
        for prefix in ("", " ", "\t", "\u3000", "\u00a0"):
            with self.subTest(prefix=prefix):
                text = "\n \n\t\n" + prefix + "- **Label**: text\n"
                self.assertEqual(detect.metrics(text, "en")["boldlead_items"], 1)

    def test_bold_label_counts_a_colon_inside_the_bold(self):
        text = "- **Review:** checked\n- **Pool：** drained\n- **Plain** text\n- **Out**: x\n"
        self.assertEqual(detect.metrics(text, "en")["boldlead_items"], 3)


class DetectorURLMaskingContractTests(RunFixture):
    def test_fake_link_cannot_hide_an_unacknowledged_lexical_hit(self):
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text("guide](leverage)\n", encoding="utf-8")
        findings.render(self.out)
        errors = contract_check.problems(self.out)
        self.assertTrue(any("open hit guide.md:" in error and "EN-03" in error for error in errors), errors)

    def test_masked_code_cannot_hide_a_new_lexical_hit(self):
        (self.docs / "guide.md").write_text("Read `x`.\n", encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text("[guide](leverage `x`)\n", encoding="utf-8")
        findings.render(self.out)
        errors = contract_check.problems(self.out)
        self.assertTrue(any("open hit guide.md:" in error and "EN-03" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
