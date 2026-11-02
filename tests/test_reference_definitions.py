"""Reference destinations remain facts across line and container boundaries."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"))

import common
import contract_check
import detect
import findings
import preserve_check
from test_run_validation import RunFixture


class ReferenceDefinitionTests(unittest.TestCase):
    def assert_target_change(self, source, target="docs/old.md"):
        before = preserve_check.facts(source)
        changed = target.replace("old", "new")
        after = preserve_check.facts(source.replace(target, changed))
        self.assertEqual(before["url"], {target: 1})
        self.assertEqual({(d["kind"], d["change"], d["value"])
                          for d in preserve_check.compare(before, after, source)},
                         {("url", "lost", target), ("url", "added", changed)})

    def test_destination_can_follow_the_label_on_the_next_line(self):
        for indent in ("", " ", "   ", "\t"):
            with self.subTest(indent=indent):
                self.assert_target_change(f"Read [guide][ref].\n\n[ref]:\n{indent}docs/old.md\n")

    def test_definitions_inside_list_and_quote_containers_are_preserved(self):
        for source in (
            "Read [guide][ref].\n\n> [ref]: docs/old.md\n",
            "> Read [guide][ref].\n>\n> [ref]:\n>   docs/old.md\n",
            "- [ref]: docs/old.md\n\nRead [guide][ref].\n",
            "- Read [guide][ref].\n\n  [ref]:\n    docs/old.md\n",
            "- Item\n  - [ref]: docs/old.md\n\nRead [guide][ref].\n",
            "> - [ref]:\n>     docs/old.md\n\nRead [guide][ref].\n",
            "1. [ref]: docs/old.md\n\nRead [guide][ref].\n",
        ):
            with self.subTest(source=source):
                self.assert_target_change(source)

    def test_nested_and_escaped_destinations_keep_their_full_value(self):
        for target in ("docs/a(b(c))/old.md", r"docs/a\)b/old.md",
                       "docs/old file.md", r"docs/a\>b/old.md"):
            for prefix in ("", "> "):
                with self.subTest(target=target, prefix=prefix):
                    self.assert_target_change(f"{prefix}[ref]:\n{prefix}  <{target}>\n", target)

    def test_wrapped_titles_leave_numbers_and_following_code_visible(self):
        for source in (
            '[ref]:\n  docs/old.md "Edition `2`"\nRead `command` in 2026.\n',
            '[ref]: docs/old.md\n  "Edition `2`"\nRead `command` in 2026.\n',
            '> [ref]:\n>   docs/old.md\n>   "Edition `2`"\n\nRead `command` in 2026.\n',
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {"docs/old.md": 1})
                self.assertEqual(facts["number"], {"2": 1, "2026": 1})
                self.assertEqual(facts["inline_code"], {"command": 1})

    def test_blank_lines_and_container_changes_do_not_join_definitions(self):
        for source in (
            "[ref]:\n\ndocs/old.md\n",
            "> [ref]:\ndocs/old.md\n",
            "- [ref]:\n- docs/old.md\n",
            "[ref]:\n> docs/old.md\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["url"], {})

    def test_invalid_destinations_remain_prose(self):
        for source in (
            "[ref]: docs/a(b/old.md\n",
            "[ref]: docs/old.md arbitrary 300\n",
            "[ref]: <docs/old.md\n",
            "[ref]:\n  <docs/old\n  file.md>\n",
            r"\[ref]: docs/old.md" + "\n",
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                if "300" in source:
                    self.assertEqual(facts["number"], {"300": 1})

    def test_reference_looking_code_stays_code(self):
        for source in ("```\n[ref]: docs/old.md\n```\n",
                       "> ```\n> [ref]: docs/old.md\n> ```\n",
                       "    [ref]: docs/old.md\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(sum(facts["code_block"].values()), 1)

    def test_code_blocks_retain_the_enclosing_reference_container(self):
        for source in (
            "- - ```\n    command\n    ```\n\n    [ref]: docs/old.md\n\n[ref]\n",
            "> - - ```\n>     > - [fake]: docs/fake.md\n>     ```\n>\n>     [ref]:\n>       docs/old.md\n\n[ref]\n",
            "- - item\n\n        [fake]: docs/fake.md\n\n    [ref]: docs/old.md\n\n[ref]\n",
        ):
            with self.subTest(source=source):
                self.assert_target_change(source)
                self.assertEqual(sum(preserve_check.facts(source)["code_block"].values()), 1)

    def test_lazy_paragraph_lines_retain_the_list_for_later_definitions(self):
        for source in (
            "- Item\nlazy continuation.\n\n    [ref]: docs/old.md\n\nRead [guide][ref].\n",
            "> - Item\n> lazy continuation.\n>\n>     [ref]: docs/old.md\n\nRead [guide][ref].\n",
        ):
            with self.subTest(source=source):
                self.assert_target_change(source)

    def test_ordered_definitions_can_start_after_headings_and_thematic_breaks(self):
        for boundary in ("# Heading", "***"):
            with self.subTest(boundary=boundary):
                self.assert_target_change(f"{boundary}\n2. [ref]: docs/old.md\n\nRead [guide][ref].\n")

    def test_noninitial_ordered_marker_cannot_interrupt_a_paragraph(self):
        source = "A paragraph.\n2. [ref]: docs/old.md\n\nRead [guide][ref].\n"
        self.assertEqual(preserve_check.facts(source)["url"], {})

    def test_reference_looking_paragraph_continuations_keep_their_inline_code(self):
        for source in (
            "The literal mapping is\n[label]: `参考になれば幸いです`\n",
            "> The literal mapping is\n> [label]: `参考になれば幸いです`\n",
            "- The literal mapping is\n  [label]: `参考になれば幸いです`\n",
            "10. The literal mapping is\n    [label]: `参考になれば幸いです`\n",
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_invalid_definitions_start_paragraphs_instead_of_reopening_definition_slots(self):
        for invalid in ("[bad]: docs/one.md junk", "[bad]: <unterminated", "[bad]:"):
            for following in ("[label]: `参考になれば幸いです`", "2. [label]: `参考になれば幸いです`"):
                with self.subTest(invalid=invalid, following=following):
                    facts = preserve_check.facts(f"{invalid}\n{following}\n")
                    self.assertEqual(facts["url"], {})
                    self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_invalid_next_line_title_leaves_the_following_paragraph_as_inline_text(self):
        source = '[one]: docs/one.md\n"unclosed title\n[label]: `literal`\n'
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {"docs/one.md": 1})
        self.assertEqual(facts["inline_code"], {"literal": 1})

    def test_consecutive_and_split_definitions_consume_their_complete_titles(self):
        source = ('[one]:\n  docs/one.md "Title\n[label]: `literal`\nends"\n'
                  '[two]: docs/two.md\n2. [three]: docs/three.md\n')
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {f"docs/{name}.md": 1 for name in ("one", "two", "three")})
        self.assertEqual(facts["inline_code"], {})

    def test_valid_split_definition_can_be_followed_by_a_noninitial_ordered_list(self):
        source = '[one]:\n  docs/one.md "Title\nends"\n2. [two]: docs/two.md\n'
        self.assertEqual(preserve_check.facts(source)["url"], {"docs/one.md": 1, "docs/two.md": 1})

    def test_noninitial_ordered_text_can_continue_a_next_line_title(self):
        source = '[ref]: docs/one.md\n"Title\n2. `literal`\nends"\n'
        facts = preserve_check.facts(source)
        self.assertEqual(facts["url"], {"docs/one.md": 1})
        self.assertEqual(facts["inline_code"], {})
        self.assertEqual(facts["number"], {"2": 1})

    def test_a_real_new_list_item_can_define_a_reference_after_invalid_text(self):
        source = "- [bad]: docs/one.md junk\n- [good]: docs/two.md\n"
        self.assertEqual(preserve_check.facts(source)["url"], {"docs/two.md": 1})

    def test_setext_headings_end_the_paragraph_before_a_reference(self):
        for first, continuation in (("", ""), ("> ", "> "), ("- ", "  "),
                                    ("> - ", ">   "), ("10. ", "    ")):
            for underline in ("=", "=====", "-", "--", "---"):
                for indentation in ("", " ", "   "):
                    source = (f"{first}Title\n{continuation}{indentation}{underline} \t\n"
                              f"{continuation}[ref]: docs/old.md\n")
                    with self.subTest(source=source):
                        self.assert_target_change(source)

    def test_complete_setext_underline_can_follow_a_lazy_title_line(self):
        source = "> Title\nlazy title continuation\n> ===\n> [ref]: docs/old.md\n"
        self.assert_target_change(source)

    def test_invalid_setext_underlines_leave_the_paragraph_as_prose(self):
        for first, continuation in (("", ""), ("> ", "> "), ("- ", "  ")):
            for underline in ("= =", "==-", "--=", "==== trailing", "    ==="):
                source = (f"{first}Title\n{continuation}{underline}\n"
                          f"{continuation}[label]: `参考になれば幸いです`\n")
                with self.subTest(source=source):
                    facts = preserve_check.facts(source)
                    self.assertEqual(facts["url"], {})
                    self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_setext_underlines_require_an_existing_paragraph(self):
        for prefix in ("", "Title\n\n", "# Heading\n", "> ", "[one]: docs/one.md\n"):
            source = prefix + "=====\n[label]: `参考になれば幸いです`\n"
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {"docs/one.md": 1} if prefix.startswith("[one]") else {})
                self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_lazy_underlines_do_not_create_setext_headings(self):
        for source in (
            "> Title\nlazy continuation\n===\n[label]: `参考になれば幸いです`\n",
            "- Title\nlazy continuation\n===\n[label]: `参考になれば幸いです`\n",
            "> Title\n===\n> [label]: `参考になれば幸いです`\n",
            "> > Title\n> ===\n> > [label]: `参考になれば幸いです`\n",
            "- Title\n ===\n  [label]: `参考になれば幸いです`\n",
        ):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_new_containers_cannot_supply_a_setext_heading_without_their_own_title(self):
        for source in ("Title\n> ===\n> [label]: `参考になれば幸いです`\n",
                       "Title\n- ===\n  [label]: `参考になれば幸いです`\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_setext_can_end_a_paragraph_started_by_an_invalid_definition(self):
        self.assert_target_change("[bad]: docs/invalid.md junk\n===\n[ref]: docs/old.md\n")

    def test_explicit_html_end_allows_a_reference_without_a_blank_line(self):
        for html in (
            "<pre>literal</pre>", "<SCRIPT\n data-x='x'>literal\n</style>",
            "<style\tmedia='all'>literal\n</TEXTAREA>", "<textarea>literal</pre>",
            "<!-- note -->", "<!-- note --> <pre>", "<!--\nnote\n-->", "<?target value?>", "<?target\nvalue\n?>",
            "<!DOCTYPE html>", "<!A\nvalue\n>", "<![CDATA[literal]]>", "<![CDATA[\nliteral\n]]>",
        ):
            for first, continuation in (("", ""), ("> ", "> "), ("- ", "  ")):
                for indentation in ("", "   "):
                    lines = html.splitlines()
                    source = first + indentation + lines[0] + "\n"
                    source += "".join(continuation + indentation + line + "\n" for line in lines[1:])
                    source += continuation + "[ref]: docs/old.md\n"
                    with self.subTest(source=source):
                        self.assert_target_change(source)

    def test_explicit_html_blocks_can_interrupt_an_ordinary_paragraph(self):
        for html in ("<pre>literal</pre>", "<!-- note -->", "<?target?>", "<!A>", "<![CDATA[x]]>"):
            with self.subTest(html=html):
                self.assert_target_change(f"A paragraph.\n{html}\n[ref]: docs/old.md\n")

    def test_indented_code_after_html_keeps_the_following_reference_visible(self):
        for html in ("<pre>literal</pre>", "<!-- note -->", "<?target?>", "<!A>", "<![CDATA[x]]>"):
            for first, continuation in (("", ""), ("> ", "> "), ("- ", "  ")):
                source = first + html + "\n" + continuation + "    command\n"
                source += continuation + "[ref]: docs/old.md\n"
                with self.subTest(source=source):
                    self.assert_target_change(source)

    def test_html_block_body_does_not_open_definitions_or_containers(self):
        for opening, closing in (("<pre>", "</script>"), ("<!--", "-->"), ("<?target", "?>"),
                                 ("<!A", ">"), ("<![CDATA[", "]]>")):
            source = (f"{opening}\n[hidden]: docs/hidden.md\n\n"
                      f"> - [still-hidden]: docs/hidden-again.md\n{closing}\n[ref]: docs/old.md\n")
            with self.subTest(opening=opening):
                self.assert_target_change(source)

    def test_html_blocks_end_when_their_container_ends(self):
        for opening in ("<pre>", "<!--", "<?target", "<!A", "<![CDATA["):
            for source in (f"> {opening}\n[ref]: docs/old.md\n",
                           f"- {opening}\n[ref]: docs/old.md\n",
                           f"- {opening}\n- [ref]: docs/old.md\n"):
                with self.subTest(source=source):
                    self.assert_target_change(source)
            self.assertEqual(preserve_check.facts(f"{opening}\n\n[ref]: docs/hidden.md\n")["url"], {})

    def test_inline_html_and_other_tags_do_not_end_a_paragraph(self):
        for text in ("Text <!-- note -->", "Text <pre>literal</pre>", "<span>literal</span>",
                     "<prelude>literal</prelude>", "<scripture>literal</scripture>", "<!1literal>",
                     "<!é>", "<ſcript>literal</script>", "<scrİpt>literal</script>",
                     "<![cdata[lower]]>", "A paragraph.\n    <!-- note -->"):
            source = text + "\n[label]: `参考になれば幸いです`\n"
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"参考になれば幸いです": 1})

    def test_html_looking_code_cannot_open_a_block_beyond_the_code(self):
        for opening in ("<pre>", "<!--", "<?target", "<!A", "<![CDATA["):
            for code in (f"```\n{opening}\n```\n", f"    {opening}\n"):
                with self.subTest(code=code):
                    self.assert_target_change(code + "[ref]: docs/old.md\n")

    def test_html_block_start_cannot_be_consumed_as_a_reference_destination(self):
        for html in ("<pre>\nliteral\n</pre>", "<!--note-->", "<?target?>", "<!A>", "<![CDATA[x]]>"):
            with self.subTest(html=html):
                self.assert_target_change(f"[not-a-reference]:\n{html}\n[ref]: docs/old.md\n")

    def test_reference_titles_keep_inline_html_but_stop_at_html_blocks(self):
        for html in ("<span>literal</span>", "<custom>", "Text <!--note-->"):
            with self.subTest(html=html):
                self.assert_target_change(f'[ref]: docs/old.md "title\n{html}\nend"\n')
        self.assertEqual(preserve_check.facts("[ref]:\n<span>\n")["url"], {"span": 1})
        for html in ("<pre>literal</pre>", "<!--note-->", "<?target?>", "<!A>", "<![CDATA[x]]>"):
            with self.subTest(html=html):
                self.assert_target_change(f'[broken]: docs/hidden.md "title\n{html}\n[ref]: docs/old.md\n')

    def test_outer_html_block_keeps_its_blank_line_termination(self):
        for opening in ("<div>", "<custom>"):
            for first, continuation in (("", ""), ("> ", "> "), ("- ", "  ")):
                source = first + opening + "\n" + continuation + "<pre>\n" + continuation + "\n"
                source += continuation + "[ref]: docs/old.md\n"
                with self.subTest(source=source):
                    self.assert_target_change(source)

    def test_outdented_html_blocks_interrupt_lazy_container_paragraphs(self):
        for paragraph in ("> Intro", "- Intro"):
            for opening in ("<pre>", "<!--", "<?target", "<!A", "<![CDATA["):
                with self.subTest(paragraph=paragraph, opening=opening):
                    source = f"{paragraph}\n{opening}\n[hidden]: docs/hidden.md\n"
                    self.assertEqual(preserve_check.facts(source)["url"], {})


    def test_reference_titles_cannot_consume_a_later_heading_or_separator(self):
        for first, continuation in (("", ""), ("> ", "> "), ("- ", "  ")):
            for boundary in ("# Heading", "## Heading", "***", "---", "===", "-", "--"):
                source = (f'{first}[unused]: docs/unused.md "Unfinished title\n'
                          f'{continuation}{boundary}\n{continuation}[ref]: docs/old.md\n'
                          f'{continuation}"\n')
                with self.subTest(source=source):
                    self.assert_target_change(source)

    def test_next_line_destinations_cannot_consume_heading_or_separator_markers(self):
        for boundary in ("#", "##", "***", "---", "===", "--", "-"):
            with self.subTest(boundary=boundary):
                self.assert_target_change(f"[unused]:\n{boundary}\n[ref]: docs/old.md\n")

    def test_nonblock_heading_like_lines_can_continue_a_reference_title(self):
        for line in ("#not-a-heading", "####### heading", "= =", "-- text", "    # Heading", "    ==="):
            with self.subTest(line=line):
                self.assert_target_change(f'[ref]: docs/old.md "Title\n{line}\nends"\n')

    def test_nonblock_fragment_and_marker_destinations_remain_valid(self):
        for target in ("#old-section", "--old-guide.md", "==old-guide.md"):
            with self.subTest(target=target):
                self.assert_target_change(f"[ref]:\n{target}\n", target)


class ReferenceDefinitionContractTests(RunFixture):
    def test_changed_reference_destination_cannot_pass_the_run_contract(self):
        for index, source in enumerate((
                "[guide][ref]\n\n[ref]:\n  docs/old.md\n",
                "> Read [guide][ref].\n>\n> [ref]: docs/old.md\n",
                "- Item\nlazy continuation.\n\n    [ref]: docs/old.md\n\nRead [guide][ref].\n",
                "> - Item\n> lazy continuation.\n>\n>     [ref]: docs/old.md\n\nRead [guide][ref].\n",
                "# Heading\n2. [ref]: docs/old.md\n\nRead [guide][ref].\n",
                "Title\n=====\n[ref]: docs/old.md\n\nRead [guide][ref].\n",
                "> Title\n> =====\n> [ref]: docs/old.md\n\nRead [guide][ref].\n",
                "- Title\n  =====\n  [ref]: docs/old.md\n\nRead [guide][ref].\n",
                "<!-- note -->\n[ref]: docs/old.md\n\nRead [guide][ref].\n",
                "<pre>literal</pre>\n[ref]: docs/old.md\n\nRead [guide][ref].\n",
                '[unused]: docs/unused.md "Title\n# Heading\n[ref]: docs/old.md\n"\n',
                '[unused]: docs/unused.md "Title\n***\n[ref]: docs/old.md\n"\n')):
            with self.subTest(source=source):
                self.out = self.base / f"run-{index}"
                (self.docs / "guide.md").write_text(source, encoding="utf-8")
                self.make_run()
                (self.out / "rewritten/guide.md").write_text(source.replace("old", "new"), encoding="utf-8")
                result = detect.scan_snapshot(self.out, common.load_rules(), [])
                common.write_json(self.out / "detect.after.json", result)
                common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
                findings.render(self.out)
                self.assertEqual(preserve_check.check(self.out)["unacknowledged"], 2)
                problems = contract_check.problems(self.out)
                self.assertEqual(sum("not acknowledged in preservation" in p for p in problems), 2, problems)


if __name__ == "__main__":
    unittest.main()
