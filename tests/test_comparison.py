"""Three rewrites must be reviewed on their current text before selection."""
import contextlib
import copy
import io
import shutil
import unittest

from test_run_validation import RunFixture

import common
import comparison
import contract_check
import findings
import snapshot


LIMITS = {"fidelity": 30, "structure": 25, "clarity": 20, "voice": 15, "concision": 10}
ORIGINAL = "Cache entries expire after 30 seconds.\nRead fresh values after expiry.\n"
DRAFTS = {
    "A": "Cache entries expire after 30 seconds.\nAfter expiry, read fresh values.\n",
    "B": "After 30 seconds, cache entries expire.\nRead fresh values after expiry.\n",
    "C": "Read fresh values after expiry.\nCache entries expire after 30 seconds.\n",
    "merged": "After expiry, read fresh values.\nCache entries expire after 30 seconds.\n",
}


class ComparisonTests(RunFixture):
    def setUp(self):
        super().setUp()
        (self.docs / "guide.md").write_text(ORIGINAL, encoding="utf-8")

    def candidate(self, identity, text=None, penalty=2):
        text = DRAFTS[identity] if text is None else text
        path = self.out / "candidates" / identity / "guide.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        scores = {key: {"score": limit, "reason": f"Reviewed {key} against the source."}
                  for key, limit in LIMITS.items()}
        scores["structure"]["score"] -= penalty
        return {
            "id": identity, "approach": f"Information order used by {identity}.",
            "sha256": common.sha256_file(path), "eligible": True, "scores": scores,
            "strengths": "The expiry condition stays next to the required action.",
            "weaknesses": "The transition can be shorter.",
            "review_note": "Checked meaning, the expiry condition and the reader's action.",
        }

    def mark_comparison_workflow(self):
        snap = common.load_json(self.out / "snapshot.json")
        snap["workflow"] = "compare-three"
        common.write_json(self.out / "snapshot.json", snap)

    def make_comparison(self):
        self.make_run()
        self.mark_comparison_workflow()
        comparison.init(self.out)
        self.entry = {
            "path": "guide.md",
            "candidates": [self.candidate(identity, penalty=penalty)
                           for identity, penalty in (("A", 2), ("B", 4), ("C", 6))],
            "selected": "A", "reason": "A keeps the condition beside the action.",
        }
        self.choose("A")
        self.save()
        self.assertEqual(contract_check.problems(self.out), [])

    def save(self, render=True):
        data = common.load_json(self.record)
        data["comparisons"] = [copy.deepcopy(self.entry)]
        common.write_json(self.record, data)
        if render:
            findings.render(self.out)

    def choose(self, identity):
        path = self.out / "candidates" / identity / "guide.md"
        target = self.out / "rewritten" / "guide.md"
        shutil.copyfile(path, target)
        self.entry["selected"] = identity
        self.entry["final_sha256"] = common.sha256_file(target)

    def errors(self):
        snap, work = common.load_snapshot(self.out)
        return comparison.problems(self.out, common.load_json(self.record), snap, work)

    def test_three_reviewed_candidates_pass_and_leave_the_source_untouched(self):
        self.make_comparison()
        self.assertEqual((self.docs / "guide.md").read_text(encoding="utf-8"), ORIGINAL)
        self.assertEqual((self.out / "original" / "guide.md").read_text(encoding="utf-8"), ORIGINAL)
        self.assertEqual(comparison.score_total(self.entry["candidates"][0]), 98)

    def test_snapshot_flag_marks_new_workflows_without_breaking_old_runs(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(snapshot.main([str(self.out), "--root", str(self.docs), "--copy",
                                            "--compare", str(self.docs)]), 0)
        self.assertEqual(common.load_snapshot(self.out)[0]["workflow"], "compare-three")
        self.out = self.base / "legacy"
        self.make_run()
        self.assertNotIn("workflow", common.load_json(self.out / "snapshot.json"))
        self.assertEqual(contract_check.problems(self.out), [])

    def test_required_comparison_cannot_be_omitted_or_empty(self):
        self.make_run()
        self.mark_comparison_workflow()
        self.assertTrue(contract_check.problems(self.out))
        data = common.load_json(self.record)
        data["comparisons"] = []
        common.write_json(self.record, data)
        findings.render(self.out)
        self.assertTrue(contract_check.problems(self.out))

    def test_unknown_workflow_is_rejected_instead_of_skipping_comparison(self):
        self.make_snapshot()
        snap = common.load_json(self.out / "snapshot.json")
        for workflow in ("compare-two", [], False, None):
            with self.subTest(workflow=workflow):
                common.write_json(self.out / "snapshot.json", {**snap, "workflow": workflow})
                with self.assertRaises(ValueError):
                    common.load_snapshot(self.out)

    def test_init_copies_only_recorded_originals_and_refuses_to_overwrite_drafts(self):
        self.make_snapshot()
        self.mark_comparison_workflow()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(comparison.main(["init", str(self.out)]), 0)
        for identity in ("A", "B", "C"):
            self.assertEqual((self.out / "candidates" / identity / "guide.md").read_bytes(),
                             (self.out / "original" / "guide.md").read_bytes())
        saved = (self.out / "candidates" / "B" / "guide.md")
        saved.write_text("An edited candidate.\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(comparison.main(["init", str(self.out)]), 2)
        self.assertEqual(saved.read_text(encoding="utf-8"), "An edited candidate.\n")

    def test_init_checks_original_integrity_before_creating_candidates(self):
        self.make_snapshot()
        self.mark_comparison_workflow()
        (self.out / "original" / "guide.md").write_text("Changed source.\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            comparison.init(self.out)
        self.assertFalse((self.out / "candidates").exists())

    def test_a_candidate_left_as_the_original_fails_even_when_ineligible(self):
        # status.py lists such a candidate as unfinished; the contract must not
        # pass it by recording it as ineligible.
        self.make_comparison()
        unchanged = self.candidate("B", text=ORIGINAL)
        unchanged["eligible"] = False
        self.entry["candidates"][1] = unchanged
        self.save()
        self.assertEqual(self.errors(), ["candidate B guide.md: is still the original; write a complete version from it"])
        self.assertIn("candidate B guide.md: is still the original; write a complete version from it",
                      contract_check.problems(self.out))

    def test_exactly_three_different_candidate_ids_are_required(self):
        self.make_comparison()
        for identities in (("A", "B"), ("A", "B", "B"), ("A", "B", "C", "C")):
            entry = copy.deepcopy(self.entry)
            entry["candidates"] = [copy.deepcopy(self.entry["candidates"][ord(i) - ord("A")])
                                   for i in identities]
            with self.subTest(identities=identities), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])

    def test_scores_are_integer_points_with_a_reason_for_every_criterion(self):
        self.make_comparison()
        for value in (True, 20.5, -1, 31, "30", None):
            entry = copy.deepcopy(self.entry)
            entry["candidates"][0]["scores"]["fidelity"]["score"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])
        for mutation in ("missing criterion", "missing reason", "empty reason"):
            entry = copy.deepcopy(self.entry)
            scores = entry["candidates"][0]["scores"]
            if mutation == "missing criterion":
                del scores["fidelity"]
            elif mutation == "missing reason":
                del scores["fidelity"]["reason"]
            else:
                scores["fidelity"]["reason"] = " "
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])

    def test_review_and_selection_fields_cannot_be_placeholder_values(self):
        self.make_comparison()
        for field, value in (("eligible", "yes"), ("approach", ""), ("strengths", []),
                             ("weaknesses", None), ("review_note", " "), ("sha256", "bad")):
            entry = copy.deepcopy(self.entry)
            entry["candidates"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])
        for field, value in (("selected", []), ("selected", "D"), ("reason", ""),
                             ("final_sha256", "bad")):
            entry = {**self.entry, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])

    def test_only_the_best_eligible_candidate_can_be_selected(self):
        self.make_comparison()
        self.choose("B")
        self.save(render=False)
        self.assertTrue(self.errors())
        self.entry["candidates"][0]["eligible"] = False
        self.entry["candidates"][0]["review_note"] = "The transition changes the condition's scope."
        self.save()
        self.assertEqual(self.errors(), [])
        self.choose("A")
        self.save(render=False)
        self.assertTrue(self.errors())
        for candidate in self.entry["candidates"]:
            candidate["eligible"] = False
        self.save(render=False)
        self.assertTrue(self.errors())

    def test_tied_eligible_candidates_can_be_chosen_with_a_reason(self):
        self.make_comparison()
        self.entry["candidates"][1]["scores"] = copy.deepcopy(self.entry["candidates"][0]["scores"])
        self.choose("B")
        self.entry["reason"] = "The scores tie; B puts the expiry condition first for the reader."
        self.save()
        self.assertEqual(self.errors(), [])

    def test_merge_must_improve_on_the_best_single_candidate(self):
        self.make_comparison()
        merged = self.candidate("merged", penalty=1)
        merged["sources"] = [{"candidate": "A", "contribution": "Keep the action."},
                             {"candidate": "B", "contribution": "Lead with its condition."}]
        self.entry["merged"] = merged
        self.choose("merged")
        self.save()
        self.assertEqual(contract_check.problems(self.out), [])
        for score in (23, 22):
            self.entry["merged"]["scores"]["structure"]["score"] = score
            self.save(render=False)
            self.assertTrue(self.errors())

    def test_equal_totals_break_ties_by_fidelity_then_structure(self):
        self.make_comparison()
        a, b = self.entry["candidates"][:2]
        a["scores"]["fidelity"]["score"] = 29
        a["scores"]["structure"]["score"] = 24
        b["scores"]["structure"]["score"] = 23
        self.save(render=False)
        self.assertTrue(self.errors())
        self.choose("B")
        self.save()
        self.assertEqual(self.errors(), [])
        a["scores"]["fidelity"]["score"] = 30
        a["scores"]["clarity"]["score"] = 19
        self.save(render=False)
        self.assertTrue(self.errors())
        self.choose("A")
        self.save()
        self.assertEqual(self.errors(), [])

    def test_merge_names_at_least_two_existing_sources_and_their_contributions(self):
        self.make_comparison()
        merged = self.candidate("merged", penalty=1)
        sources = [
            [{"candidate": "A", "contribution": "Keep the action."}],
            [{"candidate": "A", "contribution": "Keep the action."},
             {"candidate": "A", "contribution": "Keep its condition."}],
            [{"candidate": "A", "contribution": "Keep the action."},
             {"candidate": "D", "contribution": "Keep its condition."}],
            [{"candidate": "A", "contribution": "Keep the action."},
             {"candidate": "B", "contribution": ""}],
        ]
        for source in sources:
            entry = {**self.entry, "merged": {**merged, "sources": source}}
            with self.subTest(sources=source), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])

    def test_a_better_eligible_merge_cannot_be_discarded_but_a_tie_can(self):
        self.make_comparison()
        merged = self.candidate("merged", penalty=1)
        merged["sources"] = [{"candidate": "A", "contribution": "Keep the action."},
                             {"candidate": "B", "contribution": "Lead with its condition."}]
        self.entry["merged"] = merged
        self.save(render=False)
        self.assertTrue(self.errors())
        merged["scores"]["structure"]["score"] = 23
        self.entry["reason"] = "A ties the merge and needs no additional changes."
        self.save()
        self.assertEqual(self.errors(), [])
        merged["scores"]["structure"]["score"] = 24
        merged["eligible"] = False
        merged["review_note"] = "Rejected: the combined wording changes the condition's scope."
        self.save()
        self.assertEqual(self.errors(), [])

    def test_editing_an_unselected_candidate_invalidates_its_review(self):
        self.make_comparison()
        path = self.out / "candidates" / "B" / "guide.md"
        path.write_text(DRAFTS["B"] + "Read the result.\n", encoding="utf-8")
        self.assertTrue(self.errors())

    def test_final_hash_and_selected_candidate_both_bind_the_final_text(self):
        self.make_comparison()
        self.entry["final_sha256"] = "0" * 64
        self.save()
        self.assertTrue(self.errors())
        target = self.out / "rewritten" / "guide.md"
        target.write_text(DRAFTS["C"], encoding="utf-8")
        self.entry["final_sha256"] = common.sha256_file(target)
        self.save()
        self.assertTrue(self.errors())

    def test_missing_candidate_and_symlink_escape_are_rejected(self):
        self.make_comparison()
        target = self.out / "candidates" / "B" / "guide.md"
        target.unlink()
        self.assertTrue(self.errors())
        external = self.base / "external.md"
        external.write_text(DRAFTS["B"], encoding="utf-8")
        target.symlink_to(external)
        self.assertTrue(self.errors())

    def test_paths_cannot_escape_or_name_unrecorded_documents(self):
        self.make_comparison()
        for path in ("../guide.md", "/guide.md", "./guide.md", "nested//guide.md"):
            entry = {**self.entry, "path": path}
            with self.subTest(path=path), self.assertRaises(ValueError):
                comparison.check_comparisons([entry])
        self.entry["path"] = "unknown.md"
        self.save()
        self.assertTrue(self.errors())

    def test_high_scores_cannot_hide_unacknowledged_fact_changes(self):
        self.make_comparison()
        changed = DRAFTS["B"].replace("30", "31")
        self.entry["candidates"][1] = self.candidate("B", text=changed, penalty=4)
        self.save()
        self.assertTrue(self.errors())
        self.entry["candidates"][1]["eligible"] = False
        self.entry["candidates"][1]["review_note"] = "Rejected: the expiry value changed from 30 to 31."
        self.save()
        self.assertEqual(self.errors(), [])

    def test_candidate_preservation_is_separate_from_the_final_record(self):
        self.make_comparison()
        changed = "Cache entries expire.\nRead fresh values after expiry.\n"
        candidate = self.candidate("B", text=changed, penalty=4)
        self.entry["candidates"][1] = candidate
        ack = {"path": "guide.md", "kind": "number", "value": "30",
               "reason": "The author approved removing this example value."}
        data = common.load_json(self.record)
        data["preservation"] = [ack]
        common.write_json(self.record, data)
        self.save()
        self.assertTrue(self.errors())
        candidate["preservation"] = [ack]
        self.save()
        self.assertEqual(self.errors(), [])
        candidate["preservation"][0]["path"] = "unknown.md"
        self.save(render=False)
        self.assertTrue(self.errors())

    def test_candidate_exemptions_do_not_come_from_the_final_record(self):
        self.make_comparison()
        candidate = self.candidate("B", text=DRAFTS["B"] + "Use robust regression.\n", penalty=4)
        self.entry["candidates"][1] = candidate
        exemption = {"path": "guide.md", "rule": "EN-04", "text": "robust",
                     "reason": "Term of art: robust regression."}
        data = common.load_json(self.record)
        data["exemptions"] = [exemption]
        common.write_json(self.record, data)
        self.save()
        self.assertTrue(self.errors())
        candidate["exemptions"] = [exemption]
        self.save()
        self.assertEqual(self.errors(), [])

    def test_code_changes_fail_even_with_candidate_preservation_entries(self):
        original = ORIGINAL + "\n```sh\ncache read\n```\n"
        (self.docs / "guide.md").write_text(original, encoding="utf-8")
        self.make_run()
        self.mark_comparison_workflow()
        comparison.init(self.out)
        candidates = [self.candidate(i, text=original, penalty=p)
                      for i, p in (("A", 2), ("B", 4), ("C", 6))]
        changed = original.replace("cache read", "cache delete")
        candidates[1] = self.candidate("B", text=changed, penalty=4)
        import preserve_check
        diffs = preserve_check.compare(preserve_check.facts(original), preserve_check.facts(changed), original)
        candidates[1]["preservation"] = [{"path": "guide.md", "kind": d["kind"], "value": d["value"],
                                          "reason": "This entry cannot authorize a code edit."} for d in diffs]
        self.entry = {"path": "guide.md", "candidates": candidates, "selected": "A",
                      "reason": "A preserves the command.",
                      "final_sha256": common.sha256_file(self.out / "rewritten" / "guide.md")}
        self.save()
        self.assertTrue(self.errors())

    def test_report_contains_all_candidates_scores_reasons_and_links_in_both_languages(self):
        self.make_comparison()
        for lang in ("ja", "en"):
            data = common.load_json(self.record)
            data["meta"]["lang"] = lang
            common.write_json(self.record, data)
            findings.render(self.out)
            report = (self.out / "report.md").read_text(encoding="utf-8")
            self.assertIn("98", report)
            self.assertIn(self.entry["reason"], report)
            for candidate in self.entry["candidates"]:
                self.assertIn(f"candidates/{candidate['id']}/guide.md", report)
                self.assertIn(candidate["scores"]["fidelity"]["reason"], report)
            self.assertEqual(contract_check.problems(self.out), [])

    def test_updated_review_requires_a_new_report(self):
        self.make_comparison()
        self.entry["candidates"][1]["review_note"] = "Checked the expiry condition and action together again."
        self.save(render=False)
        self.assertTrue(any("report.md differs" in error for error in contract_check.problems(self.out)))
        findings.render(self.out)
        self.assertEqual(contract_check.problems(self.out), [])

    def test_comparison_fragments_replace_by_path_and_invalid_merges_are_atomic(self):
        self.make_comparison()
        updated = copy.deepcopy(self.entry)
        updated["reason"] = "The revised review still favors A's sequence."
        findings.merge(self.record, [self.fragment({"comparisons": [updated]})])
        self.assertEqual(common.load_json(self.record)["comparisons"], [updated])
        before = self.record.read_bytes()
        invalid = copy.deepcopy(updated)
        invalid["candidates"][0]["scores"]["fidelity"]["score"] = 31
        for entries in ([updated, updated], [invalid]):
            with self.subTest(entries=entries), self.assertRaises(findings.RecordError):
                findings.merge(self.record, [self.fragment({"meta": {"assessor": "must not save"},
                                                           "comparisons": entries})])
            self.assertEqual(self.record.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
