# deslop

An agent skill that rewrites documents until nothing in them reads as
machine-generated, in what they say as much as in how they say it, without
adding anything they do not say. It works on Japanese and
English Markdown and plain text. For each document it produces three complete
restructurings, reviews and scores them, and delivers the best eligible
version, combining parts when that produces a better result.

> It improves writing. It does not invent facts, add deliberate errors, or aim
> at AI-detector scores, and it reports none.

## What it does

`INVENTORY → VOICE → DETECT → REWRITE → REVIEW → SELECT → VERIFY → REPORT`

Each document gets three full candidates before selection. A failed final
verification returns to rewriting and review.

- **Genre** tunes detection to the kind of document: `readme`, `reference`,
  `tutorial`, `article`, `spec`, `pr`, `message`, `changelog`, `template`,
  `prompt` or `general`. Each exempts its own conventions (a reference's bold
  parameter names, a message's "let me know", a template's unfilled fields)
  and moves density limits (an article allows fewer
  headings and bullets than a README). `README*`, `CHANGELOG*`, `AGENTS.md`,
  `CLAUDE.md` and `*.prompt.md` are recognised by name; others are set with
  `--genre`
- **Prompts** written for a model (system prompts, prompt templates,
  `AGENTS.md`, `CLAUDE.md`, skills) are rewritten into a specification the
  model can check its work against: persona superlatives, exhortations
  (`think deeply`, `ベストプラクティスを最大限に活用`) and pressure are cut,
  demanded qualities (`robust`, `保守性に優れた`) become the conditions the
  prompt already states, and goal, context, constraints and output each get
  their place. Context the model cannot infer stays, since a prompt cut to
  "implement it properly" is worse than the original, and a condition the
  prompt never states is asked of the author, not invented
- **Snapshot** copies the originals before the first edit. In-place mode is the
  default only when every file is tracked by Git with no uncommitted changes;
  otherwise the rewrite goes to a copy. The run is published only after every
  copy and its manifest are complete; a failed write leaves no partial run
- **Voice** records the author's register, terms and sentence habits from a
  style guide or their own earlier text, so the rewrite does not trade one
  generic voice for another
- **Detect** runs `scripts/detect.py`: 9 chat-artifact rules (openers, closers,
  citation tokens such as `oaicite` or `utm_source=chatgpt.com`, placeholders),
  67 lexical rules for English and Japanese model vocabulary and emoji, a
  check for statistics with nothing cited in their paragraph, and 10 density
  measures (bold, em dashes, bold-label bullets, heading and list density,
  repeated Japanese sentence endings, uniform sentence length, triads,
  horizontal rules). The word lists follow Wikipedia's "Signs of AI writing",
  studies of excess vocabulary in PubMed abstracts and Japanese write-ups of
  AI-style Japanese (sources in `reference/patterns.md`). Front
  matter, code and URLs are masked. Eight content perspectives (sentences
  that tell the reader nothing, content the reader does not need, unsupported
  specifics, invented examples, coverage padding, missing positions, effects
  without a mechanism, borrowed authority) and eighteen structural perspectives
  (announced openings, restating summaries, padded triads, generic claims,
  translationese, voice drift…) are read by the agent. The detector cues
  thirteen of them from the document's shape (a title-repeating opening, a
  summary-named last section, lists of three again and again, sibling
  sections built alike, mixed `です・ます` and plain endings…), so the
  read starts where they probably apply
- **Rewrite** works content → structure → sentences → words. The content pass
  keeps a claim only if it informs the reader, is specific to its subject,
  serves the reader's task and is supported by the document; an unsupported
  figure the argument rests on is kept and listed for the author. It creates
  three versions from the same original: one that keeps the argument's
  progression, one ordered around the reader's tasks, and one that removes
  repetition and brings claims beside their evidence. Plans adapt to the
  genre. Each full version stays in `candidates/A/`, `B/` or `C/`
- **Review** records each candidate's strengths, weaknesses and score reasons:
  fidelity /30, structure /25, clarity /20, author's voice /15 and concision
  /10. Totals are out of 100. These are editorial judgments. A candidate
  with missing requirements, changed facts or unresolved hits cannot win
- **Select** takes the highest-scoring eligible version. Compatible
  improvements from other versions can form a combined candidate, which gets
  its own review and scores. It is adopted only when it beats the best
  standalone version; otherwise that version stays selected. The report
  links all candidates and explains the choice
- **Verify** requires zero open hits, a fact check (`scripts/preserve_check.py`:
  numbers, URLs and link targets, inline code and footnotes either survive or are
  acknowledged; code blocks and their occurrence counts must stay unchanged),
  a cold read of the whole document, and, where the host has
  subagents, an independent reader who sees only the result
- **Contract** `scripts/contract_check.py` recomputes all of it on the current
  files and fails on any open hit, unaccounted original hit, unrecorded
  perspective, perspective marked N/A where the originals are cued,
  unacknowledged fact change or stale report. It rejects invalid snapshots,
  duplicate paths and paths outside the recorded roots; copy runs are checked
  against `rewritten/`. New runs use `snapshot.py --compare` to require a
  comparison for every document. Candidate hashes must match their reviewed
  text, eligible candidates pass their own rule and fact checks, and the
  final working file must match the selected candidate. Older snapshots
  without the comparison flag remain supported

- **Status** `scripts/status.py <out>` shows how far a run has come and what
  is left, step by step: which before-hits still need a finding (by path and
  rule, with lines), which perspectives are unrecorded or cued and so cannot
  be `N/A`, which candidates are still the original, missing comparisons,
  open hits, unacknowledged fact changes and stale outputs. It ends with the
  next command, writes nothing, and exits 0 only when the contract passes, so
  an interrupted run can be resumed where it stopped

Ask "where does this read as AI-written" and it stops after DETECT and changes
nothing.

## Install

```sh
make link                 # symlink into every installed host's skills dir
make link AGENT=claude    # one host only
make status
make unlink
```

Then ask your agent to remove the AI style from a document, or invoke
`/deslop` in a slash-command host.

The response shows the three approaches, scores and tradeoffs, then identifies
the selected version. Short candidates can be shown in full; longer ones are
provided as complete files. `report.md` holds the per-criterion reasons,
any integration decision and the prose character counts before and after.

## Use the detector alone

```sh
make detect TARGET=docs/
python3 skills/deslop/scripts/detect.py --root . README.md docs/
python3 skills/deslop/scripts/detect.py --genre article --genre docs/api.md=reference docs/
python3 skills/deslop/scripts/detect.py --genre docs/reference=reference --genre docs/guides=tutorial docs/
```

Genre-exempt hits are still printed, marked with the genre. `--genre
PATH=GENRE` takes a file or a directory; a directory's genre reaches every
document below it, the deepest directory wins, and a file named on its own
wins over any directory.

Exit 0 means no hit; 1 lists them as `path:line:col RULE text`
(`--explain` adds each rule's note). Perspective cues follow as
`path:line PERSPECTIVE cue: why: line`; they never change the exit code.
Invalid inputs and unreadable or unwritable paths exit 2.

Text that is not in a file can be piped in; `--stdin-name` gives it the path
used for its genre and Markdown handling:

```sh
pbpaste | python3 skills/deslop/scripts/detect.py - --stdin-name CHANGELOG.md
```

### Diagnose without rewriting

`--format markdown` prints a diagnosis to paste into a chat, an issue or a
PR comment: a table of documents, then for each one its open hits placed
under the section heading they fall in, with each rule's note, the density
measures over their limits, the lines where perspective cues say to read
first, and the exempt hits with their reasons.

```sh
python3 skills/deslop/scripts/detect.py docs/ --format markdown > diagnosis.md
```

### Choose the rules

`--select` and `--ignore` take rule IDs (`EN-04`), families (`EN`, `JA`,
`EMO`, `ART`, `DEN`, `CNT`) or tiers (`artifact`, `lexical`, `content`,
`density`), comma-separated or repeated. `--list-rules` prints the
catalogue with each density limit and the genres that exempt or move it.
A gate that should stop only chat residue (`I hope this helps`, `oaicite`
tokens, unfilled `[placeholders]`) is one flag:

```sh
python3 skills/deslop/scripts/detect.py docs/ --select artifact --format github
python3 skills/deslop/scripts/detect.py --list-rules --select DEN
```

The selection is recorded in the `--out` result. A rewrite run scans every
rule, so `--snapshot` refuses both flags.

### Keep a phrase on purpose

A hit that is right where it stands (a term of art, a name, a quoted
tagline) can be accepted in the document, with its reason:

```markdown
Robust statistics resist outliers. <!-- deslop-ignore EN-04: the field's term -->

<!-- deslop-ignore EN-14, EN-04: the product's registered tagline -->
A comprehensive, seamless sync.

<!-- deslop-ignore-file DEN-05: a glossary, one heading per term -->
```

`deslop-ignore` covers the line it shares with text, or else the next
nonblank line; `deslop-ignore-file` covers the whole document, density rules
included. Directives name rule IDs only and need a reason after the colon.
Artifact rules cannot be ignored this way. Directives inside code do
nothing, and a directive that covers no hit is listed as unused (a warning
annotation with `--format github`) so it can be removed. Only Markdown
files are read for them; `--no-inline-ignores` disregards them all, and a
rewrite run never reads them.

### Gate a docs tree in CI

A tree that already has tells can still stop new ones. Record a baseline
once, commit it, and check against it; only hits the baseline does not hold
fail. Lexical hits match by path, rule and text, one for one, so a second
copy of an accepted phrase is new; density hits match by path and rule.
When accepted hits disappear, the summary says so, and rerunning with
`--baseline .deslop-baseline.json --out .deslop-baseline.json` tightens the
baseline in place; any new hits that run reports are accepted too.

```sh
python3 skills/deslop/scripts/detect.py docs/ --out .deslop-baseline.json   # once
python3 skills/deslop/scripts/detect.py docs/ --baseline .deslop-baseline.json --format github
```

`--format github` prints open hits as GitHub Actions error annotations on
the changed lines and cues as notices; paths are relative to `--root`
(default: the current directory), so run it from the repository root.
For a readable summary on the job page, add a second step that appends the
diagnosis: `detect.py docs/ --baseline .deslop-baseline.json --format
markdown >> "$GITHUB_STEP_SUMMARY"`.
A rewrite run never takes a baseline: its contract accounts for every hit.

## Landing page

Published at <https://simota.github.io/deslop/>. Pages serves the static
files only, so pasted text there gets the browser's partial scan, labelled
as such; the four bundled samples show their full `detect.py` scans. Run it
locally for the complete detector:

```sh
make serve                       # http://127.0.0.1:8765/
python3 site/serve.py --port 8080
```

`site/` is a local page that runs the detector on pasted text through
`POST /api/detect`, which calls `detect.py` with the same rules, genre
exemptions and inline ignores as the command line. A full scan can be
copied as the `--format markdown` diagnosis. `site/data.js` bundles copies of the rules,
their reference entries, `examples/` and two corpus documents with their
scans. `python3 site/build_data.py` rebuilds it; `make test` fails when it,
or a count, phase or corpus result stated on the page, no longer matches the
skill. `artifacts/` holds the page's design and QA records, the promo video
with its sources, and `artifacts/quality/`, the before-and-after quality
scores with the scripts that measured them.

## Develop

```sh
make test    # offline unit tests
make check   # tests + skill consistency (references cited, rule docs in sync)
```

The Makefile needs a GNU Make newer than 3.81, the version macOS ships;
3.81 stops while resolving the checkout path. Without one, run the tests
with `python3 -m unittest discover -s tests`.

Scripts use the Python 3.10+ standard library only. `examples/` holds an
AI-styled sample and its rewrite in each language; the tests depend on their
exact contents.
