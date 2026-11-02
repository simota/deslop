"""Reports must keep complete identifying values and render record text literally."""
import unittest

from test_run_validation import RunFixture

import common
import comparison
import findings


class ReportIntegrityTests(RunFixture):
    def test_long_paths_values_and_reasons_are_not_truncated(self):
        name = "cache-configuration-" + "reference-" * 6 + "guide.md"
        (self.docs / "guide.md").rename(self.docs / name)
        self.make_run()
        data = common.load_json(self.record)
        reason = "Keep this documented value because " + "the source requires it; " * 8 + "do not change its unit."
        value = "https://example.com/" + "nested/" * 12 + "reference"
        before = "The original explanation " + "contains a required condition; " * 4
        after = "The revised explanation " + "retains the same required condition; " * 4
        data["findings"] = [{"id": "T-001", "path": name, "rule": "STR-01", "occurrences": 1,
                             "action": "rewritten", "before": before, "after": after}]
        data["preservation"] = [{"path": name, "kind": "url", "value": value, "reason": reason}]
        data["exemptions"] = [{"path": name, "rule": "EN-04", "text": before, "reason": reason}]
        data["perspectives"][0]["note"] = reason
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                data["meta"]["lang"] = lang
                common.write_json(self.record, data)
                report, _ = findings.build_report(self.out)
                for text in (name, value, reason, before.strip(), after.strip()):
                    self.assertIn(text, report)

    def test_record_text_cannot_create_report_markup(self):
        self.make_run()
        data = common.load_json(self.record)
        sample = "<details> [label](https://example.com) `code` | *emphasis* & value"
        data["meta"]["target"] = sample
        data["meta"]["assessor"] = sample
        data["meta"]["date"] = "today\n\n## Forged heading"
        data["voice"]["rules"] = [sample]
        data["limitations"] = [sample]
        data["decisions"] = [sample]
        data["perspectives"][0]["note"] = sample
        common.write_json(self.record, data)
        report, _ = findings.build_report(self.out)
        target = f"- target: {common.markdown_code(sample)} (copy)"
        self.assertIn(target, report)
        prose = report.replace(target, "")
        self.assertNotIn("<details>", prose)
        self.assertNotIn("[label](https://example.com)", prose)
        self.assertNotIn("\n## Forged heading", report)
        escaped = "&lt;details&gt; \\[label\\](https://example.com) \\`code\\` \\| \\*emphasis\\* &amp; value"
        self.assertEqual(prose.count(escaped), 5)

    def test_code_identifiers_preserve_whitespace_and_literal_delimiters(self):
        cases = (
            ("guide.md", "`guide.md`"),
            ("two  spaces.md", "`two  spaces.md`"),
            (" leading.md", "`  leading.md `"),
            ("trailing.md ", "` trailing.md  `"),
            (" both.md ", "`  both.md  `"),
            ("  ", "`  `"),
            ("`quoted`.md", "`` `quoted`.md ``"),
            ("ticks``.md", "```ticks``.md```"),
            ("pipe|name.md", r"`pipe`\|`name.md`"),
            ("pipe | name.md", r"` pipe  `\|`  name.md `"),
            (r"slash\|name.md", r"`slash\`\|`name.md`"),
            ("line\nname.md", r'`"line\nname.md"`'),
            ("tab\tname.md", r'`"tab\tname.md"`'),
            ('"line\\nname.md"', r'`"\"line\\nname.md\""`'),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(common.markdown_code(value), expected)

    def test_different_path_whitespace_remains_distinct_in_the_report(self):
        (self.docs / "guide.md").rename(self.docs / "two  spaces.md")
        (self.docs / "two spaces.md").write_text("Other notes.\n", encoding="utf-8")
        self.make_run()
        report, _ = findings.build_report(self.out)
        for path in ("two  spaces.md", "two spaces.md"):
            with self.subTest(path=path):
                self.assertEqual(report.count(f"| `{path}` |"), 1)

    def test_comparison_headings_keep_distinct_document_paths(self):
        reviews = []
        for path in ("two  spaces.md", "two spaces.md"):
            candidates = [{"id": identity, "sha256": "0" * 64, "eligible": True,
                           "approach": "Keep the information order.", "strengths": "Facts remain.",
                           "weaknesses": "The ending repeats a point.", "review_note": "Read the full text.",
                           "scores": {key: {"score": limit, "reason": "Checked this criterion."}
                                      for key, limit in comparison.SCORE_LIMITS.items()}}
                          for identity in comparison.CANDIDATE_IDS]
            reviews.append({"path": path, "candidates": candidates, "selected": "A",
                            "reason": "The candidates are tied.", "final_sha256": "0" * 64})
        report = "\n".join(comparison.report_lines(self.out, {"comparisons": reviews}, "en"))
        for path in ("two  spaces.md", "two spaces.md"):
            self.assertEqual(report.count(f"### `{path}`\n"), 1)

    def test_protected_values_keep_significant_whitespace(self):
        self.make_run()
        data = common.load_json(self.record)
        data["preservation"] = [{"path": "guide.md", "kind": "inline_code", "value": value,
                                  "reason": "Reviewed the exact literal."}
                                 for value in ("two  spaces", "two spaces")]
        common.write_json(self.record, data)
        report, _ = findings.build_report(self.out)
        for value in ("two  spaces", "two spaces"):
            self.assertEqual(report.count(f"| inline_code | `{value}` |"), 1)

    def test_list_fields_keep_leading_list_and_separator_markers_literal(self):
        self.make_run()
        data = common.load_json(self.record)
        cases = (
            ("---", r"\---"),
            ("--", r"\--"),
            ("- -", r"\- -"),
            ("- Preserve this literal dash.", r"\- Preserve this literal dash."),
            ("+ Preserve this literal plus.", r"\+ Preserve this literal plus."),
            ("1. Keep this item number.", r"1\. Keep this item number."),
            ("2) Keep this item number.", r"2\) Keep this item number."),
            ("1.5 seconds remains a decimal.", "1.5 seconds remains a decimal."),
            ("-f remains an option.", "-f remains an option."),
        )
        for items in (data["voice"]["rules"], data.setdefault("limitations", []),
                      data.setdefault("decisions", [])):
            items[:] = [source for source, _ in cases]
        common.write_json(self.record, data)
        report, _ = findings.build_report(self.out)
        for source, escaped in cases:
            with self.subTest(source=source):
                self.assertEqual(report.count(f"\n- {escaped}\n"), 3)


if __name__ == "__main__":
    unittest.main()
