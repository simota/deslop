"""Original-hit accounting must honor the same exemptions as detection."""
import contextlib
import io
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "deslop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import contract_check  # noqa: E402
import detect  # noqa: E402
import findings  # noqa: E402
import preserve_check  # noqa: E402
import snapshot  # noqa: E402
from test_run_validation import RunFixture  # noqa: E402


class ExemptionAccountingTests(RunFixture):
    def check_run(self, before, after, exemptions=(), changes=(), genre="general"):
        self.out = self.base / f"run-{len(list(self.base.glob('run-*')))}"
        (self.docs / "guide.md").write_text(before, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snapshot.main([
                str(self.out), "--root", str(self.docs), "--copy", "--genre", genre, str(self.docs),
            ]), 0)
        data = {
            "schema_version": 1,
            "meta": {"target": str(self.docs), "lang": "en", "mode": "copy",
                     "assessor": "test", "date": "2026-10-31"},
            "voice": {"source": "inferred", "rules": ["Use direct statements."]},
            "perspectives": [{"id": p["id"], "result": "applied", "note": "Read."}
                             for p in common.load_rules()["perspectives"]],
            "findings": list(changes),
            "exemptions": list(exemptions),
        }
        common.write_json(self.out / "findings.json", data)
        rules = common.load_rules()
        common.write_json(self.out / "detect.before.json",
                          detect.scan_snapshot(self.out, rules, [], originals=True))
        (self.out / "rewritten" / "guide.md").write_text(after, encoding="utf-8")
        common.write_json(self.out / "detect.after.json", detect.scan_snapshot(self.out, rules, exemptions))
        common.write_json(self.out / "preserve.json", preserve_check.check(self.out))
        findings.render(self.out)
        return contract_check.problems(self.out)

    def regression_exemption(self):
        return {"path": "guide.md", "rule": "EN-04", "text": "robust regression", "reason": "Term of art."}

    def regression_finding(self):
        return {"id": "T-002", "path": "guide.md", "rule": "EN-04", "occurrences": 1,
                "action": "exempted", "before": "robust regression", "reason": "Term of art."}

    def test_scoped_exemption_does_not_account_for_another_deleted_occurrence(self):
        for gap in (" ", "\n\n"):
            with self.subTest(gap=gap):
                problems = self.check_run(
                    f"A robust cache.{gap}Use robust regression.\n",
                    f"A cache.{gap}Use robust regression.\n", [self.regression_exemption()])
                self.assertEqual(problems, ["before-hit guide.md:1 EN-04 has no finding or exemption"])

    def test_nonmatching_scoped_exemption_does_not_account_for_a_deleted_hit(self):
        problems = self.check_run("A robust cache.\n", "A cache.\n", [self.regression_exemption()])
        self.assertEqual(problems, ["before-hit guide.md:1 EN-04 has no finding or exemption"])

    def test_a_finding_accounts_for_the_deleted_unexempted_occurrence(self):
        change = {"id": "T-001", "path": "guide.md", "rule": "EN-04", "occurrences": 1,
                  "action": "rewritten", "before": "A robust cache.", "after": "A cache."}
        self.assertEqual(self.check_run(
            "A robust cache.\n\nUse robust regression.\n",
            "A cache.\n\nUse robust regression.\n", [self.regression_exemption()], [change]), [])

    def test_exempted_finding_does_not_account_for_another_deleted_occurrence(self):
        problems = self.check_run(
            "A robust cache.\n\nUse robust regression.\n",
            "A cache.\n\nUse robust regression.\n", [self.regression_exemption()], [self.regression_finding()])
        self.assertEqual(problems, ["before-hit guide.md:1 EN-04 has no finding or exemption"])

    def test_exempted_findings_still_work_with_matching_exemptions(self):
        source = "Use robust regression.\n"
        self.assertEqual(self.check_run(source, source, [self.regression_exemption()], [self.regression_finding()]), [])
        change = {"id": "T-001", "path": "guide.md", "rule": "EN-04", "occurrences": 1,
                  "action": "rewritten", "before": "A robust cache.", "after": "A cache."}
        self.assertEqual(self.check_run(
            "A robust cache.\n\nUse robust regression.\n",
            "A cache.\n\nUse robust regression.\n", [self.regression_exemption()],
            [self.regression_finding(), change]), [])

    def test_scoped_exemption_accounts_for_its_original_occurrence(self):
        source = "Use robust regression.\n"
        self.assertEqual(self.check_run(source, source, [self.regression_exemption()]), [])

    def test_file_wide_lexical_exemption_still_accounts_for_every_occurrence(self):
        exemption = {"path": "guide.md", "rule": "EN-04", "reason": "Retained quoted wording."}
        source = '> "A robust cache. Use robust regression."\n'
        self.assertEqual(self.check_run(source, source, [exemption]), [])

    def test_original_hit_still_present_after_rewrite_is_open(self):
        source = "A robust cache.\n\nUse robust regression.\n"
        problems = self.check_run(source, source, [self.regression_exemption()])
        self.assertTrue(any(p.startswith("open hit guide.md:1 EN-04") for p in problems), problems)

    def test_new_unexempted_hit_after_rewrite_is_open(self):
        problems = self.check_run("Use robust regression.\n",
                                  "Use robust regression.\n\nA robust cache.\n", [self.regression_exemption()])
        self.assertTrue(any(p.startswith("open hit guide.md:3 EN-04") for p in problems), problems)
        self.assertFalse(any(p.startswith("before-hit") for p in problems), problems)

    def test_artifact_exemption_does_not_account_for_unquoted_originals(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                exemption = {"path": "guide.md", "rule": "ART-03", "reason": "Quoted reply."}
                if scoped:
                    exemption["text"] = "I hope this helps"
                problems = self.check_run("I hope this helps.\n\n> I hope this helps.\n",
                                          "> I hope this helps.\n", [exemption])
                self.assertEqual(problems, ["before-hit guide.md:1 ART-03 has no finding or exemption"])

    def test_artifact_exemption_accounts_for_quoted_originals(self):
        exemption = {"path": "guide.md", "rule": "ART-03", "text": "I hope this helps", "reason": "Quoted reply."}
        source = "> I hope this helps.\n"
        self.assertEqual(self.check_run(source, source, [exemption]), [])

    def test_new_unquoted_artifact_is_open_even_with_file_wide_exemption(self):
        exemption = {"path": "guide.md", "rule": "ART-03", "reason": "Quoted reply."}
        problems = self.check_run("> I hope this helps.\n", "> I hope this helps.\n\nI hope this helps.\n", [exemption])
        self.assertTrue(any(p.startswith("open hit guide.md:3 ART-03") for p in problems), problems)

    def test_genre_exempt_originals_still_need_no_finding(self):
        source = "Let me know if you have any questions.\n"
        for after in (source, "Please reply by email.\n"):
            with self.subTest(after=after):
                self.assertEqual(self.check_run(source, after, genre="message"), [])

    def test_scoped_exemption_can_surround_a_multiline_hit(self):
        passage = "The editor marks errors,\n  highlighting the failed token in blue."
        exemption = {"path": "guide.md", "rule": "EN-21", "text": passage,
                     "reason": "Describes the visible editor behavior."}
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=newline):
                source = ("Editor behavior.\n\n" + passage + "\n").replace("\n", newline)
                self.assertEqual(self.check_run(source, source, [exemption]), [])

    def test_scoped_exemption_can_start_before_the_hits_line(self):
        passage = "Use the estimator for\nrobust regression on these rows."
        exemption = {"path": "guide.md", "rule": "EN-04", "text": passage,
                     "reason": "Identifies the statistical method."}
        source = "Estimator settings.\n\n" + passage + "\n"
        self.assertEqual(self.check_run(source, source, [exemption]), [])

    def test_multiline_exemption_does_not_cover_another_occurrence(self):
        passage = "The editor marks errors,\n  highlighting the failed token in blue."
        exemption = {"path": "guide.md", "rule": "EN-21", "text": passage,
                     "reason": "Describes the visible editor behavior."}
        other = "The release landed,\n  highlighting the team's progress."
        for source in (passage + "\n\n" + other + "\n", other + "\n\n" + passage + "\n"):
            with self.subTest(source=source):
                problems = self.check_run(source, source, [exemption])
                line = 4 if source.startswith(passage) else 1
                self.assertEqual(len(problems), 2, problems)
                self.assertTrue(problems[0].startswith(f"open hit guide.md:{line} EN-21"), problems)
                self.assertEqual(problems[1], f"before-hit guide.md:{line} EN-21 has no finding or exemption")

    def test_multiline_exemption_does_not_account_for_another_deleted_hit(self):
        passage = "The editor marks errors,\n  highlighting the failed token in blue."
        exemption = {"path": "guide.md", "rule": "EN-21", "text": passage,
                     "reason": "Describes the visible editor behavior."}
        source = passage + "\n\nThe release landed,\n  highlighting the team's progress.\n"
        self.assertEqual(self.check_run(source, passage + "\n", [exemption]),
                         ["before-hit guide.md:4 EN-21 has no finding or exemption"])

    def test_multiline_context_does_not_relax_artifact_quote_restriction(self):
        for quoted in (True, False):
            with self.subTest(quoted=quoted):
                passage = ("> Transcript:\n> I hope this helps." if quoted
                           else "Closing comment:\nI hope this helps.")
                exemption = {"path": "guide.md", "rule": "ART-03", "text": passage,
                             "reason": "Retained transcript wording."}
                problems = self.check_run(passage + "\n", passage + "\n", [exemption])
                if quoted:
                    self.assertEqual(problems, [])
                else:
                    self.assertEqual(len(problems), 2, problems)
                    self.assertTrue(problems[0].startswith("open hit guide.md:2 ART-03"), problems)
                    self.assertEqual(problems[1], "before-hit guide.md:2 ART-03 has no finding or exemption")

    def test_exemption_can_still_name_part_of_a_multiline_hit(self):
        source = "The editor marks errors,\n  highlighting the failed token in blue.\n"
        exemption = {"path": "guide.md", "rule": "EN-21", "text": ",\n  highlighting",
                     "reason": "Describes the visible editor behavior."}
        self.assertEqual(self.check_run(source, source, [exemption]), [])


if __name__ == "__main__":
    unittest.main()
