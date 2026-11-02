# Findings schema

**Read when:** writing any fragment for `scripts/findings.py merge`, and at
REPORT.

`findings.json` is the run record; `report.md` is rendered from it. Fragments
are JSON files written with the host's file-write tool into scratch, then
merged. `meta` and `voice` update by key; `findings` and `perspectives` replace
an entry with the same `id` or append; `comparisons` replaces by document
`path` or appends; the lists `exemptions`, `preservation`,
`limitations` and `decisions` append unless an identical entry exists. The
merged record is checked before it is written, so a bad fragment changes
nothing; the first fragment of a run must therefore carry `meta` and `voice`.
Each finding ID and perspective ID must occur once within a record or
fragment. Update an entry by merging a new fragment with that ID, not by
appending a second entry to the same list. A duplicate rejects the merge
before the saved record changes.

The report keeps complete document paths, excerpts, protected values and
reasons. It escapes recorded text so Markdown or HTML inside a quotation
cannot become report structure. Explanatory text is folded onto one line;
file names keep their significant spaces and use JSON string notation when
control characters need to be shown.

For the three-candidate workflow, include one `comparisons` entry per snapshot
document. Its full shape is in `reference/comparison.md`. Merge a complete
replacement entry when a candidate, review or selection changes; do not
append another entry for the same path. Old records without comparisons
remain valid, but a snapshot made with `--compare` requires them before the
contract can pass. Candidate acknowledgements belong inside their candidate
records; the top-level change and acknowledgement lists describe the final
selected text only.

An exemption covers only the occurrences it matches, in both the original
and the rewrite. When a term of art is exempted but another occurrence of
the same rule is removed, record that removal as a finding.

```json
{
  "schema_version": 1,
  "meta": {
    "target": "/path/to/docs",
    "lang": "ja",
    "mode": "in-place",
    "assessor": "Claude Code (<model>)",
    "date": "2026-10-31"
  },
  "voice": {
    "source": "samples",
    "rules": [
      "です・ます調、読者を「あなた」と呼ばない",
      "製品名と設定名は英語のまま、コード書式で書く"
    ]
  },
  "findings": [
    {
      "id": "T-001",
      "path": "docs/cache.md",
      "rule": "JA-04",
      "occurrences": 3,
      "action": "rewritten",
      "before": "有効期限を設定することができます。",
      "after": "有効期限を設定できます。"
    },
    {
      "id": "T-002",
      "path": "docs/cache.md",
      "rule": "STR-02",
      "occurrences": 1,
      "action": "deleted",
      "before": "## まとめ（本文の繰り返し 3 文）"
    }
  ],
  "perspectives": [
    {"id": "STR-01", "result": "applied", "note": "冒頭の予告文を削除 (T-003)"},
    {"id": "STR-14", "result": "N/A", "note": "見出しは 1 つだけ"}
  ],
  "exemptions": [
    {"path": "docs/stats.md", "rule": "EN-04", "text": "robust", "reason": "term of art: robust regression"}
  ],
  "preservation": [
    {"path": "docs/cache.md", "kind": "number", "value": "3", "reason": "「以下の3つ」の前置き文ごと削除"}
  ],
  "limitations": [],
  "decisions": ["性能向上の主張に測定値がない（docs/cache.md 末尾）"]
}
```

| Field | Rule |
|---|---|
| `meta.lang` | `ja` or `en`; the report's language |
| `meta.mode` | `in-place` or `copy`; must match `snapshot.json` |
| `voice.source` | `documented` (style guide), `samples` (the author's own text), `inferred` (genre default) |
| `voice.rules` | At least one rule; three to eight is typical |
| `findings[].id` | `T-NNN`, unique |
| `findings[].path` | Relative to the snapshot root, as `detect.py` prints it |
| `findings[].rule` | A rule id from `rules.json` or an `STR-NN` or `CON-NN` perspective |
| `findings[].action` | `deleted`, `rewritten`, `restructured` or `exempted`. `after` is required for `rewritten` and `restructured`; `reason` and a matching `exemptions` entry for `exempted` |
| `perspectives[]` | One per `STR-NN` and `CON-NN`, `result` `applied`, `N/A` or `not checked`, always with a `note`. `N/A` is refused for a perspective `detect.py` cues in the originals |
| `exemptions[]` | `path`, `rule`, `reason`; `text` narrows it to occurrences containing that text, or contained in that exact surrounding passage, including across line breaks. Without `text` it covers every occurrence of the rule in the file (use for density hits) |
| `preservation[].kind` | `number`, `url` (also a Markdown link or reference-definition target such as `docs/setup.md#install`), `inline_code`, `code_block` (value `sha256:` plus 12 hex digits, as `preserve_check.py` prints it) or `footnote` |

`code_block` remains a recognized diagnostic kind, but a preservation entry
cannot authorize a code block change. Added or removed copies of an existing
block also fail, in both candidate checks and the final check, including
older runs without comparisons. Restore the original blocks before VERIFY.
