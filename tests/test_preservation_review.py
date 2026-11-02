"""Preservation checks reject URL edits and every change to code blocks."""
import subprocess
import sys
import unittest

from test_run_validation import RunFixture

import common
import contract_check
import detect
import findings
import preserve_check


def differences(before, after):
    return preserve_check.compare(preserve_check.facts(before),
                                  preserve_check.facts(after), before)


class BareUrlPreservationTests(unittest.TestCase):
    def test_a_change_after_balanced_parentheses_is_reported(self):
        for path in ("a(b)/old", "a(b(c)d)/old", "a(b)(c)/old"):
            before = "https://example.com/" + path
            after = before.replace("old", "new")
            with self.subTest(path=path):
                self.assertEqual(differences(f"See {before}.\n", f"See {after}.\n"),
                                 [{"kind": "url", "change": "lost", "value": before, "count": 1},
                                  {"kind": "url", "change": "added", "value": after, "count": 1}])

    def test_http_schemes_are_case_insensitive_but_values_stay_exact(self):
        for scheme in ("HTTP", "HTTPS", "HtTpS"):
            for template in ("See {}.\n", "See <{}>.\n"):
                before = scheme + "://example.com/old"
                after = before.replace("old", "new")
                with self.subTest(scheme=scheme, template=template):
                    self.assertEqual(differences(template.format(before), template.format(after)),
                                     [{"kind": "url", "change": "lost", "value": before, "count": 1},
                                      {"kind": "url", "change": "added", "value": after, "count": 1}])

    def test_ipv6_host_brackets_do_not_hide_path_changes(self):
        for authority in ("[::1]", "[2001:db8::1]:8080", "user:pass@[2001:db8::1]"):
            before = "http://" + authority + "/old"
            after = before.replace("old", "new")
            with self.subTest(authority=authority):
                facts = preserve_check.facts(f"[See {before}].\n")
                self.assertEqual(facts["url"], {before: 1})
                self.assertEqual(facts["number"], {})
                self.assertEqual(differences(f"See {before}.\n", f"See {after}.\n"),
                                 [{"kind": "url", "change": "lost", "value": before, "count": 1},
                                  {"kind": "url", "change": "added", "value": after, "count": 1}])

    def test_sentence_delimiters_end_the_url_after_its_own_parentheses(self):
        target = "https://example.com/a(b(c)d)"
        for suffix in (".", ",", ";", ":", ").", ")]", ")300"):
            with self.subTest(suffix=suffix):
                facts = preserve_check.facts(f"See ({target}{suffix}\n")
                self.assertEqual(facts["url"], {target: 1})
                self.assertEqual(facts["number"], {"300": 1} if suffix == ")300" else {})

    def test_unmatched_closer_does_not_swallow_the_next_url(self):
        first, second = "https://example.com/a(b)", "HTTPS://example.com/next"
        self.assertEqual(preserve_check.facts(f"({first}){second}.\n")["url"],
                         {first: 1, second: 1})

    def test_parentheses_cannot_authorize_a_prefix_of_an_existing_url(self):
        before = "See https://example.com/a(b)/private.\n"
        target = "https://example.com/a(b)"
        self.assertEqual(differences(before, before + f"\nSee [guide](<{target}>).\n"),
                         [{"kind": "url", "change": "added", "value": target, "count": 1}])

    def test_a_complete_emphasized_url_with_parentheses_can_be_restated(self):
        for scheme in ("https", "HTTPS"):
            for marker in ("*", "**", "_"):
                target = scheme + "://example.com/a(b(c)d)"
                before = f"See {marker}{target}{marker}.\n"
                with self.subTest(scheme=scheme, marker=marker):
                    self.assertEqual(differences(before, before + f"\nSee [guide](<{target}>).\n"), [])

    def test_deep_parentheses_do_not_require_recursive_matching(self):
        target = "https://example.com/" + "(" * 4000 + "x" + ")" * 4000 + "/guide"
        self.assertEqual(preserve_check.facts(f"See ({target}).\n")["url"], {target: 1})

    def test_unescaped_nested_labels_cannot_create_reference_definitions(self):
        for source in ("[nested[label]: `literal`\n", "> [nested[label]: `literal`\n",
                       "- [nested[label]: `literal`\n"):
            with self.subTest(source=source):
                facts = preserve_check.facts(source)
                self.assertEqual(facts["url"], {})
                self.assertEqual(facts["inline_code"], {"literal": 1})
        source = "[nested\\[label]: docs/guide.md\n"
        self.assertEqual(preserve_check.facts(source)["url"], {"docs/guide.md": 1})


class CodeBlockMultiplicityTests(unittest.TestCase):
    block = "```sh\nprintf stable\n```\n"

    def test_removing_or_adding_a_repeated_code_block_is_reported(self):
        single = self.block
        repeated = "\n".join([single] * 3)
        value = next(iter(preserve_check.facts(single)["code_block"]))
        self.assertEqual(differences(repeated, single),
                         [{"kind": "code_block", "change": "lost", "value": value, "count": 2}])
        self.assertEqual(differences(single, repeated),
                         [{"kind": "code_block", "change": "added", "value": value, "count": 2}])

    def test_unchanged_code_and_repeated_prose_facts_keep_the_existing_policy(self):
        text = "Use `value` 300 times. See https://example.com/guide.[^ref]\n"
        self.assertEqual(differences(self.block + text * 3, self.block + text), [])
        self.assertEqual(differences(self.block * 2, self.block * 2), [])


class PreservationCommandTests(RunFixture):
    def test_code_changes_cannot_be_acknowledged_in_legacy_runs(self):
        original = "```sh\nprintf old\n```\n"
        (self.docs / "guide.md").write_text(original, encoding="utf-8")
        self.make_run()
        for rewritten in (original.replace("old", "new"), original + "\n" + original, "Removed.\n"):
            with self.subTest(rewritten=rewritten):
                (self.out / "rewritten/guide.md").write_text(rewritten, encoding="utf-8")
                record = common.load_json(self.record)
                record["preservation"] = [
                    {"path": "guide.md", "kind": diff["kind"], "value": diff["value"],
                     "reason": "Attempt to approve a code edit."}
                    for diff in differences(original, rewritten)
                ]
                common.write_json(self.record, record)
                result = preserve_check.check(self.out)
                self.assertGreater(result["unacknowledged"], 0)
                self.assertTrue(all(not diff["acknowledged"] for diff in result["files"][0]["diffs"]))
                command = subprocess.run([sys.executable, preserve_check.__file__, str(self.out)],
                                         capture_output=True, text=True, timeout=10)
                self.assertEqual(command.returncode, 1, command.stderr)
                self.assertNotIn("Traceback", command.stderr)
                common.write_json(self.out / "detect.after.json",
                                  detect.scan_snapshot(self.out, common.load_rules(), []))
                findings.render(self.out)
                self.assertTrue(any("code_block" in problem for problem in contract_check.problems(self.out)))

    def test_changed_bare_urls_fail_the_run_contract(self):
        original = "See HTTPS://example.com/a(b)/old.\n"
        (self.docs / "guide.md").write_text(original, encoding="utf-8")
        self.make_run()
        (self.out / "rewritten/guide.md").write_text(original.replace("old", "new"), encoding="utf-8")
        result = preserve_check.check(self.out)
        self.assertEqual(result["unacknowledged"], 2)
        common.write_json(self.out / "preserve.json", result)
        common.write_json(self.out / "detect.after.json",
                          detect.scan_snapshot(self.out, common.load_rules(), []))
        findings.render(self.out)
        problems = contract_check.problems(self.out)
        self.assertEqual(sum("not acknowledged in preservation" in problem for problem in problems), 2)

    def test_an_unwritable_output_is_a_usage_error_without_a_traceback(self):
        self.make_run()
        command = subprocess.run([sys.executable, preserve_check.__file__, str(self.out),
                                  "--out", str(self.out)], capture_output=True, text=True, timeout=10)
        self.assertEqual(command.returncode, 2, command.stderr)
        self.assertIn("error:", command.stderr)
        self.assertNotIn("Traceback", command.stderr)


if __name__ == "__main__":
    unittest.main()
