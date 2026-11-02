"""Regression checks for fenced code inside Markdown containers."""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detect  # noqa: E402
import preserve_check  # noqa: E402
from common import code_blocks, load_rules  # noqa: E402

RULES = load_rules()
COMPILED = detect.compile_rules(RULES)


def scan(text):
    return detect.scan_text(text, COMPILED, RULES["min_chars"])[2]


class ContainerCodeTests(unittest.TestCase):
    CONTAINERS = (
        ("- ", "  "),
        ("1. ", "   "),
        ("> ", "> "),
        ("> > ", "> > "),
        ("> - ", ">   "),
        ("- > ", "  > "),
        ("> - > ", ">   > "),
        ("- - ", "    "),
    )

    def test_container_code_is_masked_and_command_changes_are_preserved(self):
        for opening, continuation in self.CONTAINERS:
            for fence in ("```", "~~~"):
                code = f"{opening}{fence}\n{continuation}robust = seamless\n{continuation}{fence}\n"
                with self.subTest(opening=opening, fence=fence):
                    self.assertEqual(scan(code), [])
                    before = code.replace("robust = seamless", "old_command")
                    after = before.replace("old_command", "new_command")
                    diffs = preserve_check.compare(preserve_check.facts(before), preserve_check.facts(after), before)
                    self.assertEqual([(d["change"], d["kind"]) for d in diffs],
                                     [("lost", "code_block"), ("added", "code_block")])

    def test_container_spans_keep_raw_offsets_and_exact_body(self):
        for opening, continuation in self.CONTAINERS:
            prefix = "Before.\n\n"
            opener, body, closer = f"{opening}~~~text\n", f"{continuation}old_command\n", f"{continuation}~~~"
            text = prefix + opener + body + closer + "\n\nAfter 42.\n"
            start = len(prefix)
            with self.subTest(opening=opening):
                self.assertEqual(code_blocks(text), [(start, start + len(opener + body + closer),
                                                      start + len(opener), start + len(opener + body))])
                self.assertEqual(preserve_check.code(text)[0], [body])
                self.assertEqual(preserve_check.facts(text)["number"], {"42": 1})

    def test_fences_continue_inside_preceding_list_and_quote_items(self):
        for text in ("- Item:\n\n  ~~~\n  robust = seamless\n  ~~~\n",
                     "> - Item:\n>\n>   ~~~\n>   robust = seamless\n>   ~~~\n",
                     "- > Item:\n  >\n  > ~~~\n  > robust = seamless\n  > ~~~\n",
                     "> > - Item:\n> >\n> >   ~~~\n> >   robust = seamless\n> >   ~~~\n"):
            with self.subTest(text=text):
                self.assertEqual(scan(text), [])
                self.assertEqual(len(code_blocks(text)), 1)

    def test_unclosed_fences_stop_when_their_container_ends(self):
        for code, following in (
            ("- ~~~\n  old_command\n", "- I hope this helps 42.\n"),
            ("- ~~~\n  old_command\n\n", "I hope this helps 42.\n"),
            ("> ~~~\n> old_command\n", "I hope this helps 42.\n"),
            ("> > ~~~\n> > old_command\n", "> I hope this helps 42.\n"),
            ("> - ~~~\n>   old_command\n", "> - I hope this helps 42.\n"),
            ("- > ~~~\n  > old_command\n", "- I hope this helps 42.\n"),
            ("> ~~~\n> old_command\n", "- > I hope this helps 42.\n"),
        ):
            text = code + following
            with self.subTest(code=code, following=following):
                hits = [h for h in scan(text) if h["rule"] == "ART-03"]
                self.assertEqual([(h["line"], h["text"]) for h in hits],
                                 [(code.count("\n") + 1, "I hope this helps")])
                self.assertEqual(preserve_check.facts(text)["number"], {"42": 1})
                blocks = preserve_check.code(text)[0]
                self.assertEqual(len(blocks), 1)
                self.assertNotIn("I hope this helps", blocks[0])

    def test_closing_fence_keeps_width_character_and_indentation_rules(self):
        for opening, continuation in self.CONTAINERS:
            for fence in ("```", "~~~"):
                wrong = "~~~" if fence == "```" else "```"
                text = (f"{opening}{fence}\n{continuation}    {fence}\n"
                        f"{continuation}{wrong}\n{continuation}{fence[:2]}\n"
                        f"{continuation}I hope this helps\n{continuation}{fence + fence[0]}\n"
                        "\nI hope this helps 42.\n")
                with self.subTest(opening=opening, fence=fence):
                    hits = [h for h in scan(text) if h["rule"] == "ART-03"]
                    self.assertEqual([(h["line"], h["text"]) for h in hits], [(8, "I hope this helps")])
                    self.assertEqual(preserve_check.facts(text)["number"], {"42": 1})

    def test_fence_body_does_not_open_more_containers(self):
        for text in ("~~~\n> ~~~\n- ~~~\nI hope this helps\n~~~\n",
                     "> ~~~\n> > ~~~\n> - ~~~\n> I hope this helps\n> ~~~\n",
                     "- ~~~\n  > ~~~\n  - ~~~\n  I hope this helps\n  ~~~\n"):
            with self.subTest(text=text):
                self.assertEqual(scan(text), [])
                self.assertEqual(len(code_blocks(text)), 1)

    def test_quote_prefix_spacing_may_change_without_ending_the_code(self):
        text = " > ~~~\n>robust = seamless\n   >~~~~\n\nI hope this helps 42.\n"
        self.assertEqual([(h["line"], h["rule"]) for h in scan(text)], [(5, "ART-03")])
        self.assertEqual(preserve_check.facts(text)["number"], {"42": 1})

    def test_same_line_list_item_can_start_one_indented_code_block(self):
        text = "-     robust\n      seamless\n\nI hope this helps 42.\n"
        self.assertEqual(len(code_blocks(text)), 1)
        self.assertEqual([(h["line"], h["rule"]) for h in scan(text)], [(4, "ART-03")])
        self.assertEqual(preserve_check.code(text)[0], ["-     robust\n      seamless"])

    def test_lazy_paragraph_lines_keep_their_list_and_quote_context(self):
        for text in ("- Item\nlazy continuation.\n\n    I hope this helps 42.\n",
                     "> Item\nlazy continuation.\n>     I hope this helps 42.\n",
                     "> - Item\n> lazy continuation.\n>\n>     I hope this helps 42.\n"):
            with self.subTest(text=text):
                self.assertEqual(code_blocks(text), [])
                self.assertEqual([h["rule"] for h in scan(text)], ["ART-03"])
                self.assertEqual(preserve_check.facts(text)["number"], {"42": 1})

    def test_ordered_list_must_start_at_one_to_interrupt_a_paragraph(self):
        for text, line in (
            ("Text.\n2. ~~~\n   I hope this helps.\n   ~~~\n", 3),
            ("- Text.\n  2. ~~~\n     I hope this helps.\n     ~~~\n", 3),
            ("> Text.\n> 2. ~~~\n>    I hope this helps.\n>    ~~~\n", 3),
            ("- Text.\n2. ~~~\n   I hope this helps.\n   ~~~\n", 3),
            ("1. Text.\n2) ~~~\n   I hope this helps.\n   ~~~\n", 3),
            ("- Text.\n2. continued prose.\n\n    I hope this helps.\n", 4),
        ):
            with self.subTest(text=text):
                hits = [h for h in scan(text) if h["rule"] == "ART-03"]
                self.assertEqual([(h["line"], h["text"]) for h in hits], [(line, "I hope this helps")])

    def test_valid_ordered_and_new_container_fences_still_interrupt(self):
        for text in (
            "Text.\n1. ~~~\n   I hope this helps.\n   ~~~\n",
            "Text.\n\n2. ~~~\n   I hope this helps.\n   ~~~\n",
            "2. ~~~\n   I hope this helps.\n   ~~~\n",
            "1. Text.\n2. ~~~\n   I hope this helps.\n   ~~~\n",
            "> 1. Text.\n> 2. ~~~\n>    I hope this helps.\n>    ~~~\n",
            "- Text.\n  1. ~~~\n     I hope this helps.\n     ~~~\n",
            "- Text.\n\n  2. ~~~\n     I hope this helps.\n     ~~~\n",
            "Text.\n> 2. ~~~\n>    I hope this helps.\n>    ~~~\n",
            "Text.\n- ~~~\n  I hope this helps.\n  ~~~\n",
        ):
            with self.subTest(text=text):
                self.assertEqual(scan(text), [])
                self.assertEqual(len(code_blocks(text)), 1)

    def test_empty_list_marker_does_not_interrupt_a_paragraph(self):
        for marker in ("*", "+", "1.", "1)"):
            for prefix in ("", "> "):
                text = (f"{prefix}Text.\n{prefix}{marker}\n"
                        f"{prefix}      I hope this helps 42.\n")
                with self.subTest(marker=marker, prefix=prefix):
                    self.assertEqual(code_blocks(text), [])
                    self.assertEqual([h["rule"] for h in scan(text)], ["ART-03"])
                    self.assertIn("42", preserve_check.facts(text)["number"])

    def test_empty_list_item_after_a_blank_line_can_contain_code(self):
        for prefix in ("", "> "):
            text = (f"{prefix}Text.\n{prefix}\n{prefix}*\n"
                    f"{prefix}      I hope this helps 42.\n")
            with self.subTest(prefix=prefix):
                self.assertEqual(scan(text), [])
                self.assertEqual(len(code_blocks(text)), 1)
                self.assertEqual(preserve_check.facts(text)["number"], {})


if __name__ == "__main__":
    unittest.main()
