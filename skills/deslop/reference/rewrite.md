# Rewriting

**Read when:** INVENTORY and VOICE (genre and voice rules), and REWRITE
(how a change is made and recorded).

## Order of work

Work on one document at a time. Apply these passes within each of its three
candidates, starting each candidate from the same original as described in
`reference/comparison.md`:

1. **Content.** Run the content pass first (`reference/content.md`): every
   claim through the information, substitution, reader and support tests.
   Whatever fails goes before anything is reworded; there is no point
   polishing a sentence that will be cut
2. **Structure.** Then the structural perspectives (`reference/structure.md`):
   remove the announced opening and the restating close, merge thin sections,
   turn bullets that carry one argument back into prose. Most lexical hits
   disappear with the sentences that held them
3. **Sentences.** For each remaining sentence with a hit, ask what it says.
   If nothing: delete. If something: write that thing directly, using nouns
   and numbers already in the document
4. **Words.** Last, single words (`JA-04`, `JA-19`, `EN-09`) and punctuation
   (`JA-20`, `DEN-02`)

Review and score the candidates before copying the selected one to the
working file. Then rerun `detect.py --snapshot <out> --exempt
<out>/findings.json` and repeat until it exits 0. If that requires an edit,
update the selected candidate and repeat its review and the selection.

## How a change is made

- **Delete first.** A sentence that only rates, announces, restates or
  encourages is removed. A sentence that addresses the reader but also names
  what the document looks at (`値を誰が管理しているかに注目してみましょう`)
  is rewritten as a plain statement of that focus, not deleted. Deletion never loses information when the sentence
  had none. Before deleting one that looks like a restatement, read what it
  adds: a sentence that sets the other case
  (`事前の承認がない残業は認められません` after the approval rule) is a
  separate rule and stays. Cutting items
  from a list must not narrow a claim below what the rest of the document
  supports
- **One list, one treatment.** Remove bold from a whole list or keep it on the
  whole list; a list with some labels bold and others plain reads as an error
- **Specifics come from the document.** Replace `improves performance` with
  the effect the document already describes (`the second request skips the
  disk read`). When the document has no specific, cut the claim and add the
  gap to `decisions` (`the README says "faster" but gives no measurement`)
- **No synonym swaps.** `leverage` → `utilize` or `重要` → `肝心` keeps the
  inflation. Change the claim, not the word
- **Keep meaning and scope.** A requirement stays a requirement; a caveat with
  a real condition stays; the order of steps stays. Cutting a hedge never
  makes a claim stronger than the original: `細部まで確認しやすくなります`
  does not become `細部まで確認でき、レビューも早く終わります`, and a request
  does not become a requirement (`Please include a test` is not `need a
  test`). A degree word
  that narrows the claim (`しやすい`, `少なくなる`, `often`) is content, not
  a hedge
- **Keep the voice.** Use the register, person and terms in `voice`. Japanese
  です・ます stays です・ます. Product terms the author keeps in English stay
  in English. When a sentence is reworded, reuse the author's own verbs and
  nouns; a substitute from another register (`解決する` → `片付ける`) is
  drift (STR-16), not a fix
- **Rhythm follows content.** Combine sentences that state one thing, split
  sentences that state two. Do not vary sentence length or endings for their
  own sake
- **Untouchable:** code blocks, commands, identifiers, URLs, front matter
  keys, quotations, anchors linked from elsewhere, legal text. A renamed
  heading still has to match any place the text names it
  (`「速さの理由」だけ知りたい人は`)

## Japanese

- **Notation is part of the voice.** Record the document's notation in
  `voice` and keep it: spacing between Japanese and Latin text (`Git の設定`
  or `Gitの設定`), full- or half-width brackets, colons and digits, the long
  vowel in katakana terms (`サーバー` or `サーバ`), and kana or kanji for the
  same word (`できる` or `出来る`, `さまざま` or `様々`). Changing any of these
  is drift (STR-16), even toward the more common form
- **Endings vary because content does.** In `です・ます` text most sentences
  end in `です` or `ます`; that alone is not a tell. Monotony is the same verb
  phrase again and again (`〜できます。` four times, DEN-07): merge those
  sentences into one that lists what can be done
- **Leave implicit what Japanese leaves implicit.** Translationese states a
  subject in every sentence (`それは`, `私たちは`, `ユーザーは`), makes verbs
  into nouns (`設定の変更を行う`) and frames sentences with `〜において`. Drop
  a subject the reader already knows and use the verb (`設定を変える`)
- **Katakana is not specificity.** `ソリューション`, `アプローチ` and
  `メリット` stand in for the actual thing just as `solution` does in English.
  Name the thing from the document; keep katakana that is the established term
  or a product name
- **Lists take `、` or `と`.** Not `、そして` before the last item (JA-27)

## Genre

The genre decides which structure is legitimate. Give each document its genre
at INVENTORY with `snapshot.py --genre GENRE` (every file) or
`--genre PATH=GENRE` (one file, or every file below a directory: the
deepest directory wins and a file's own assignment beats any directory's,
so `--genre docs/api=reference --genre docs/api/intro.md=tutorial` works in
either order); a file named `README*` is `readme` and
`CHANGELOG*`, `CHANGES*`, `HISTORY*` or `NEWS*` is `changelog` unless told
otherwise, and anything else is `general`. `detect.py` takes the same flag
when run without a snapshot.

`PATH` may be relative to the current directory or to `--root`. If those
interpretations name different target documents, the command refuses the
ambiguous assignment; use an absolute path to select the intended file.

The genre then does two things in `detect.py`, both defined under `genres` in
`scripts/rules.json`. It exempts the conventions it needs: those hits stay in
the output, marked with the genre, and need no finding or exemption entry.
And it moves density limits, looser where the genre scans and stricter where
it argues in prose. Sentence- and word-level rules still apply everywhere.
A convention the table does not cover is still exempted by hand, with the
genre named.

| Genre | Keep | Remove | Set by the genre |
|---|---|---|---|
| General prose (`general`) | What the content needs | Everything the rules and perspectives name | Default limits |
| README (`readme`) | Install and usage steps as numbered lists, a feature list when it is an inventory, code blocks | Taglines, "Why X?" sections of adjectives, closing invitations | DEN-06 exempt; DEN-05 up to 8 |
| API / reference (`reference`) | Tables, parameter lists, bold for parameter names, terse fragments | Narrative openers, importance claims | DEN-01, DEN-04, DEN-05, DEN-06, DEN-08 exempt |
| Tutorial (`tutorial`) | Numbered steps, one heading per step, a short statement of the result up front | Signposting between every step, praise of the reader, recap sections | DEN-05, DEN-06 exempt; DEN-03 at 0 |
| Blog / article (`article`) | Headings every few paragraphs, the problem the article answers and a point of view, each stated once | SEO headings, FAQ padding, `まとめ` that repeats the body | DEN-01 1.5, DEN-04 0, DEN-05 3, DEN-06 0.3 |
| Spec / RFC (`spec`) | `MUST`/`SHOULD`, numbered requirements, rationale sections | Hedges on requirements, promotional framing | DEN-05, DEN-06, DEN-08 exempt; DEN-03 at 0 |
| PR description (`pr`) | What changed, why, how it was tested; past one screen, an opener and the rest in one `<details>` (STR-17) | Section templates left empty, headings over single lines, emoji | DEN-06 exempt; DEN-03 and DEN-10 at 0 |
| Email / message (`message`) | Greeting and sign-off customary in the language, an invitation to reply | Chat closers, restated requests, stacked apologies | EN-20, JA-21 exempt; DEN-04 0, DEN-05 0, DEN-06 0.3 |
| Changelog (`changelog`) | One bullet per change | Adjectives on changes (`powerful new`) | DEN-05, DEN-06, DEN-08 exempt |
| Template (`template`) | The fields its user fills in (`[name]`, `[HH:MM]`, `〔 〕`), one per item the user must supply, with their bold labels | Chat residue, filler around the fields, invented values put in a field | ART-07 exempt (the one artifact rule a genre may exempt); DEN-04 exempt |

Pick the genre from what the document is for, not from where it lives: a
`docs/` page that walks through setup is a `tutorial`, a blog post saved as
`README.md` is an `article`. Slide text has no entry: use `general` and
exempt its rules (DEN-10) by hand. The report lists each file's genre and
what it changed.

A `pr` description of 20 non-blank lines or more is folded (STR-17 in
`reference/structure.md`): an opener the reviewer can stop after, what the
reviewer must act on, then one `<details>` block holding the rest. The text
inside the fold is rewritten like the text outside it. Give the three
candidates different openers and a different split between what stays
visible and what is folded.

In every genre, `✅` / `❌` as the cell values of a comparison table, and
`🟢` / `🟡` / `🔴` as the value of a status field, are conventions: exempt those
EMO-01 hits by hand with the mark as `text`. The
same marks heading bullets, and any emoji decorating a result, are removed.

## Recording

Write a fragment per batch of one to five findings into scratch and merge it
(`reference/findings-schema.md`). One finding per document and rule: count the
occurrences, show one representative `before`/`after` pair, and set `action`:

- `deleted` — the text was removed
- `rewritten` — the text was replaced by a direct statement
- `restructured` — the change was to structure (sections, lists, order)
- `exempted` — kept on purpose; add the matching `exemptions` entry with the
  reason specific to the occurrence

When a deleted sentence carried a number, URL or link target, inline code or footnote that no
longer appears anywhere in the document, add a `preservation` entry: the value,
its kind and why losing it is intended. When the rewrite introduces a value the
original never contained, that is almost always an invented fact: undo it
instead of acknowledging it.
