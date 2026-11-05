# Verifying

**Read when:** VERIFY, after every round of REWRITE, and before the report.

A document passes VERIFY only when all four hold after its last edit. Any
failure sends it back to REWRITE and REVIEW; there is no partial pass. Keep
the edited candidate, its scores and the selection current before checking
the final working file again.

The three full candidates and any combined version must remain available.
`contract_check.py` verifies their hashes, scores and eligibility, the
selection rule, and the final file's match to the selected candidate. It
rescans eligible candidates with their own exemptions and preservation
entries. A combined winner must outscore the best eligible standalone
candidate (`reference/comparison.md`).

## 1. Rules

```sh
python3 scripts/detect.py --snapshot <out> --exempt <out>/findings.json --out <out>/detect.after.json
```

Exit 0: no open hit. Exit 1: read each listed hit in context and rewrite,
delete or exempt it. A new hit that was not in `detect.before.json` was
introduced by the rewrite; fix the rewrite rather than exempting it.

## 2. Facts

```sh
python3 scripts/preserve_check.py <out>
```

Exit 0: every number, URL or link target, inline code span and footnote either
still appears or has a `preservation` entry, and code blocks and their
occurrence counts are unchanged. Code block changes cannot be acknowledged
away, including adding or removing a repeat of the same block. Restore the
original blocks. An added value is reverted unless the requester supplied it.

Other values are compared by presence, not by count: dropping a repeat of a value
the document still states is not a change, so a value changed into another
value the document already states (`30` to `3` where `3` appears elsewhere)
passes this check and is left to the cold read.

Numbers include their sign, leading decimal point and exponent: changing
`-10` to `10`, `.5` to `5` or `1e-3` to `1e3` must be acknowledged.
Full-width digits count as their ASCII form, but superscripts do not: `10²`
is the numbers `10` and `2`, not `102`. Normal, superscript and subscript
number runs stay separate at both ends: `10²3` yields `10`, `2` and `3`,
and `SO₄²⁻` yields `4` and `2`. Signs and digits within one run stay
together, so `10⁻³` includes `-3`. A footnote's references and its
definition are compared apart, so removing the citation from a claim is
reported even when the definition stays; one `footnote` entry acknowledges
both. Definitions begin at the line's content start, including inside lists
and blockquotes. A colon after a citation in prose does not make it a
definition. An escaped marker such as `\[^1]` is literal text, so escaping a
reference or definition is reported as losing that role. Footnote labels
are not numbers; escaped literal labels remain prose. Link titles, HTML
blocks, and inline HTML syntax such as attributes and comments cannot
supply either footnote role; numbers in their text are still checked.
Text between inline HTML tags can still contain references. A URL is already
present only when the original states it whole, in prose or in code, not as
the start of a longer one. Explicit
Markdown destinations and autolinks retain their trailing punctuation;
sentence punctuation after a bare URL is excluded. Link destinations retain
nested parentheses and escaped delimiters; numbers in link titles are still
checked. Bare HTTP and HTTPS URLs also retain balanced parentheses and
bracketed IPv6 hosts; scheme recognition is case-insensitive. Reference
definitions can put the destination on the next line or
appear inside a list or blockquote. Definitions immediately after ATX or
Setext headings and completed HTML blocks are also checked. A line that
continues a paragraph remains prose, with its inline code protected.
Backticks in destinations cannot hide the following prose from detection.
Inline links may wrap inside a list or blockquote; their destinations and
titles cannot consume a later paragraph, heading or list item. Detection
uses the same destination boundaries as the fact check. Link labels and
titles remain prose, and incomplete or escaped link syntax cannot hide it.
Inline code spans can cross a line ending within a paragraph, including a
blockquote; rewrapping
preserves the code's contents without treating quote markers as code. Code
fences are protected inside lists and blockquotes, including fences on the
list marker's line. An unclosed fence ends with its container, so following
prose is still checked.

All run commands validate `snapshot.json` before reading its files. A copy
run uses `<out>/rewritten/`; an in-place run uses its recorded root. Paths
must be unique and stay within their original and working roots. Directory
read errors stop document discovery and original-file inventory; an unread
subdirectory cannot be silently omitted from a successful check. If a run
record is invalid, inspect the error and restore the record or take a fresh
snapshot before editing; do not redirect verification to the originals.
Snapshot creation publishes the complete run with a directory rename.
The output directory's parent must be writable; a failed read or write
leaves the requested output absent or empty, so initialization can be retried.
Recorded genres must be known strings. When a genre is omitted, it is
inferred from the filename as in earlier snapshots, with `general` used
when no filename pattern matches.
An alias inside a recorded root keeps the snapshot's document path, genre
and exemptions. Its target's filename cannot change those choices.
Detection and preservation hashes identify the same bytes that were
analyzed. Candidate checks use their verified bytes for both detection and
fact comparison, and the report's record hash identifies the JSON that was
rendered. Editing a file afterward still requires running verification again.

Bold markers written straight after a bare URL are read as part of it, so
removing the bold from `**see https://example.com/repo**` reports
`https://example.com/repo**` lost and `https://example.com/repo` added.
Record both under `preservation` with that reason; the link itself did not
change.

A new link may reuse a complete URL or an independent literal from the
original. A prefix or suffix of another URL is a different value and needs
a reason. Literal tokens in code keep their trailing punctuation; sentence
punctuation outside a prose value does not become part of its target.
Prose quotation marks and emphasis can surround a complete value. A quoted
code value keeps its inner brackets and punctuation; quote concatenations
and escape sequences are not decoded. A value embedded in unfamiliar code
syntax needs a reason rather than an assumed match.

## 3. Cold read

Read each rewritten document start to end, as its reader would, without
looking at the original or the rule list. Mark every place that still reads as
generated: a sentence that rates instead of states, a paragraph shape repeated
from the previous one, a heading nobody would navigate to, a transition that
could sit in any document, a claim that would be just as true of a
competitor, an example nobody could have observed, a benefit with no "how".
These are tells no rule names; they are the reason this step exists. Then
check the eight perspectives in `reference/content.md` and the sixteen in
`reference/structure.md` once more against the final text, reading first the
lines that `detect.after.json` still cues. Every mark goes back through
REWRITE and is recorded under the closest perspective.

Also check that the document still does its job: the steps still work in
order, the requirements are all still there, and nothing a reader needs was
deleted with the padding.

## 4. Independent reader

With subagents available, give one fresh reader the rewritten text only (not
the rules, the original or this record) and ask which sentences read as
machine-generated and why, and which claims say nothing about this particular
subject. Treat their list like cold-read marks. Agreement is
not the target; each mark is read and either fixed or answered in `decisions`.
Without a subagent, record "independent reader not run" in `limitations`.

A second check finds what the rewrite made worse. When the rewrite is
byte-identical to the original there is nothing to compare: skip this check
and say so in `limitations`, or give the readers the single text if a plain
review is wanted. When other readers are
available (another subagent or another model's CLI), give them the original
and the rewrite unlabeled, as "two articles" in either order, with only a
neutral task such as "review and compare these". Do not say which is the
original or that either was generated. Readers often rate the original's
opening, closing summary, bold, question headings and closing calls to action
higher, especially when they judge for shares; those are the patterns this
skill removes, and they are not taken back. What is taken back is any place where
the rewrite is worse than the original: a claim made stronger, a word in a
different register, a topic change left without its heading, a fact lost.
Those marks go through REWRITE. A reader that returns nothing is run once
more; if it fails again, the comparison stands on the others and
`limitations` names the missing reader. A reader whose host has this skill
installed may recognise the task; when one names it, record that its comparison was not
blind in `limitations`.

## Finishing

```sh
python3 scripts/findings.py report <out>
python3 scripts/status.py <out>
python3 scripts/contract_check.py <out>
```

`status.py` lists, per step, what is still open and the command that comes
next; it is the quickest way to see which `(path, rule)` groups lack a
finding or which perspective is cued but recorded `N/A`. It exits 0 only
after running the contract check itself.

`contract_check.py` reruns rules and facts on the current files, so a later
edit cannot pass on an earlier record. Render the report after the last merge;
a report from an earlier `findings.json` fails the check.
