# Test corpus

Documents for trying the skill end to end on real input. They are inputs only:
run records, rewrites and reviews stay in each run's directory, outside the
repository. `manifest.json` lists each document with its genre, language,
origin and generation prompt, what it exercises, and the
detector's result at `baseline_commit`.

Every document here was written for testing; none is anyone's real
publication. Unlike `examples/`, nothing here is a test fixture: no test reads
these files, and a changed baseline is a signal to look at, not a failure.

## Layout

One directory per genre the document is run with, covering all 11 of the
skill's genres. The file name says what the document is and its language
(`-ja`, `-en`).

| Path | Genre | Lang | Generator | Scenario |
|---|---|---|---|---|
| `general/job-change-linkedin-en.md` | general | en | codex | personal: LinkedIn post about a job change |
| `general/time-tracking-landing-en.md` | general | en | claude | marketing: landing page copy |
| `general/career-self-pr-ja.md` | general | ja | claude | 転職：職務経歴書の自己PR |
| `general/cloud-accounting-press-release-ja.md` | general | ja | codex | 広報：新サービスのプレスリリース |
| `general/remote-work-faq-ja.md` | general | ja | agy | 人事：社内制度の FAQ |
| `general/weekly-meeting-minutes-ja.md` | general | ja | claude | チーム運営：定例会議の議事録 |
| `reference/invoices-api-reference-en.md` | reference | en | codex | developer docs: REST endpoint reference |
| `reference/deploy-cli-reference-ja.md` | reference | ja | claude | 開発ドキュメント：CLI コマンドのリファレンス |
| `reference/invoices-api-reference-ja.md` | reference | ja | codex | developer docs: REST endpoint reference |
| `tutorial/github-actions-ci-tutorial-en.md` | tutorial | en | claude | tutorial: CI setup step by step |
| `tutorial/docker-postgres-tutorial-ja.md` | tutorial | ja | agy | 入門記事：手順を追うチュートリアル |
| `tutorial/github-actions-ci-tutorial-ja.md` | tutorial | ja | claude | tutorial: CI setup step by step |
| `article/back-to-monolith-blog-en.md` | article | en | claude | engineering blog: opinion piece |
| `article/product-launch-blog-en.md` | article | en | agy | company blog: product announcement |
| `article/code-review-ja.md` | article | ja | subagent | 社内ブログ：チーム運営のノウハウ記事 |
| `article/new-grad-first-year-long-ja.md` | article | ja | claude | 長文コラム：6000 字を超える記事 |
| `article/rust-ownership-intro-ja.md` | article | ja | codex | 技術ブログ：初心者向けの解説記事 |
| `readme/logpipe-en.md` | readme | en | subagent | OSS: README for a CLI tool |
| `readme/date-utils-readme-ja.md` | readme | ja | codex | OSS：ライブラリの README |
| `spec/feature-flags-rfc-en.md` | spec | en | claude | engineering: RFC for a new internal service |
| `spec/equipment-requirements-ja.md` | spec | ja | agy | 業務システム：要件定義書 |
| `spec/feature-flags-rfc-ja.md` | spec | ja | claude | engineering: RFC for a new internal service |
| `spec/rate-limit-design-ja.md` | spec | ja | subagent | 設計：社内マイクロサービスの設計書 |
| `pr/http-retry-pr-en.md` | pr | en | codex | code review: pull request description |
| `pr/login-validation-pr-ja.md` | pr | ja | claude | コードレビュー：PR の説明文 |
| `message/cold-outreach-email-en.md` | message | en | claude | sales: cold email to a prospect |
| `message/incident-progress-slack-ja.md` | message | ja | codex | 業務連絡：障害対応の進捗を上司に Slack で報告 |
| `message/invoice-misdelivery-apology-ja.md` | message | ja | agy | 顧客対応：請求書の誤送付についての謝罪メール |
| `changelog/js-library-changelog-en.md` | changelog | en | codex | release: CHANGELOG entry |
| `changelog/app-store-release-notes-ja.md` | changelog | ja | claude | リリース：App Store のアップデート内容 |
| `template/checkout-postmortem-en.md` | template | en | subagent | incident response: postmortem template |
| `template/weekly-status-template-en.md` | template | en | codex | team ops: reusable weekly status report template |
| `template/delivery-delay-mail-ja.md` | template | ja | subagent | 取引先対応：納期遅延を伝えるメールの文面 |
| `template/study-group-proposal-ja.md` | template | ja | subagent | 社内企画：制度の立ち上げ企画書 |
| `template/tsumiki-release-post-ja.md` | template | ja | subagent | 告知：アプリのリリースを X に投稿 |
| `prompt/code-review-system-prompt-ja.md` | prompt | ja | subagent | AI 運用：コードレビュー用アシスタントのシステムプロンプト |

Every document was generated from the prompt recorded in the manifest, which
asks for the document the way an ordinary user would and never mentions this
skill or asks for brevity. Generators were a Claude Code subagent, the `claude`
CLI, `codex exec` and `agy`, each run from an empty directory. Answers are
saved unedited except where `notes` in the manifest says otherwise (one outer
code fence removed). Three prompts asked for English and got Japanese; those
answers are kept as `-ja` documents and the English versions were regenerated
with "Write it in English." added.

## Running the detector on the corpus

```sh
python3 -c 'import json; [print(d["genre"], "corpus/" + d["path"], "{hits} hits, {open} open, {exempt} exempt".format(**d["baseline"])) for d in json.load(open("corpus/manifest.json"))["documents"]]' |
while read genre file baseline; do
  printf '%s (baseline: %s)\n  ' "$file" "$baseline"
  python3 skills/deslop/scripts/detect.py --quiet --genre "$genre" -- "$file" 2>&1
done
```

Each document prints its recorded baseline above the current summary line,
so a difference shows without a separate comparison.

For a full run, snapshot a document in copy mode with its genre
(`snapshot.py <out> --root corpus/<genre> --copy --genre <genre> <path>`) and
follow `skills/deslop/SKILL.md`.

## Known gaps

- Every generator ran with the requester's global instructions present
  (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, as
  recorded per document). They may make the drafts plainer than a default
  model would write; `claude --bare` avoids them but cannot log in here.
- No human-written document, no document with a distinct author's voice, and
  no generated draft edited by a person.
- `readme`, `pr` and `changelog` have two documents each, one per language.
- `prompt` has one Japanese document, and its generator already wrote it as a
  specification (0 hits, 0 cues); no persona- or exhortation-heavy prompt is
  in the corpus yet.
- Legal text, slides and `.docx`/`.pdf` sources are out of the skill's scope
  and have no entry.
