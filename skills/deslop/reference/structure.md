# Structural perspectives

**Read when:** DETECT (read each document whole for these) and VERIFY (the
cold read checks them again).

Rules cannot see these: they live in how a document is built, not in any one
phrase. Read the whole document once per perspective group, record each
perspective in `perspectives` as `applied` (with what changed, or "none
found"), `N/A` (with why it cannot occur in this genre) or `not checked` (with
why; also in `limitations`). A perspective that changed something also gets a
finding with `rule` set to its id.

`detect.py` lists **cues** for some of these: lines where the shape of the
document suggests the perspective applies. A cue is not a hit. It needs no
finding or exemption and does not change the exit code; it says where to read
first. Read the cued place, then decide. A perspective cued in the originals
cannot be recorded as `N/A`: record `applied`, with "none found" and the
reason when the cue was wrong. Each perspective shows at most five cued lines
per document. Perspectives without a cue are read the same way as before; the
cues cover only what the shape of a document can show.

| Perspective | Cued when |
|---|---|
| STR-01 | The first paragraph announces the document, or half its first sentence's words are in the title |
| STR-02 | The last section is named as a summary, or is at most three sentences with 85% of their words used earlier |
| STR-03 | At least 40% of paragraphs (two or more) end on a sentence that judges what came before |
| STR-04 | Two or more lists, at least 60% of them, have exactly three items |
| STR-05 | Two or more sections, at least half of them, hold only two sentences or fewer of prose. Not cued in `readme`, `reference`, `spec`, `pr` or `changelog` |
| STR-06 | Three quarters of four or more sibling sections share one block layout. Not cued in `reference`, `spec` or `changelog` |
| STR-11 | Two adjacent sentences share half their words, or the second opens with "In other words" |
| STR-13 | 80% of five or more paragraphs have the same number of sentences |
| STR-14 | A heading ends in a question mark or `とは` |
| STR-16 | Japanese prose mixes `です・ます` and plain endings, the minority at 15% or more |
| STR-17 | 20 or more non-blank lines and no `<details>` block; a `<details>` block with no paragraph before it; a non-blank line that is not a tag straight after `</summary>`. Cued only in `pr` |

Cues that compare proportions (STR-03 to STR-06, STR-13, STR-16) need as
much prose as the density rules. The genres that silence a cue are set as
`quiet` on the perspective in `scripts/rules.json`; a perspective with
`only` is cued in those genres and no other.

### `STR-01`
**Announced opening.** The first paragraph says what the document will do, or
restates the title. Delete it; the first sentence should already be content.
An opening often wraps the one piece of content it has, the problem the
document answers (`レビューに時間がかかりすぎる`), in an importance claim, a
borrowed majority and an announcement. Delete the wrapping and keep that
problem as one plain sentence; a reader new to the document needs it to know
why the rest follows. When the announcement also tells how the sections are
arranged (by period, then by theme), keep that arrangement as a plain
sentence too; without it the next sentences point at nothing.

### `STR-02`
**Closing that restates the body.** A final section or paragraph repeats the
main points. Delete it, or keep only what is new (a next step, a limit).
The author's own feeling or stance in a closing (`私はターミナルを選びました`)
is new, not a restatement: in a first-person article keep it even when the
rest of the section goes.
A "challenges and future outlook" close that ends on optimism is the same
pattern (EN-26).

### `STR-03`
**Moral at the end of every paragraph.** Paragraphs close with a sentence that
evaluates what was just said ("This makes X much easier"). Cut those sentences.

### `STR-04`
**Padded triads.** Groups of exactly three (adjectives, benefits, bullets)
where the content has two or four. Keep the real number of items.

### `STR-05`
**Over-structuring.** Headings, bullets, bold and tables where a paragraph
would read better: a heading over two sentences, bullets that are one argument
cut into pieces. Restore prose; keep structure the reader navigates or scans.
A checklist, a template's fields, a set of labels or parallel tools each with
its job is an inventory the reader scans or copies: drop its bold, keep it a
list. Folded into one sentence (`〜か、〜か、〜か、です。`) it is harder to
read than the list it replaced. A density limit is not a reason to flatten an
inventory: when a density hit stands only because of such lists, exempt it
and name the inventories in the reason. A heading that marks a change of
topic is navigation even when its parent heading names both topics: after a
figure, table or code block, after a paragraph or list that closes one
subject, and over each of several parallel items (measures, options, steps)
the reader compares. Removing a heading must not leave a topic change
unmarked, a density limit is never the reason to remove one, and the gap is
never filled with a signpost sentence (STR-10).

### `STR-06`
**Symmetric sections.** Every section has the same shape and length (intro
sentence, three bullets, closing line). Let each section be as long as its
content.

### `STR-07`
**Generic claims.** Sentences that would be true of any product or topic
("improves efficiency", "多くの企業が"), claims credited to unnamed experts
or studies (EN-24), and statistics with no source. Replace with the document's
own specifics, or delete. Never invent the specifics. The content tests in
`reference/content.md` decide whether such a claim has anything left to keep.

### `STR-08`
**Hedging and false balance.** Qualifiers on things the document knows;
"on the other hand" sections that exist only to look balanced, and
pros-and-cons that end without a choice (`一概には言えません`, JA-29). State
what is known; keep a caveat only where there is a real condition.

### `STR-09`
**Reflexive contrast framing.** Repeated "not X but Y" (`単なる〜ではなく`)
against a position nobody holds. State Y.

### `STR-10`
**Signposting and meta-commentary.** "Next, let's look at…", "次に〜を見て
いきましょう", "As mentioned above". Delete; headings and order already
signpost.

### `STR-11`
**Restatement.** The same point twice in a row in different words
(`つまり`, `In other words`). Keep the clearer one.

### `STR-12`
**Register and enthusiasm mismatch.** Hype, exclamation, praise of the
reader or sympathy formulas in a technical or business document. Match the
register in `voice`.

### `STR-13`
**Uniform rhythm.** Every sentence the same length and build, every
paragraph three sentences. Let the content set the rhythm: combine what belongs
together, split what is overloaded (see DEN-07, DEN-08).

### `STR-14`
**Question headings and FAQ padding.** Headings phrased as the reader's
question (`〜とは？`, "What is X?"), FAQ entries nobody asks. Name the content;
fold padding questions into the text or delete them.

### `STR-15`
**Translationese.** English structure in Japanese (`〜において`, explicit
pronouns `それは`, `〜することができる`, a subject in every sentence) or
Japanese structure in English. Rewrite as a native writer of the target
language would.

### `STR-16`
**Voice drift from the author.** The rewrite or the original drifts from the
rules in `voice`: register changes mid-document, terms translated that the
author keeps in English, a different person addressing the reader. Bring it
back to the recorded voice.

### `STR-17`
**Detail the reader cannot skip.** A pull request description longer than one
screen with every section at the same level: the reviewer reads all of it to
learn what the change is and whether it needs them. Put the shortest text
that answers those two questions first, then fold the rest into one
`<details>` block, as Simon Willison does with agent-written descriptions
(<https://simonwillison.net/2026/Nov/9/details-summary/>).

- The opener is one to three sentences chosen from the document. Nothing is
  written for it that the document does not say. It is the author's statement
  of what deserves the reader's time, so list it under `decisions` for the
  author to confirm.
- What a reviewer must act on stays outside the fold: breaking changes,
  questions put to the reviewer, screenshots, and every section the
  repository's PR template requires (ticket number, disclosure, checklist).
- The fold exempts nothing. Every rule and perspective applies to the text
  inside it as it does outside, and it is rewritten the same way.
- `<summary>` names what is folded (`Details`, `詳細`). A model name goes
  there only when the document or the requester gives one.
- Write `<details>`, then `<summary>…</summary>` on its own line, a blank
  line, the Markdown, a blank line, `</details>`. Without the blank line the
  Markdown stays part of the HTML block and is shown as typed (CommonMark,
  HTML blocks). Headings, tables and code blocks move into the fold unchanged;
  do not convert them to HTML tags.
- A description under 20 non-blank lines stays flat: a fold over a few lines
  is over-structuring (STR-05). One fold, closed by default (no `open`).
