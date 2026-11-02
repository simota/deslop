"""Link destinations must not lend their backticks to surrounding prose."""
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check


class DetectorLinkBoundaryTests(unittest.TestCase):
    def hits(self, text):
        rules = common.load_rules()
        return detect.scan_text(text, detect.compile_rules(rules), rules["min_chars"])[2]

    def test_destination_backticks_do_not_hide_following_artifacts(self):
        links = (
            "<https://example.com/`literal>",
            "[manual](https://example.com/`literal)",
            "[manual](<https://example.com/`literal>)",
            "[manual](docs/`literal)",
            "[manual]: https://example.com/`literal\n",
        )
        for link in links:
            with self.subTest(link=link):
                text = f"{link} I hope this helps. `id`.\n"
                hits = [h for h in self.hits(text) if h["rule"] == "ART-03"]
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0]["text"], "I hope this helps")
                lines = text.splitlines()
                self.assertEqual(lines[hits[0]["line"] - 1][hits[0]["col"] - 1:],
                                 "I hope this helps. `id`.")

    def test_destination_backticks_do_not_hide_lexical_hits(self):
        hits = self.hits("<https://example.com/`literal> A robust cache. `id`.\n")
        self.assertTrue(any(h["rule"] == "EN-04" and h["text"] == "robust" for h in hits))

    def test_real_code_after_link_stays_masked(self):
        text = "<https://example.com/`literal> `I hope this helps.`\n"
        self.assertFalse(any(h["rule"] == "ART-03" for h in self.hits(text)))

    def test_link_syntax_inside_real_code_stays_opaque(self):
        text = "``<https://example.com/`literal> I hope this helps.``\n"
        self.assertEqual(self.hits(text), [])

    def test_tracking_artifacts_in_destinations_remain_visible(self):
        for link in ("<https://example.com/`literal?utm_source=chatgpt.com>",
                     "[manual](https://example.com/`literal?utm_source=chatgpt.com)"):
            with self.subTest(link=link):
                hits = self.hits(f"{link} Read `id`.\n")
                self.assertTrue(any(h["rule"] == "ART-06" for h in hits))

    def test_reference_looking_paragraph_lines_keep_code_artifacts_masked(self):
        for text in (
            "The literal mapping is\n[label]: `参考になれば幸いです`\n",
            "> The literal mapping is\n> [label]: `参考になれば幸いです`\n",
            "- The literal mapping is\n  [label]: `参考になれば幸いです`\n",
            "[bad]: docs/one.md junk\n[label]: `参考になれば幸いです`\n",
            "[bad]: docs/one.md junk\n2. [label]: `参考になれば幸いです`\n",
        ):
            with self.subTest(text=text):
                self.assertFalse(any(hit["rule"] == "ART-04" for hit in self.hits(text)))

    def test_real_reference_destinations_keep_tracking_artifacts_visible(self):
        for prefix in ("", "A paragraph.\n\n", "# Heading\n", "A paragraph.\n> ", "A paragraph.\n- "):
            with self.subTest(prefix=prefix):
                text = prefix + "[ref]: https://example.com/`literal?utm_source=chatgpt.com\n"
                self.assertTrue(any(hit["rule"] == "ART-06" for hit in self.hits(text)))

    def test_references_after_explicit_html_keep_tracking_artifacts_visible(self):
        for html in ("<pre>x</pre>", "<!-- note -->", "<?target?>", "<!A>", "<![CDATA[x]]>"):
            with self.subTest(html=html):
                text = html + "\n[ref]: https://example.com/`literal?utm_source=chatgpt.com\nRead `id`.\n"
                self.assertTrue(any(hit["rule"] == "ART-06" for hit in self.hits(text)))

    def test_inline_html_does_not_unmask_code_on_a_paragraph_continuation(self):
        for text in ("Text <!-- note -->", "Text <pre>literal</pre>", "<span>literal</span>"):
            with self.subTest(text=text):
                source = text + "\n[label]: `参考になれば幸いです`\n"
                self.assertFalse(any(hit["rule"] == "ART-04" for hit in self.hits(source)))


class DetectorLinkContractTests(RunFixture):
    def test_artifact_introduced_after_link_fails_the_run_contract(self):
        before = "<https://example.com/`literal> Read `id`.\n"
        (self.docs / "guide.md").write_text(before, encoding="utf-8")
        self.make_run()
        (self.out / "rewritten" / "guide.md").write_text(
            before.replace("Read", "I hope this helps."), encoding="utf-8")
        self.assertEqual(preserve_check.check(self.out)["unacknowledged"], 0)
        findings.render(self.out)
        problems = contract_check.problems(self.out)
        self.assertTrue(any("open hit guide.md:" in p and "ART-03" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
