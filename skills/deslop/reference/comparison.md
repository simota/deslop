# Comparing rewrites

**Read when:** REWRITE, REVIEW and SELECT, and when recording candidate scores.

## Contents

- [Create three versions](#create-three-versions)
- [Review and score](#review-and-score)
- [Select or combine](#select-or-combine)
- [Record and deliver](#record-and-deliver)

## Create three versions

Take the snapshot with `--compare`. After DETECT and the voice record, run:

```sh
python3 scripts/comparison.py init <out>
```

This copies every recorded original to `candidates/A/<path>`,
`candidates/B/<path>` and `candidates/C/<path>` inside the run directory.
It refuses an existing candidate directory; do not run it again to revise
candidates. Edit those copies, keeping their document paths and genres.
Leave the final working files unchanged until selection.

The candidates are published together only after all originals have passed
their snapshot hashes and all copies have been written. Each original is
read once, so A, B and C receive the same verified bytes. A failed
initialization leaves no partial candidate directory and can be retried.

Choose three plans that fit the reader and genre. These are starting points:

| Candidate | Plan |
|---|---|
| A | Keep the original argument's progression; regroup paragraphs and remove detours |
| B | Order the information around the reader's questions, decisions or tasks |
| C | Remove repetition and bring each claim close to its evidence or condition |

Write a complete document for each plan. A heading outline or a list of
suggestions is not a candidate. Apply the content, structure, sentence and
word passes to each one. All candidates start from the same `original/`
file, voice rules, reader and genre; B must not inherit A's deletions, nor
C inherit B's. Keep required steps in their dependency order and preserve
code, quotations, identifiers, links and referenced anchors.

For a long document, draft sections separately within each candidate, then
read the whole version for transitions, duplication and missing conditions.
For short or constrained text, compare useful choices in sentence grouping
and information placement. Explain unavoidable overlap in `review_note`
and `limitations`; do not lengthen or invent content to force differences.

When delegation is available, give writers the same original and voice rules
with different plans. Give a separate reviewer the original, the candidates
and the rubric without telling them which should win. Sequential work uses
the same steps; record the lack of a separate reviewer in `limitations`.

## Review and score

Read each full candidate against the original. Check the meaning of each
claim, its uncertainty and conditions, the attribution of numbers, required
steps and their order, and everything the reader needs to act. The value
check cannot tell whether an unchanged number now qualifies the wrong
claim. Record this review in `review_note`, with the candidate's strengths
and weaknesses in their own fields.

Set `eligible` to false if a candidate changes facts or protected content,
loses required information, has unresolved detector hits, or fails that
semantic review. Explain the blocking issue in `review_note`. A high score
cannot offset it. Repair the candidate and review it again, or retain it as
a rejected alternative. At least one standalone candidate must be eligible.

Use the same rubric for all candidates, including any combined version:

| Key | Maximum | What earns the points |
|---|---:|---|
| `fidelity` | 30 | Meaning, qualifications, evidence and necessary information remain clear and accurate |
| `structure` | 25 | The information order and paragraphs serve this reader's task |
| `clarity` | 20 | Subjects, relationships and transitions can be understood on one reading |
| `voice` | 15 | Register, terminology and rhythm follow the recorded author's voice |
| `concision` | 10 | Padding is removed while the needed explanation remains |

Assign an integer within each range and give a short, text-specific reason.
Full points mean no identified weakness on that criterion; subtract points
for the weaknesses the review names. Do not reward shorter text merely for
being shorter. The script adds the five scores to a total out of 100.
These are editorial judgments, not AI-detector scores or measured certainty.

Candidate `exemptions` and `preservation` use the same formats and restrictions
as the main record, but cover only that candidate and document. The contract
rescans each eligible candidate with its recorded genre and its own
exemptions, and compares its values with the original. Every value change
needs a reason; changed code blocks are rejected even with a reason. Never
use a preservation entry to permit an invented claim or a missing requirement.
The final record's acknowledgements do not excuse candidate changes.

## Select or combine

Choose the eligible candidate with the highest total. Break a tie by fidelity,
then structure, then the smaller unnecessary departure from the original;
record the concrete reason. If all candidates are ineligible, revise them
and repeat REVIEW. Do not describe a failing result as the best version.

Combine only when another candidate offers a specific improvement that fits
the selected candidate. Write the full result to
`candidates/merged/<path>`, retaining A, B and C. Record at least two different
source candidates and what each contributes: for example, B's order with
A's paragraph explaining a condition. The base version counts as a source.
Resolve duplication, broken transitions and shifts in register after joining
the parts. Check the result against the original, then review and score it
from scratch using the same rubric.

Adopt the combined version only if it is eligible and its total is strictly
higher than the best eligible standalone version; when it meets those
conditions, select it. Otherwise keep the
standalone winner and record why the combination was not adopted. If a
combination was attempted, retain its full text and review even when rejected.
One attempt is usually enough; stop when no specific improvement remains.

Copy the selected candidate to the working path recorded in `snapshot.json`
(`rewritten/<path>` for copy mode). Record only the final changes against
the original in the main findings, exemptions and preservation lists. Do not
merge all candidate change logs into those lists.

## Record and deliver

Add one `comparisons` entry per snapshot document to `findings.json`:

| Field | Value |
|---|---|
| `path` | The document path relative to the snapshot root |
| `candidates` | Exactly three complete candidate records, IDs `A`, `B`, `C` |
| `selected` | `A`, `B`, `C`, or `merged` |
| `reason` | Why this version won, including the tie-break or integration decision |
| `final_sha256` | SHA-256 of the selected final working file |
| `merged` | Optional full candidate record with ID `merged`, plus `sources` |

Each candidate record has this shape (the digest shown is illustrative):

```json
{
  "id": "A",
  "approach": "Keep the argument order; move each condition beside its claim",
  "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "eligible": true,
  "scores": {
    "fidelity": {"score": 30, "reason": "All requirements and their conditions remain"},
    "structure": {"score": 22, "reason": "Conditions are adjacent; setup still appears late"},
    "clarity": {"score": 18, "reason": "Subjects are explicit; the final paragraph is dense"},
    "voice": {"score": 15, "reason": "Register and glossary match the voice record"},
    "concision": {"score": 9, "reason": "The closing paragraph repeats the scope once"}
  },
  "strengths": "Each requirement states its condition in the same paragraph",
  "weaknesses": "A first-time reader must find setup in the second section",
  "review_note": "Checked claim scope, number attribution, steps and protected content against the original",
  "exemptions": [],
  "preservation": []
}
```

For a combined record, add `sources`, such as
`[{"candidate": "B", "contribution": "Reader's task order"},
{"candidate": "A", "contribution": "Conditions beside each requirement"}]`.
Scores and review always describe the combined text itself.

Calculate hashes after the review's last edit (for example with `sha256sum`).
Changing any candidate invalidates its saved hash; changing the selected
working text also requires updating the selected candidate, reviewing and
scoring it again, and rerunning SELECT and VERIFY. Do not just refresh hashes
while keeping a review of older text.

`findings.py report` includes candidate links, scores, reasons, reviews and
the selection. `contract_check.py` checks them against the files. Show the
three approaches and totals in chat with the selection reason, then deliver
the selected full text or file. Also show all three full versions when short;
otherwise link their complete files. Keep the report available for the
per-criterion reasons and any rejected combination.
