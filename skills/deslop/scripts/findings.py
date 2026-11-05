#!/usr/bin/env python3
"""Build, check and render the run record.

    findings.py merge <out>/findings.json <fragment>...
    findings.py check <out>/findings.json
    findings.py report <out>

merge creates the record if needed. `meta` and `voice` update by key;
`findings` and `perspectives` replace by id, `comparisons` by path; `exemptions`,
`preservation`, `limitations` and `decisions` append unless already present.
The merged record is checked before it is written, so a bad fragment
changes nothing. report writes <out>/report.md in meta.lang, stamped with
the SHA-256 of findings.json; both hit counts are recomputed from original/
and the working copies.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import comparison
from common import decode_text, genre_table, load_json, load_rules, sha256_bytes, write_json, write_text
from common import markdown_code
from common import markdown_inline as cell

ACTIONS = {"rewritten", "deleted", "restructured", "exempted"}
RESULTS = {"applied", "N/A", "not checked"}
VOICE_SOURCES = {"documented", "samples", "inferred"}
# Fact kinds compared by preserve_check.py, in its report order.
KINDS = ("code_block", "inline_code", "url", "footnote", "number")
ID = re.compile(r"T-\d{3}")
LISTS = ("exemptions", "preservation", "limitations", "decisions")
OBJECT_LISTS = ("findings", "perspectives", "comparisons", "exemptions", "preservation")
KEYED_LISTS = (("findings", "id"), ("perspectives", "id"), ("comparisons", "path"))


class RecordError(ValueError):
    pass


def known_rules():
    rules = load_rules()
    tiers = {r["id"]: r["tier"] for r in rules["rules"]}
    tiers.update({p["id"]: "perspective" for p in rules["perspectives"]})
    return tiers, [p["id"] for p in rules["perspectives"]]


def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{where} must be a non-empty string")


def check_shape(data, where):
    """Reject wrong JSON types before anything indexes into them."""
    if not isinstance(data, dict):
        raise RecordError(f"{where} must be a JSON object")
    for key in ("meta", "voice"):
        if key in data and not isinstance(data[key], dict):
            raise RecordError(f"{where}: {key} must be an object")
    for key in ("findings", "perspectives", "comparisons", *LISTS):
        if not isinstance(data.get(key, []), list):
            raise RecordError(f"{where}: {key} must be a list")
        if key in OBJECT_LISTS and not all(isinstance(item, dict) for item in data.get(key, [])):
            raise RecordError(f"{where}: every entry of {key} must be an object")
    for key, identity in KEYED_LISTS:
        seen = set()
        for i, item in enumerate(data.get(key, [])):
            text(item.get(identity), f"{where}: {key}[{i}].{identity}")
            if item[identity] in seen:
                raise RecordError(f"{where}: {key}[{i}].{identity} {item[identity]!r} must be unique")
            seen.add(item[identity])


def check_record(data):
    tiers, _ = known_rules()
    check_shape(data, "findings.json")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise RecordError("schema_version must be 1")
    meta = data.get("meta") or {}
    for key in ("target", "assessor", "date"):
        text(meta.get(key), f"meta.{key}")
    if meta.get("lang") not in ("ja", "en"):
        raise RecordError("meta.lang must be ja or en")
    if meta.get("mode") not in ("in-place", "copy"):
        raise RecordError("meta.mode must be in-place or copy")
    voice = data.get("voice") or {}
    text(voice.get("source"), "voice.source")
    if voice.get("source") not in VOICE_SOURCES:
        raise RecordError(f"voice.source must be one of {sorted(VOICE_SOURCES)}")
    if not isinstance(voice.get("rules"), list) or not voice["rules"]:
        raise RecordError("voice.rules must list at least one rule of the author's voice")
    for i, rule in enumerate(voice["rules"]):
        text(rule, f"voice.rules[{i}]")
    seen = set()
    for i, f in enumerate(data.get("findings", [])):
        where = f"findings[{i}]"
        if not ID.fullmatch(f["id"]) or f["id"] in seen:
            raise RecordError(f"{where}.id must be a unique T-NNN")
        seen.add(f["id"])
        text(f.get("path"), f"{where}.path")
        text(f.get("rule"), f"{where}.rule")
        if f.get("rule") not in tiers:
            raise RecordError(f"{where}.rule {f.get('rule')!r} is not in rules.json")
        text(f.get("action"), f"{where}.action")
        if f["action"] not in ACTIONS:
            raise RecordError(f"{where}.action must be one of {sorted(ACTIONS)}")
        if type(f.get("occurrences")) is not int or f["occurrences"] < 1:
            raise RecordError(f"{where}.occurrences must be a positive integer")
        text(f.get("before"), f"{where}.before")
        if f["action"] in ("rewritten", "restructured"):
            text(f.get("after"), f"{where}.after")
        if f["action"] == "exempted":
            text(f.get("reason"), f"{where}.reason")
    for i, p in enumerate(data.get("perspectives", [])):
        if p.get("id") not in tiers or tiers[p["id"]] != "perspective":
            raise RecordError(f"perspectives[{i}].id must be an STR-NN or CON-NN perspective")
        text(p.get("result"), f"perspectives[{i}].result")
        if p["result"] not in RESULTS:
            raise RecordError(f"perspectives[{i}].result must be one of {sorted(RESULTS)}")
        text(p.get("note"), f"perspectives[{i}].note")
    for i, e in enumerate(data.get("exemptions", [])):
        text(e.get("path"), f"exemptions[{i}].path")
        text(e.get("rule"), f"exemptions[{i}].rule")
        if e.get("rule") not in tiers:
            raise RecordError(f"exemptions[{i}].rule is not in rules.json")
        if "text" in e:
            text(e["text"], f"exemptions[{i}].text")
        text(e.get("reason"), f"exemptions[{i}].reason")
    for i, p in enumerate(data.get("preservation", [])):
        text(p.get("path"), f"preservation[{i}].path")
        text(p.get("kind"), f"preservation[{i}].kind")
        if p.get("kind") not in KINDS:
            raise RecordError(f"preservation[{i}].kind must be one of {sorted(KINDS)}")
        text(p.get("value"), f"preservation[{i}].value")
        text(p.get("reason"), f"preservation[{i}].reason")
    for key in ("limitations", "decisions"):
        for i, line in enumerate(data.get(key, [])):
            text(line, f"{key}[{i}]")
    try:
        comparison.check_comparisons(data.get("comparisons", []))
    except ValueError as e:
        raise RecordError(str(e)) from e
    return data


def merge_into(data, fragment, where="fragment"):
    check_shape(data, "findings.json")
    check_shape(fragment, where)
    unknown = set(fragment) - {"schema_version", "meta", "voice", "findings", "perspectives", "comparisons", *LISTS}
    if unknown:
        raise RecordError(f"{where}: unknown top-level keys: {sorted(unknown)}")
    if type(fragment.get("schema_version", 1)) is not int or fragment.get("schema_version", 1) != 1:
        raise RecordError(f"{where}: schema_version must be 1")
    for key in ("meta", "voice"):
        if key in fragment:
            data.setdefault(key, {}).update(fragment[key])
    for key, identity in KEYED_LISTS:
        items = data.setdefault(key, [])
        index = {item.get(identity): n for n, item in enumerate(items)}
        for item in fragment.get(key, []):
            if item.get(identity) in index:
                items[index[item[identity]]] = item
            else:
                index[item.get(identity)] = len(items)
                items.append(item)
    for key in LISTS:
        items = data.setdefault(key, [])
        for item in fragment.get(key, []):
            if item not in items:
                items.append(item)
    return data


def merge(record, fragments):
    path = Path(record)
    data = load_json(path) if path.exists() else {"schema_version": 1}
    for frag in fragments:
        merge_into(data, load_json(frag), str(frag))
    check_record(data)
    write_json(path, data)
    return data


LABELS = {
    "ja": {
        "title": "AI文体除去レポート", "result": "結果", "files": "対象ファイル", "before": "除去前の検出",
        "after": "除去後の未処理", "exempt": "除外", "chars": "本文の文字数", "voice": "著者の文体", "findings": "変更",
        "perspectives": "構造と内容の観点", "exemptions": "除外の理由", "preservation": "意図した事実の変更",
        "limitations": "限界", "decisions": "判断が必要な点", "none": "なし",
        "cols_f": "| ID | ファイル | ルール | 処置 | 変更前 → 変更後 |",
        "cols_p": "| 観点 | 結果 | メモ |", "cols_e": "| ファイル | ルール | 対象 | 理由 |",
        "cols_k": "| ファイル | 種別 | 値 | 理由 |",
        "genres": "文書の種類", "cols_g": "| ファイル | 種類 | ジャンルによる調整 |",
    },
    "en": {
        "title": "AI-style removal report", "result": "Result", "files": "Files", "before": "Hits before",
        "after": "Open after", "exempt": "Exempt", "chars": "Prose characters", "voice": "Author's voice", "findings": "Changes",
        "perspectives": "Structural and content perspectives", "exemptions": "Exemptions", "preservation": "Intended fact changes",
        "limitations": "Limitations", "decisions": "Decisions for a human", "none": "None",
        "cols_f": "| ID | File | Rule | Action | Before → After |",
        "cols_p": "| Perspective | Result | Note |", "cols_e": "| File | Rule | Text | Reason |",
        "cols_k": "| File | Kind | Value | Reason |",
        "genres": "Genres", "cols_g": "| File | Genre | Adjusted for the genre |",
    },
}


def adjustments(genre):
    """One line naming what a genre exempts and which limits it changes."""
    parts = [f"{rid} exempt" for rid in genre["exempt"]]
    parts += [f"{rid} {k} {v}" for rid, bound in genre["limits"].items() for k, v in bound.items()]
    return "; ".join(parts) or "—"


def build_report(out):
    """Return (report.md text, after-summary) for the run as it stands now."""
    import detect

    out = Path(out)
    record = out / "findings.json"
    content = record.read_bytes()
    data = check_record(json.loads(decode_text(content)))
    L = LABELS[data["meta"]["lang"]]
    scanned = detect.scan_snapshot(out, load_rules(), [], originals=True)
    current = detect.scan_snapshot(out, load_rules(), data.get("exemptions", []))
    before, after = scanned["summary"], current["summary"]
    chars = [sum(f["metrics"]["chars"] for f in r["files"]) for r in (scanned, current)]
    names = {p["id"]: p["name"] for p in load_rules()["perspectives"]}
    genres = genre_table(load_rules())
    lines = [
        f"<!-- deslop:findings-sha256={sha256_bytes(content)} -->",
        f"# {L['title']}", "",
        f"- target: {markdown_code(data['meta']['target'])} ({data['meta']['mode']})",
        f"- assessor: {cell(data['meta']['assessor'])} · {cell(data['meta']['date'])}", "",
        f"## {L['result']}", "",
        f"| {L['files']} | {L['before']} | {L['after']} | {L['exempt']} | {L['chars']} |", "|---|---|---|---|---|",
        f"| {after['files']} | {before['total']} | {after['open']} | {after['exempt']} | {chars[0]} → {chars[1]} |", "",
        f"## {L['genres']}", "", L["cols_g"], "|---|---|---|",
        *[f"| {markdown_code(f['path'])} | {genres[f['genre']]['name']} (`{f['genre']}`) | {adjustments(genres[f['genre']])} |"
          for f in current["files"]], "",
        f"## {L['voice']} ({data['voice']['source']})", "",
        *[f"- {cell(r)}" for r in data["voice"]["rules"]], "",
        *comparison.report_lines(out, data, data["meta"]["lang"]),
        f"## {L['findings']}", "", L["cols_f"], "|---|---|---|---|---|",
        *[f"| {f['id']} | {markdown_code(f['path'])} | {f['rule']} ×{f['occurrences']} | {f['action']} | "
          f"{cell(f['before'])} → {cell(f.get('after') or f.get('reason') or '∅')} |"
          for f in data.get("findings", [])], "",
        f"## {L['perspectives']}", "", L["cols_p"], "|---|---|---|",
        *[f"| {p['id']} {names.get(p['id'], '')} | {p['result']} | {cell(p.get('note'))} |"
          for p in data.get("perspectives", [])], "",
    ]
    sections = [
        ("exemptions", L["cols_e"], lambda e: f"| {markdown_code(e['path'])} | {e['rule']} | {cell(e.get('text') or '*')} | {cell(e['reason'])} |"),
        ("preservation", L["cols_k"], lambda p: f"| {markdown_code(p['path'])} | {p['kind']} | {markdown_code(p['value'])} | {cell(p['reason'])} |"),
    ]
    for key, cols, row in sections:
        lines += [f"## {L[key]}", ""]
        items = data.get(key, [])
        lines += ([cols, "|" + "---|" * cols.count(" | ") + "---|", *map(row, items)] if items else [L["none"]]) + [""]
    for key in ("limitations", "decisions"):
        lines += [f"## {L[key]}", "", *([f"- {cell(x)}" for x in data.get(key, [])] or [L["none"]]), ""]
    return "\n".join(lines), after


def render(out):
    text, after = build_report(out)
    write_text(Path(out) / "report.md", text)
    return after


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("record")
    m.add_argument("fragments", nargs="+")
    c = sub.add_parser("check")
    c.add_argument("record")
    r = sub.add_parser("report")
    r.add_argument("run")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "merge":
            data = merge(a.record, a.fragments)
            print(f"{len(data.get('findings', []))} findings in {a.record}")
        elif a.cmd == "check":
            check_record(load_json(a.record))
            print("ok")
        else:
            after = render(a.run)
            print(f"report.md written; {after['open']} open hits")
    except (RecordError, KeyError, OSError, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
