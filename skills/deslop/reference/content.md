# Content perspectives

**Read when:** DETECT (read each document whole for these, before the
structural perspectives) and REWRITE (the content pass comes first).

Wording and structure are only half of what makes a document read as
generated. The other half is what it says: sentences that would be true of any
subject, advice the reader already follows, numbers nobody measured, examples
nobody saw. A rewrite that fixes the phrasing of such a sentence leaves the
tell in place. These perspectives judge the content itself.

They are recorded like the structural ones: each `CON-NN` in `perspectives` as
`applied`, `N/A` or `not checked` with a note, and a finding with `rule` set
to its id for every perspective that changed something. Rules can point at
some of it (`CNT-01`, `EN-24`, `EN-27`, `JA-31`, `JA-32`), and `detect.py`
cues CON-05 when two or more headings name stock sections (benefits, best
practices, FAQ, `メリット`, `今後の展望`); most of it needs the reading below.
Cues work as described in `reference/structure.md`.

## The content pass

Before touching wording, go through each document paragraph by paragraph and
put every claim through four tests. Keep a claim only if it passes all four.

1. **Information.** What does the reader know after this sentence that they
   did not know before? If the answer is "nothing" or "that the topic is
   important", the sentence goes (CON-01)
2. **Substitution.** Replace the subject with a different product, library or
   topic. If the sentence is still true, it says nothing about this subject
   (CON-01, CON-07)
3. **Reader.** Would the reader named in INVENTORY need this to do what they
   came to do? Basics they already know and topics outside their task go
   (CON-02, CON-05)
4. **Support.** Is the claim backed by something in the document: a
   measurement, a link, a code path, a step the reader can repeat? A specific
   with no support is not deleted silently and never "fixed" with an invented
   source (CON-03)

Then ask of each section what it would lose if it were deleted outright. A
section whose answer is "nothing the reader needs" is removed with its heading.

While reading, also note what the document says against itself and what it
ties to a date. A step split into its own change that a checklist elsewhere
requires inside every change, a status code monitored in one section and
missing from the table in another, a statement "as of" a date that has since
passed: these need no outside knowledge to see, and the skill does not
resolve them. List each under `decisions` with the places it appears.

Reading for them is a pass of its own, done even on a short message: hold
each pair below side by side rather than trusting a read-through to notice.
Take the list one item at a time and, for each, find every place in the
document it applies to before moving to the next. Earlier runs missed pairs
that were on this list because they read the document once and the list once.

- Each usage example against the prose that describes it (an example that
  omits an argument the synopsis requires, output whose columns differ from
  the text that explains them)
- Each definition in a table against the same thing defined in prose or code
  (a key format that includes a field the table says that unit lacks)
- Numbers that constrain each other (a schedule of 24 sessions a year and a
  cap of one talk per person; a KPI of "twice a month" and a fallback to
  once a month; a period given as "one week" next to the two dates)
- Each named name against its other mentions (the same period called two
  things, a cross-reference to "the next section" that sits elsewhere)
- What the document says it supports against how it says it works (Windows
  builds and rotation detected by inode)
- A frequency or method promised against a word that contradicts it
  (`[報告の頻度]にて随時`)
- Each goal or target against the mechanism meant to reach it (a per-user
  limit keyed too coarsely for the goal it serves, "unused" judged from
  sampled metrics)
- Two values of one measure given in the same tense (an error rate "is 18%"
  and "is now 3%")
- Each decision or problem against the action items that should follow it,
  and each date against the deadlines it depends on
- What an overview, a plan table or a free trial promises against the
  detailed section that defines it
- Each row of a test or verification table against the list of changes
- A heading's claim against the strength of the section under it, and a
  name used in prose against the contact or owner given for it
- One thing called by two names (`bearer token` in one section, `API key`
  in another)
- What one section marks optional or conditional against a step that
  assumes it (a retry procedure that relies on an optional header)
- A list or range stated in one place against a word elsewhere that claims
  more (`all versions` next to a matrix of three), and each example or
  snippet against the scope the text declares for it
- How a mechanism is said to work against what the change does (backoff
  "reduces repeated requests" in a change that adds retries)
- A question against the scope of its answer (asked about overtime and
  holiday work, answered for one)
- The time a decision is made against the time the figures it depends on are
  set (continuing after three months, targets reset at three months)
- In Japanese, the honorific against the sentence's end: `させていただく` asks
  for consent, `こととなりました` reports a decision already made

Never reword a passage so that a contradiction disappears; that resolves it
for the author. List it under `decisions` and leave both places as they are.

Notes the author left for themselves are not content either: a screenshot or
GIF placeholder (`（スクショ：…）`), `TODO`, `ここに図`. Delete them (CON-05)
and list each under `decisions` so the author can insert the real thing. When
the note also told the reader a state (`#TODO: 見積もり未取得`), keep that
state as a plain sentence (`見積もりはまだ取得していない。`).

## What the pass may and may not do

- **May delete** any sentence, paragraph or section that fails the
  information, substitution or reader test. Deleting a claim with no content
  loses nothing; record it under the perspective and, when it carried a
  number or link, in `preservation`
- **May keep a weaker claim** by cutting it down to what the document
  supports (`大幅に高速化` → `2回目以降はディスクを読まない`, when the document
  says so)
- **Must not add** facts, sources, numbers, examples, experience or opinions.
  When a claim needs one of those to survive, it is cut or kept plain, and the
  gap goes under `decisions` for the author
- **Must not delete a real fact** because it reads generic. A sentence that
  states a limit, a default, a requirement or a step stays, even if it is
  dull

A thorough content pass can shrink a generated document a lot. That is the
expected result, not a failure; the report shows prose characters before and
after so the reader sees it. When most of a document goes, say so in the chat
summary and list in `decisions` what the author would need to supply to make
it worth publishing.

## Perspectives

### `CON-01`
**Sentence that tells the reader nothing.** Fails the information or
substitution test: `キャッシュはパフォーマンスにとって重要です`, `Security is a
top priority`, `This guide will help you get the most out of X`. Delete it.
Do not replace it with a better-sounding sentence of the same emptiness.

### `CON-02`
**Content the reader already knows or does not need.** Definitions of terms
the reader uses daily, reminders to test and back up, a history of the field
in an installation guide. Judge against the least experienced reader the
document names or addresses (a FAQ for all staff includes new hires, who need
`報連相` spelled out): an API
reference does not explain what an API is. Delete it, or link to where it is
explained if the document already links there.

### `CON-03`
**Unsupported specifics.** Statistics, study results, quotations, dates, user
counts and benchmark figures with no source in the document and no way to
derive them from it (`導入企業の約30%が効果を実感`, `studies show a 40%
increase`). Generated drafts invent these. They are never verified or
replaced by this skill: when the figure is decoration (an opening hook, an
aside nothing else depends on), delete the sentence and record the number in
`preservation`; when the document's argument rests on it, keep it unchanged
and list it under `decisions` as needing a source. `CNT-01` points at
percentages and multipliers with nothing cited in their paragraph.
When the document itself says its specifics are assumed or unverified (a
generated reference whose options were invented), that statement is the
support status: keep it as a plain sentence, never delete it (EN-25, JA-33).

### `CON-04`
**Invented or generic illustration.** Hypothetical scenarios and personas
(`Imagine you're a developer who…`, `例えば、あなたが`, `Aさん（仮名）の場合`)
and examples that fit any product (`EC サイトや SNS など`). If the document
has a real example, use that one; otherwise delete the illustration and keep
the point it was meant to illustrate, stated directly.

### `CON-05`
**Coverage padding.** Sections and bullets present because a complete article
"should" have them: benefits, use cases, best practices, security
considerations, future prospects, FAQ, each one generic. Keep what the reader
needs for their task and what is specific to this subject; remove the rest,
headings included. Ask what the reader would miss, not what a table of
contents would miss.

### `CON-06`
**No position where the document has the basis for one.** Options compared
and left at `一概には言えません` or "it depends on your needs" when the document
itself contains the conditions that decide. State the choice under each
condition the document gives (`更新が多いなら TTL を短く`). When the
document does not contain the basis, delete the empty comparison rather than
inventing a recommendation, and list the open question under `decisions`.

### `CON-07`
**Effect claimed without a mechanism.** Benefits asserted with no account of
how they happen: `生産性が向上します`, `improves the developer experience`,
`ユーザー満足度を高めます`. Replace with the mechanism the document describes
(what the reader no longer has to do, what the system skips), or delete the
claim when the document describes none.

### `CON-08`
**Borrowed authority or experience.** Appeals to unnamed experts, trends and
majorities (`専門家によると`, `多くの企業が`, `experts agree`), and first-person
experience the author's other material does not support (`私も以前は〜で悩んで
いました`, `In my years of experience`). Name the source the document actually
cites, or cut the appeal and keep the claim only if the document supports it.
First-person experience is never deleted on suspicion alone: when nothing in
`voice` or the document backs it, list it under `decisions` for the author to
confirm or remove.
