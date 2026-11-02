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
  `tutorial`, `article`, `spec`, `pr`, `message`, `changelog`, `template` or
  `general`. Each exempts its own conventions (a reference's bold parameter
  names, a message's "let me know", a template's unfilled fields) and moves
  density limits (an article allows fewer
  headings and bullets than a README). `README*` and `CHANGELOG*` are
  recognised by name; others are set with `--genre`
- **Snapshot** copies the originals before the first edit. In-place mode is the
  default only when every file is tracked by Git with no uncommitted changes;
  otherwise the rewrite goes to a copy. The run is published only after every
  copy and its manifest are complete; a failed write leaves no partial run
- **Voice** records the author's register, terms and sentence habits from a
  style guide or their own earlier text, so the rewrite does not trade one
  generic voice for another
- **Detect** runs `scripts/detect.py`: 9 chat-artifact rules (openers, closers,
  citation tokens such as `oaicite` or `utm_source=chatgpt.com`, placeholders),
  61 lexical rules for English and Japanese model vocabulary and emoji, a
  check for statistics with nothing cited in their paragraph, and 10 density
  measures (bold, em dashes, bold-label bullets, heading and list density,
  repeated Japanese sentence endings, uniform sentence length, triads,
  horizontal rules). The word lists follow Wikipedia's "Signs of AI writing",
  studies of excess vocabulary in PubMed abstracts and Japanese write-ups of
  AI-style Japanese (sources in `reference/patterns.md`). Front
  matter, code and URLs are masked. Eight content perspectives (sentences
  that tell the reader nothing, content the reader does not need, unsupported
  specifics, invented examples, coverage padding, missing positions, effects
  without a mechanism, borrowed authority) and sixteen structural perspectives
  (announced openings, restating summaries, padded triads, generic claims,
  translationese, voice drift…) are read by the agent. The detector cues
  eleven of them from the document's shape (a title-repeating opening, a
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
```

Genre-exempt hits are still printed, marked with the genre.

Exit 0 means no hit; 1 lists them as `path:line:col RULE text`. Perspective
cues follow as `path:line PERSPECTIVE cue: why: line`; they never change the
exit code. Invalid inputs and unreadable or unwritable paths exit 2.

## Landing page

```sh
make serve                       # http://127.0.0.1:8765/
python3 site/serve.py --port 8080
```

`site/` is a local page that runs the detector on pasted text through
`POST /api/detect`, which calls `detect.py` with the same rules and genre
exemptions as the command line. `site/data.js` bundles copies of the rules,
`examples/` and two corpus documents with their scans; nothing regenerates
it, so update it by hand when those change. `artifacts/` holds the page's
design and QA records and the promo video with its sources.

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
