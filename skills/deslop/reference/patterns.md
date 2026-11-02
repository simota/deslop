# Patterns

**Read when:** DETECT (what each `detect.py` rule id means) and REWRITE
(deciding what an occurrence becomes).

Every rule in `scripts/rules.json` has an entry here; the test suite fails when
the two disagree. Tiers:

- **artifact** — residue of a chat session. Never legitimate in a finished
  document: delete it. Exemptable only inside a quotation
- **lexical** — words and phrases models overuse. Each occurrence is decided in
  context: rewrite the claim, delete it, or exempt it with a specific reason
- **content** — checks on what a passage claims rather than how it is
  worded (`CNT-01`). Decided with the content perspectives in
  `reference/content.md`
- **density** — document-level measures, checked once the document has at least
  400 characters of prose (`DEN-05` and `DEN-06` from 1,500, set by the rule's
  `min_chars` in `scripts/rules.json`). The fix is structural, not one word

The direction under each rule is the default move, not a substitution table.
Swapping a listed word for its nearest synonym keeps the tell.

The lists draw on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
the excess-vocabulary studies of PubMed abstracts ([Kobak et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12219543/),
[Juzek and Ward 2025](https://arxiv.org/abs/2412.11385)), the trope catalogue at
[tropes.fyi](https://tropes.fyi/directory), and Japanese write-ups of AI-style
Japanese ([Zenn](https://zenn.dev/fibujrsl/articles/4958a844214709),
[note](https://note.com/asakurayane/n/n22c830839687),
[aiproof](https://aiproof.jp/blog/ai-text-features)). Wikipedia's page and the
trope catalogues warn that a single tell proves nothing: a hit is a
candidate, and many hits together are the signal.

## Artifact

### `ART-01`
English chat opener (`Certainly!`, `Sure, here's`, `Great question.`), also
after a list marker or bold. `Of course, the cache…` in ordinary prose does not
match. Delete the opener; start with the first sentence that carries content.

### `ART-02`
Japanese chat opener (`もちろんです`, `承知しました`). Delete it.

### `ART-03`
English chat closer (`I hope this helps`, `Happy coding!`, `You're absolutely
right!`, `Would you like me to`, `Is there anything else I can`). Delete. If the
document needs a contact route, state the route (`Issues go to the tracker
at …`). Follow-up invitations are `EN-20`.

### `ART-04`
Japanese chat closer (`参考になれば幸いです`, `いかがでしたか`). Delete. A real
contact route is stated plainly. Invitations to ask are `JA-21`.

### `ART-05`
The model referring to itself (`As an AI language model, I`, knowledge cutoff
such as `as of my last knowledge update`,
`AIとして、` opening a sentence). A document about AI products that says a tool
runs `as an AI agent`, or an author who writes `As an AI researcher, I`, does
not match.
Delete the sentence; if it carried a real limit (data current to a date), state
the limit as a fact with its date, if the document gives one.

### `ART-06`
Citation and tracking tokens from chat interfaces (`【4†source】`,
`turn0search1`, `contentReference[oaicite:2]`, `utm_source=chatgpt.com`,
`utm_source=openai`, `utm_source=copilot.com`, `referrer=grok.com`).
Remove the token; keep the real link without the tracking parameter. A claim
whose only source was the token loses its citation: list it under `decisions`.

### `ART-07`
Unfilled placeholder (`[Insert company name]`, `【会社名】`, `[取引先会社名]`,
`〇〇株式会社`, `〇名`, `○月○日`,
`[リンク]`, template fields such as `[HH:MM]`, `[N]`, `[link]`, `[YYYY-MM-DD]`,
a date such as `2025-XX-XX`, `INSERT_SOURCE_URL_30`,
`PASTE_YOUTUBE_VIDEO_URL_HERE`); a Markdown link such as
`[Your first project](tutorial.md)` or `[リンク](…)` does not match, nor does
a `[label]` that a valid reference definition in the document resolves, `[N/A]`,
the zero in a kanji numeral (`二〇二〇年`, `一〇〇円`) or a `○` used as a
bullet (`○日時`). In a
document meant to be filled in by its user (a postmortem template, a mail
draft with `[担当者名]`), give it the `template` genre, which exempts this
rule and no other artifact rule. Never fill it
with an invented value: list it under `decisions` and leave a visible marker
only if the requester wants the draft to keep it. Remove only the marker and
the words that depend on it (`〇名規模のチームで` → `チームで`); the sentence
and its claim stay.

Examples inside code, front matter or HTML blocks do not define references.
A valid definition may wrap onto the next line or sit in a list or quote.
An escaped `\[Your Name]` remains a literal placeholder rather than a link.

### `ART-08`
English response framing (`Here's a revised version`, `Below is the summary`).
Delete; the document is the content, not a reply about it.

### `ART-09`
Japanese response framing (`以下に〜をまとめました`, `こちらが〜です。`).
Delete.

## English lexical

### `EN-01`
Verbs whose frequency jumped after chat models arrived: `delve`, `showcase`,
`garner`, `bolster`, `boasts` (for "has"). Use the verb for what actually
happens (`covers`, `shows`, `gets`, `has`), or cut the sentence that announces
the topic.

### `EN-02`
Ornamental nouns: `tapestry`, `a testament to`, `in the realm of`,
`the landscape of`, `interplay`, `intricacies`, `cornerstone`, `beacon of`. Name the subject directly (`in databases`, not `in the
realm of databases`).

### `EN-03`
Inflated verbs: `leverage`, `harness`, `unlock the power`, `empower`,
`elevate`, `streamline`, `foster`, `supercharge`. Say `use`, `let`, `make
faster`, or what concretely changes; often the sentence can go.

### `EN-04`
Promotional adjectives: `seamless`, `robust`, `cutting-edge`, `innovative`,
`holistic`, `game-changing`. Replace with the property and its evidence from
the document (`retries three times`, `no restart needed`) or delete. Exempt
established terms (`robust statistics`, `robust regression`).

### `EN-05`
Importance asserted: `plays a crucial role`, `is pivotal`, `of paramount
importance`. Show why it matters, with the document's own consequence, or
state the fact without the rating.

### `EN-06`
Throat-clearing: `It's important to note`, `It's worth noting`, `Notably,`.
Delete the frame; keep the note.

### `EN-07`
Scene-setting openers: `In today's fast-paced world`, `in the digital age`.
Delete; begin with the document's subject.

### `EN-08`
Formulaic wrap-up: `In conclusion`, `In summary`, `Overall`, `Ultimately` at
the start of a sentence. Delete the paragraph if it restates the body; keep
only a new consequence or next step.

### `EN-09`
Connective stacking: `Moreover,`, `Furthermore,`, `Additionally,`. Usually
delete; the order of sentences already says "and". Use `but`, `so`, `because`
when the relation is real.

### `EN-10`
Reflexive contrast: `isn't just X, it's Y`, `It's not X — it's Y`, `It's not
about X; it's about Y`, `more than just`, `is not merely`, `not only … but
also`. State Y.
Keep a contrast only when someone actually believes X.

### `EN-11`
Journey metaphors: `embark on`, `a journey of`, `navigate the complexities`.
Name the task (`set up`, `migrate`, `handle`).

### `EN-12`
Signposted dives: `Let's dive into`, `deep dive`, `Let's explore`, `Let's
break this down`. Delete and
start the explanation.

### `EN-13`
Significance verbs: `underscores`, `highlights the importance`, `serves as a
reminder`, `stands as`. State the fact the significance rested on.

### `EN-14`
Intensifiers standing in for detail: `intricate`, `meticulous`, `nuanced`,
`comprehensive`, `a wide range of`, `myriad`, `vibrant`, `pivotal` before a
noun (`a pivotal moment`; `is pivotal` and `a pivotal role` are `EN-05`). Give
the detail or the count, or delete the adjective.

### `EN-15`
Audience widening: `whether you're a beginner or an expert`. Name the actual
reader once, near the top, or delete.

### `EN-16`
Stacked hedges: `can potentially`, `might possibly`, `arguably`, `to some
extent`. One hedge where uncertainty is real, with its condition; none where
the document knows.

### `EN-17`
Marketing enthusiasm: `we're excited`, `look no further`, `next level`.
Delete; describe the change.

### `EN-18`
Staged reveal: `Here's the thing`, `The result?`, `Let that sink in`,
`Imagine a world where`. Write the statement directly.

### `EN-19`
Template section names: `Key takeaways`, `Final thoughts`, `Wrapping up`.
Remove the section if it repeats the body; otherwise give it a heading that
names its content.

### `EN-20`
Follow-up invitation (`Let me know if you have any questions`, `Feel free to
reach out`). Delete it from documents. In an email or message to a person it
is the genre's convention, and the `message` genre exempts it.

### `EN-21`
A trailing `-ing` clause that assigns significance (`, highlighting its
importance`, `, reflecting the broader trend`, `, contributing to the`). It
claims a meaning the sentence has not shown. Cut the clause; if the
consequence is real and in the document, state it as its own sentence.

### `EN-22`
`serves as a`, `stands as the` where `is` says the same (`The file serves as
the entry point` → `The file is the entry point`). Keep it when the thing
really does stand in for something else (`a stub serves as the server in
tests`), and exempt that occurrence.

### `EN-23`
Legacy and brochure puffery: `key turning point`, `watershed moment`,
`indelible mark`, `deeply rooted`, `lasting impact`, `setting the stage for`,
`evolving landscape`, `rich cultural heritage`, `nestled in`, `in the heart
of`, `breathtaking`. Replace with the fact behind it (a date, a number, what
changed) or cut it.

### `EN-24`
Unnamed authority: `experts agree`, `industry reports suggest`, `observers
have noted`, `some critics argue`, `studies show that`. Name the source the
document cites; if it cites none, cut the attribution and keep the claim only
if the document supports it, listing the missing source under `decisions`.

### `EN-25`
Disclaimers about the model's own sources: `while specific details are
limited`, `is not widely documented`, `based on available information`, `in
the provided sources`. They describe the chat session, not the subject.
Delete; a real gap in the record is stated plainly (`the release date is not
published`). A disclaimer that the document's own specifics were not verified
or were invented (`the options below are assumed`) is such a gap: never
delete it alone, or invented values read as fact. Restate it as a plain
sentence in the document and list it under `decisions` (CON-03). A statement
of what kind of document it is (`this page is an example spec`) is part of
that limit and stays.

### `EN-26`
The closing formula `Despite these challenges, …` and headings such as
`Challenges and Future Prospects` or `Future Outlook`. Keep a limitation or a
plan the document actually has, under a heading named for it; cut the
optimistic wrap-up.

### `EN-27`
Invented scenario in place of a real example: `Imagine you're a developer
who…`, `Picture this`, `Let's say you`, `Consider the following scenario`.
Use an example the document actually has, or drop the scenario and state the
point (CON-04).

## Japanese lexical

### `JA-01`
結論をぼかす文末（`〜と言えるでしょう`、`〜ではないでしょうか`）。根拠がある
なら言い切る。根拠がないなら条件を書くか、その文を削る。

### `JA-02`
`〜と言っても過言ではありません`。誇張を外して事実だけを書く。多くは削除で足りる。

### `JA-03`
重要さの宣言（`〜が重要です`、`重要な役割を果たします`、`鍵となります`）。
なぜ重要かを文書内の帰結で示すか、評価語を外して事実だけ残す。

### `JA-04`
`〜することができます`。`〜できます` にする。主語と動詞がはっきりするなら
`〜します` で足りることも多い。

### `JA-05`
翻訳調の前置き（`〜という点において`、`〜という観点から`）。前置きを外し、
何についての文かを主語で示す。

### `JA-06`
中身のない宣伝語（`シームレス`、`包括的`、`革新的`、`新たな可能性`、
`最大限に引き出す`、`飛躍的に`、`強力な`、`直感的な`、`堅牢な`）。測れる性質と文書内の根拠に置き換えるか削る。

### `JA-07`
`〜することで、〜が可能になります` 型の効能文。何をすると何が起きるかを具体的に
書く（`ヒットした要求はディスクを読まない`）。

### `JA-08`
内容の予告（`本記事では〜を解説します`）。削除して本題から始める。

### `JA-09`
本文の繰り返しで終わる締め（`## まとめ`、`まとめると、`、`総じて、`、
`以上、〜について解説しました`）。本文を
繰り返すだけなら節ごと削る。新しい結論や次の手順だけを残す。

### `JA-10`
読者への勧誘（`〜してみてはいかがでしょうか`、`ぜひ〜ください`）。手順なら命令形や
`〜します` で書き、勧誘は削る。勧誘の形でも、記事が何に着目するかを伝えている文
（`〜に注目してみましょう`）は削らず、着眼点を平叙文で書く。

### `JA-11`
言い直し（`つまり、`、`言い換えると、`）。前の文が分かりにくいならそちらを直し、
言い直しの文を削る。

### `JA-12`
反射的な対比（`単なる〜ではなく`、`〜だけでなく〜も`）。主張したい側だけを書く。

### `JA-13`
列挙の定型句（`〜が挙げられます`、`〜には3つの理由があります`、`まず1つ目は`）。`〜は次の2つです` のように数と中身を直接書くか、
文に溶かす。

### `JA-14`
探求・冒険の比喩（`深掘り`、`紐解く`、`〜への旅`、`徹底解説`、`完全ガイド`）。
何をするのかをそのまま書く。

### `JA-15`
情緒的な宣伝語（`寄り添う`、`一人ひとりに合わせた`、`あなたの未来`）。具体的な
機能や条件に置き換えるか削る。

### `JA-16`
出典のない動向（`〜が期待されます`、`注目を集めています`、`今後ますます`）。
出典があればそれを示し、なければ削る。

### `JA-17`
SEO記事型の見出し（`〜とは？`、`〜のメリット`、`〜のポイント`）。節の中身を
名詞句で名付ける（`## 設定項目`）。中身が薄ければ見出しごと前後の節に統合する。

### `JA-18`
具体例の代わりの「さまざまな〜」（`さまざまな用途`、`幅広いニーズ`）。文書にある
用途を挙げるか削る。

### `JA-19`
過剰な丁寧表現（`〜となっております`）。`〜です` にする。ビジネスメールの
挨拶 `お世話になっております` は定型句なので当たらない。

### `JA-20`
和文中のダッシュ（`——`）。読点、括弧、または文を分けて書く。

### `JA-21`
問い合わせへの誘い（`ご不明な点があれば`、`ご不明な点がございましたら`、
`お気軽にご質問ください`、`お気軽にお申し付けください`）。文書からは削除し、
窓口が必要なら窓口そのものを書く。人宛てのメールやメッセージでは慣習なので、
`message` ジャンルが除外する。メールの下書きを `template` で扱うときは、
`message` の慣習として手で除外する。

### `JA-22`
文頭の `さらに、`、`加えて、`、`このように、`。段落を順に積むだけの接続詞は削る。
`このように、` で始まる文が前の段落の言い直しなら文ごと削る（STR-03）。前の文と
本当に論理関係があるなら、その関係（理由、条件、対比）が分かる書き方にする。

### `JA-23`
本題の前の道案内（`見ていきましょう`、`詳しく解説します`、`それでは早速`）。
削除して本題から始める。手順の導入なら何をするかだけを書く。

### `JA-24`
`XはYを可能にします`。英語の "X enables Y" の直訳。`Xを使うとYできます`、
`XでYします` のように、誰が何をするかを動詞で書く。

### `JA-25`
重ねたぼかし（`可能性があるかもしれません`、`場合もあるかもしれません`）。
ぼかしは一つで足りる。条件が分かっているなら条件を書いて言い切る。

### `JA-26`
読者の悩みを想定する問いかけ（`〜と思ったことはありませんか`、
`〜でお困りではありませんか`）。記事冒頭の定型なので削り、対象読者が必要なら
`〜する人向けです` と一文で書く。

### `JA-27`
`A、B、そしてC`。英語の "A, B, and C" を写した列挙で、日本語では最後の項目の前に
`そして` を置かない。`A、B、C` か `AとBとC` にする。動作を順に並べる文
（`起動し、設定を読み、そして待機する`）は対象外なので、そう書いて除外する。

### `JA-28`
名言風の締め（`大切なのは〜です`、`〜が成功への鍵です`、`〜への第一歩`）。
中身のない教訓なら削る。具体的な行動を指しているなら、その行動を手順として書く。

### `JA-29`
結論を避ける両論併記（`一概には言えません`、`メリットもデメリットもあります`、
`自分に合った方法を選びましょう`）。文書が判断の材料を持っているなら、どの条件で
どちらを選ぶかを書く。持っていないなら削る。

### `JA-30`
和文中の欧文引用符（`“設定”`）。和文では `「」` を使う。英文の引用や UI の文言を
そのまま示す場合は除外する。

### `JA-31`
出典を示さない伝聞と多数派への言及（`〜と言われています`、`〜とされています`、
`調査によると`、`多くの企業が`）。文書が出典を挙げているならそれを名指しする。
挙げていないなら伝聞の枠を外し、文書が裏づける部分だけを残す（CON-08）。

### `JA-32`
実例の代わりの架空の場面（`想像してみてください`、`例えば、あなたが`、
`Aさん（仮名）`、`とある企業`）。文書に実例があればそれを使い、なければ場面を削って
言いたいことを直接書く（CON-04）。

### `JA-33`
生成モデル自身の断り書き（`実際の仕様は確認できていません`、`以下のフィールドと
動作を仮定しています`、`一般的な〜を参考にした仮の内容です`、`仕様例です`）。
依頼者に向けた口調は消すが、断り書きそのものは消さない。`本ページは仕様例です。`
のように文書の種類を述べる一文も、その限界の一部なので残す。内容が未確認・仮定で
あることは文書の本当の限界で、消すと作られた値が確定した仕様に読める。
`以下のオプションと終了コードは未確認の仮案です。` のように平叙文で本文に残し、
`decisions` に挙げる（CON-03）。平叙文がなおこのルールに当たるときは、その理由で
除外する。

### `EMO-01`
飾りの絵文字（見出しや箇条書きの頭の 🚀 ✅ ✨ ⏱）。削除する。UI の文言を
そのまま引用している場合、比較表のセルで対応の有無を示す ✅ / ❌、状況欄で
進捗を示す信号色 🟢 🟡 🔴 だけ除外できる（`text` にその記号を指定する）。
信号色を外すなら、同じ欄の文字の状態表記（On track など）を必ず残す。表の勝ち負けを飾る 🏆 😱 は
削除する。

## Content

### `CNT-01`
A percentage or multiplier (`30%`, `2倍`, `3割`) stated as a claim: its
sentence names a population (`企業`, `users`), a change (`向上`, `削減`,
`faster`) or an approximation (`約` before an amount, `程度`, `about`), and its paragraph has no link, footnote, named source, stated
assumption (`仮定`, `estimate`) or measurement (`63 → 27 ms`). Table rows and
ranges such as `15-30%`, `15 - 30%` and `15% - 30%` are not checked.
A source in a different Markdown block, such as the next list item or a
section after a heading, does not support the claim's paragraph.
Generated drafts invent such
figures. Do not look
for a source and do not change the number: if it is decoration, delete the
sentence and record the value in `preservation`; if the document depends on
it, keep it and list it under `decisions` as needing a source, then exempt
the hit with that reason. A figure measured in the document itself (a
benchmark table, a log) is exempted with that named (CON-03).

## Density

Heading metrics and structural cues recognize ATX headings (`## Title`)
and Setext headings (a title underlined by `===` or `---`). An underline
after a blank line remains a separator, and code examples are excluded.

A density hit that stands only because the structure is real (one section per
code sample, three facts that are three, a page of flags) is exempted with that
structure named. Never move a ratio by restructuring: no merging sentences to
pass DEN-08, no folding a list or removing a heading to pass DEN-05 or DEN-06.

### `DEN-01`
Bold spans per 1,000 prose characters above 3. Keep bold for the one term a
reader must not miss per section, or for UI labels; remove the rest.

### `DEN-02`
Em dashes per 1,000 characters above 1.5 (English). Use commas, parentheses,
a colon, or two sentences.

### `DEN-03`
Over 5% of sentences end in `!`. Expository text states; remove them.

### `DEN-04`
Three or more `**Label**: explanation` or `**Label:** explanation` bullets. Write the items as prose, or
as a plain list or table when the reader scans them (the `reference` genre
exempts it). A block of short field labels with values (`日時`, `場所`,
`Owner`, `Due`, `Status`) is a form the reader fills in or scans, not prose
cut into pieces: keep its bold and exempt the hit naming the block (the
`template` genre exempts it).

### `DEN-05`
More than 5 headings per 1,000 prose characters, checked from 1,500
characters of prose: below that a title and a few sections decide the rate.
Merge thin sections; keep a heading only where a reader would navigate to it.

### `DEN-06`
More than 60% of body lines are list items (10 lines or more), checked from
1,500 characters of prose: below that one checklist decides the share. Turn
reasoning back into sentences; keep lists for steps, options and inventories.

### `DEN-07`
Four or more consecutive Japanese sentences ending in the same three
characters (`〜できます。` ×4). Hard-wrapped lines are joined into their
paragraph first, and a `。` inside `「」` or `『』` does not end a sentence. A
heading or a table ends the run; a blank line between paragraphs does not.
Combine sentences, change which part comes last, or cut one. Do not vary endings at random; vary them because the
sentences say different kinds of things.

### `DEN-08`
Sentence-length coefficient of variation below 0.3 over eight or more
sentences: every sentence the same length. Merge related short sentences and
split overloaded ones where the content asks for it.

### `DEN-09`
Three or more `X, Y, and Z` lists (English). Keep the items that matter; two
items or four are fine when that is how many there are.

### `DEN-10`
Three or more horizontal rules (`---`, `***`) between sections. Headings already
separate sections; remove the rules. A slide deck or a document whose format
uses rules as separators is a genre exemption.
