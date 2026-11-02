"""Footnote references and definitions keep their Markdown roles."""
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


def changes(before, after):
    return {(d["change"], d["kind"], d["value"], d.get("role"))
            for d in preserve_check.compare(preserve_check.facts(before),
                                            preserve_check.facts(after), before)}


class FootnoteBoundaryTests(unittest.TestCase):
    def test_a_colon_in_prose_does_not_turn_a_reference_into_a_definition(self):
        for newline in ("\n", "\r\n"):
            for prefix in ("", "> ", "- "):
                before = (f"{prefix}Cache behavior[^ref]: entries expire.{newline}{newline}"
                          f"[^ref]: Source.{newline}")
                after = before.replace("behavior[^ref]", "behavior")
                with self.subTest(newline=newline, prefix=prefix):
                    self.assertEqual(changes(before, after),
                                     {("lost", "footnote", "[^ref]", None)})

    def test_escaped_references_are_literal_but_even_backslashes_keep_the_reference(self):
        for slashes in range(5):
            source = "Claim." + "\\" * slashes + "[^ref]\n\n[^ref]: Source.\n"
            with self.subTest(slashes=slashes):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote"], {} if slashes % 2 else {"[^ref]": 1})
                self.assertEqual(facts["footnote_definition"], {"[^ref]": 1})

    def test_escaping_a_reference_or_definition_reports_the_lost_role(self):
        source = "Claim.[^ref]\n\n[^ref]: Source.\n"
        for changed, role in ((source.replace("Claim.[", "Claim.\\["), None),
                              (source.replace("\n[^ref]", "\n\\[^ref]"), "definition")):
            with self.subTest(changed=changed):
                self.assertEqual(changes(source, changed),
                                 {("lost", "footnote", "[^ref]", role)})

    def test_a_literal_backslash_before_a_label_does_not_open_a_definition(self):
        for slashes in range(1, 5):
            source = "\\" * slashes + "[^ref]: Source.\n"
            with self.subTest(slashes=slashes):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["footnote"], {} if slashes % 2 else {"[^ref]": 1})

    def test_definition_starts_follow_existing_list_and_quote_containers(self):
        for newline in ("\n", "\r\n"):
            for source in (
                "[^ref]: Source.\n", "   [^ref]: Source.\n",
                "> [^ref]: Source.\n", "> > [^ref]: Source.\n",
                "- [^ref]: Source.\n", "10. [^ref]: Source.\n",
                "> - [^ref]: Source.\n", "- > [^ref]: Source.\n",
                "- Entry.\n\n  [^ref]: Source.\n",
                "10. Entry.\n\n    [^ref]: Source.\n",
                "> - Entry.\n>\n>   [^ref]: Source.\n",
                "- - Entry.\n\n    [^ref]: Source.\n",
            ):
                source = source.replace("\n", newline)
                with self.subTest(source=source):
                    facts = preserve_check.facts(source)
                    self.assertEqual(facts["footnote_definition"], {"[^ref]": 1})
                    self.assertEqual(facts["footnote"], {})

    def test_footnote_definitions_can_interrupt_prose_and_follow_each_other(self):
        for source in ("Claim.[^one]\n[^one]: Source.\n[^two]: Another source.\n",
                       "> Claim.[^one]\n> [^one]: Source.\n> [^two]: Another source.\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {"[^one]": 1, "[^two]": 1})
                self.assertEqual(facts["footnote"], {"[^one]": 1})

    def test_heading_content_and_incomplete_ordered_markers_are_not_definition_starts(self):
        for source in ("# [^ref]: Heading.\n", "Intro [^ref]: text.\n",
                       "A paragraph.\n2. [^ref]: continuation.\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["footnote"], {"[^ref]": 1})

    def test_code_and_link_destinations_do_not_supply_footnotes(self):
        for source in ("`[^ref]: code`\n", "```\n[^ref]: code\n```\n",
                       "> ```\n> [^ref]: code\n> ```\n", "    [^ref]: code\n",
                       "- Entry.\n\n      [^ref]: code\n",
                       "[guide](docs/[^ref]:target)\n", "<https://example.com/[^ref]>\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["footnote"], {})

    def test_masked_inline_spans_cannot_create_a_definition_start(self):
        for source in ("`x`[^ref]: text.\n", "<https://example.com>[^ref]: text.\n",
                       "> `x`[^ref]: text.\n", "[link](docs/guide)[^ref]: text.\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["footnote"], {"[^ref]": 1})

    def test_a_url_before_a_definition_does_not_shift_its_source_position(self):
        source = "See https://example.com/guide.\n\n[^ref]: Source.\n"
        self.assertEqual(preserve_check.facts(source)["footnote_definition"], {"[^ref]": 1})

    def test_link_definitions_commit_their_boundaries_before_footnote_definitions(self):
        for source in ('[link]: docs/guide\n2. [^ref]: Source.\n',
                       '[link]: docs/guide "Title\n[^title]: literal\nends"\n[^ref]: Source.\n'):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {"[^ref]": 1})
                self.assertEqual(facts["footnote"], {})

    def test_html_block_bodies_cannot_open_footnote_definitions(self):
        for source in ("<!--\n[^literal]: text\n-->\n[^ref]: Source.\n",
                       "> <pre>\n> [^literal]: text\n> </pre>\n> [^ref]: Source.\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote_definition"], {"[^ref]": 1})
                self.assertEqual(facts["footnote"], {})

    def test_html_blocks_do_not_supply_references_without_a_definition(self):
        for source in ("<!-- Claim.[^ref] -->\n", "<pre>Claim.[^ref]</pre>\n",
                       "> <div>\n> Claim.[^ref]\n> </div>\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote"], {})
                self.assertEqual(facts["footnote_definition"], {})

    def test_inline_html_syntax_does_not_supply_footnotes_but_keeps_numbers(self):
        for literal in ('<span title="[^ref]: hint 37">text</span>',
                        "<span title='[^ref]: hint 37'>text</span>",
                        '<span data-note=[^ref]: data-count=37 />',
                        '<!-- [^ref]: comment 37 -->',
                        '<?instruction [^ref]: text 37 ?>',
                        '<!DECL [^ref]: text 37>',
                        '<![CDATA[[^ref]: text 37]]>'):
            with self.subTest(literal=literal):
                facts = preserve_check.facts(f"Use {literal} here.\n")
                self.assertEqual(facts["footnote"], {})
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["number"], {"37": 1})

    def test_text_between_inline_html_tags_keeps_its_references(self):
        source = 'Use <span title="[^literal]: hint">Claim.[^ref]</span>.\n'
        self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})

    def test_html_looking_text_inside_a_footnote_label_stays_in_the_label(self):
        for label in ("ref<i>", "ref<a>", "ref<!--x-->", "ref<?x?>"):
            marker = f"[^{label}]"
            source = f"Claim.{marker}\n\n{marker}: Source.\n"
            with self.subTest(label=label):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["footnote"], {marker: 1})
                self.assertEqual(facts["footnote_definition"], {marker: 1})
                self.assertEqual(changes(source, source.replace(f"Claim.{marker}", "Claim.")),
                                 {("lost", "footnote", marker, None)})
                self.assertEqual(changes(source, source.replace(f"\n{marker}: Source.\n", "\n")),
                                 {("lost", "footnote", marker, "definition")})

    def test_html_starting_outside_a_footnote_label_still_takes_precedence(self):
        for literal in ('<span title="[^ref<i>]: hint 37">text</span>',
                        '<!-- [^ref<i>]: hint 37 -->'):
            with self.subTest(literal=literal):
                facts = preserve_check.facts(f"Use {literal} here. Claim.[^real]\n")
                self.assertEqual(facts["footnote"], {"[^real]": 1})
                self.assertEqual(facts["footnote_definition"], {})
                self.assertEqual(facts["number"], {"37": 1})

    def test_wrapped_inline_html_respects_quote_continuations(self):
        for newline in ("\n", "\r\n"):
            source = ('> Use <span\n> title="[^literal]: hint">Claim.[^ref]</span>.\n'
                      .replace("\n", newline))
            with self.subTest(newline=newline):
                self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})

    def test_incomplete_malformed_and_escaped_inline_html_remains_prose(self):
        for source in ('Use <span title="[^ref]: missing end.\n',
                       'Use <span bad@name="[^ref]">text</span>.\n',
                       'Use <33 title="[^ref]">text</33>.\n',
                       'Use <span title=[^ref] other= >text</span>.\n',
                       'Use \\<span title="[^ref]: hint">text</span>.\n',
                       'Use \\<!-- [^ref] --> here.\n',
                       'Use ' + '<!-- ' * 2000 + 'Claim.[^ref] >.\n'):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})
        self.assertEqual(preserve_check.facts('Use \\\\<span title="[^ref]: hint">text</span>.\n')["footnote"], {})

    def test_inline_html_cannot_start_inside_code_urls_or_link_titles(self):
        for source in ('Use `<span title="` then Claim.[^ref] ">.\n',
                       'Use `<!--` then Claim.[^ref] -->.\n',
                       'See https://example.com/<span title=" then Claim.[^ref] ">.\n',
                       '[guide](docs/guide \'<span title="\') then Claim.[^ref] ">.\n',
                       '[guide](docs/guide "<!--") then Claim.[^ref] -->.\n'):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})

    def test_incomplete_inline_html_cannot_cross_paragraph_or_heading_boundaries(self):
        for source in ('Use <span title="missing end.\n\nClaim.[^ref] ">.\n',
                       'Use <span title="missing end.\n# Claim.[^ref]\n">.\n',
                       'Use <!-- missing end.\n\nClaim.[^ref] -->.\n',
                       'Use <!-- missing end.\n# Claim.[^ref]\n-->.\n'):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})

    def test_link_titles_cannot_supply_either_footnote_role_but_keep_numbers(self):
        for newline in ("\n", "\r\n"):
            for prefix in ("", "> "):
                for opening, closing in (('[guide](docs/guide "', '")'),
                                         ('[guide]: docs/guide "', '"')):
                    source = (prefix + opening + "Edition 2[^ref]\n"
                              + prefix + "[^ref]: title text\n" + prefix + closing + "\n")
                    source = source.replace("\n", newline)
                    with self.subTest(source=source):
                        facts = preserve_check.facts(source)
                        self.assertEqual(facts["footnote"], {})
                        self.assertEqual(facts["footnote_definition"], {})
                        self.assertEqual(facts["number"], {"2": 1})

    def test_incomplete_links_leave_their_footnote_references_as_prose(self):
        for source in ('[guide](docs/guide "Title[^ref]\n',
                       '[guide]: docs/guide "Title[^ref]\n'):
            with self.subTest(source=source):
                self.assertEqual(preserve_check.facts(source)["footnote"], {"[^ref]": 1})

    def test_only_actual_footnote_labels_are_excluded_from_numeric_facts(self):
        self.assertEqual(preserve_check.facts("Claim.[^17]\n\n[^17]: Source.\n")["number"], {})
        self.assertEqual(preserve_check.facts(r"The literal marker is \[^17]." + "\n")["number"],
                         {"17": 1})


class FootnoteContractTests(RunFixture):
    def test_html_looking_labels_cannot_hide_a_lost_role_with_a_fresh_report(self):
        for index, label in enumerate(("ref<i>", "ref<!--x-->")):
            marker = f"[^{label}]"
            source = f"Claim.{marker}\n\n{marker}: Source.\n"
            for role in (None, "definition"):
                with self.subTest(label=label, role=role):
                    self.out = self.base / f"label-{index}-{role}"
                    (self.docs / "guide.md").write_text(source, encoding="utf-8")
                    self.make_run()
                    after = (source.replace(f"Claim.{marker}", "Claim.") if role is None else
                             source.replace(f"\n{marker}: Source.\n", "\n"))
                    (self.out / "rewritten" / "guide.md").write_text(after, encoding="utf-8")
                    common.write_json(self.out / "detect.after.json",
                                      detect.scan_snapshot(self.out, common.load_rules(), []))
                    common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
                    findings.render(self.out)
                    role_text = " definition" if role else ""
                    self.assertEqual(contract_check.problems(self.out),
                                     [f"guide.md: lost footnote{role_text} '{marker}' not acknowledged in preservation"])

    def test_lost_footnote_roles_fail_a_fresh_report_until_acknowledged(self):
        ordinary = "Cache entries expire.[^ref]\n\n[^ref]: Source.\n"
        colon = "Cache behavior[^ref]: entries expire.\n\n[^ref]: Source.\n"
        cases = ((colon, colon.replace("behavior[^ref]", "behavior"), None),
                 (ordinary, ordinary.replace("expire.[", "expire.\\["), None),
                 (ordinary, ordinary.replace("\n[^ref]", "\n\\[^ref]"), "definition"),
                 (ordinary, ordinary.replace("\n[^ref]", "\nSource [^ref]"), "definition"))
        for index, (before, after, role) in enumerate(cases):
            with self.subTest(after=after):
                self.out = self.base / f"run-{index}"
                (self.docs / "guide.md").write_text(before, encoding="utf-8")
                self.make_run()
                (self.out / "rewritten" / "guide.md").write_text(after, encoding="utf-8")
                common.write_json(self.out / "detect.after.json",
                                  detect.scan_snapshot(self.out, common.load_rules(), []))
                result = preserve_check.check(self.out)
                common.write_json(self.out / "preserve.json", result)
                findings.render(self.out)
                self.assertEqual(result["unacknowledged"], 1)
                self.assertEqual(result["files"][0]["diffs"][0].get("role"), role)
                role_text = " definition" if role else ""
                self.assertEqual(contract_check.problems(self.out),
                                 [f"guide.md: lost footnote{role_text} '[^ref]' not acknowledged in preservation"])
                record = common.load_json(self.record)
                record["preservation"] = [{"path": "guide.md", "kind": "footnote", "value": "[^ref]",
                                           "reason": "The author explicitly removed this citation."}]
                common.write_json(self.record, record)
                common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
                findings.render(self.out)
                self.assertEqual(contract_check.problems(self.out), [])

    def test_literal_labels_cannot_hide_a_lost_role_with_a_fresh_report(self):
        literals = ("<!--\n[^ref]: This is only a comment.\n-->\n",
                    "<pre>\n[^ref]: This is only literal text.\n</pre>\n",
                    'Use <span title="[^ref]: hint">this label</span>.\n',
                    'Use <!-- [^ref]: a comment --> this label.\n',
                    '[link]: docs/guide "Title\n[^ref]: title text\nends"\n',
                    '[guide](docs/guide "Title\n[^ref]: title text\nends")\n')
        for index, literal in enumerate(literals):
            source = literal + "\nClaim.[^ref]\n\n[^ref]: Source.\n"
            for role in (None, "definition"):
                with self.subTest(literal=literal, role=role):
                    self.out = self.base / f"literal-{index}-{role}"
                    (self.docs / "guide.md").write_text(source, encoding="utf-8")
                    self.make_run()
                    after = (source.replace("Claim.[^ref]", "Claim.") if role is None else
                             source.replace("\n[^ref]: Source.\n", "\n"))
                    (self.out / "rewritten" / "guide.md").write_text(after, encoding="utf-8")
                    common.write_json(self.out / "detect.after.json",
                                      detect.scan_snapshot(self.out, common.load_rules(), []))
                    result = preserve_check.check(self.out)
                    common.write_json(self.out / "preserve.json", result)
                    findings.render(self.out)
                    self.assertEqual(result["unacknowledged"], 1)
                    self.assertEqual(result["files"][0]["diffs"][0].get("role"), role)
                    role_text = " definition" if role else ""
                    self.assertEqual(contract_check.problems(self.out),
                                     [f"guide.md: lost footnote{role_text} '[^ref]' not acknowledged in preservation"])


if __name__ == "__main__":
    unittest.main()
