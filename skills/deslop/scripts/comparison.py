#!/usr/bin/env python3
"""Validate and report three complete rewrites of each document.

    comparison.py init <out>

init copies the snapshot originals to candidates/A, B and C. Reviews belong
in findings.json; they are tied to the candidate bytes by SHA-256. Candidate
annotations never stand in for the final rewrite's findings or preservation.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from common import decode_text, is_markdown, load_rules, load_snapshot, sha256_bytes, sha256_file
from common import markdown_code
from common import markdown_inline as _inline

CANDIDATE_IDS = ("A", "B", "C")
SCORE_LIMITS = {"fidelity": 30, "structure": 25, "clarity": 20, "voice": 15, "concision": 10}
DIGEST = re.compile(r"[0-9a-f]{64}")


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a non-empty string")


def _digest(value, where):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise ValueError(f"{where} must be a SHA-256 digest")


def _relative(value, where):
    _text(value, where)
    path = PurePosixPath(value)
    if ("\0" in value or not path.parts or path.is_absolute() or ".." in path.parts
            or path.as_posix() != value):
        raise ValueError(f"{where} must be a canonical relative path")


def score_total(candidate):
    """Compute an editorial total from the five reviewed criteria."""
    return sum(candidate["scores"][key]["score"] for key in SCORE_LIMITS)


def _annotations(candidate, path, where):
    # Reuse the existing rule, exemption and preservation schema. This small
    # record has no comparisons, so findings can call us without recursion.
    import findings

    record = {
        "schema_version": 1,
        "meta": {"target": path, "assessor": "comparison", "date": "validation",
                 "lang": "en", "mode": "copy"},
        "voice": {"source": "inferred", "rules": ["Candidate annotation validation."]},
        "exemptions": candidate.get("exemptions", []),
        "preservation": candidate.get("preservation", []),
    }
    try:
        findings.check_record(record)
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from e
    for key in ("exemptions", "preservation"):
        for item in record[key]:
            if item["path"] != path:
                raise ValueError(f"{where}.{key} must refer only to {path!r}")


def _candidate(candidate, path, where, *, merged=False):
    if not isinstance(candidate, dict):
        raise ValueError(f"{where} must be an object")
    allowed = ("merged",) if merged else CANDIDATE_IDS
    if candidate.get("id") not in allowed:
        raise ValueError(f"{where}.id must be one of {allowed}")
    for key in ("approach", "strengths", "weaknesses", "review_note"):
        _text(candidate.get(key), f"{where}.{key}")
    _digest(candidate.get("sha256"), f"{where}.sha256")
    if type(candidate.get("eligible")) is not bool:
        raise ValueError(f"{where}.eligible must be a boolean")
    scores = candidate.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(SCORE_LIMITS):
        raise ValueError(f"{where}.scores must contain exactly {list(SCORE_LIMITS)}")
    for key, maximum in SCORE_LIMITS.items():
        part = scores[key]
        if (not isinstance(part, dict) or type(part.get("score")) is not int
                or not 0 <= part["score"] <= maximum):
            raise ValueError(f"{where}.scores.{key}.score must be an integer from 0 to {maximum}")
        _text(part.get("reason"), f"{where}.scores.{key}.reason")
    _annotations(candidate, path, where)
    if merged:
        sources = candidate.get("sources")
        if not isinstance(sources, list) or not 2 <= len(sources) <= 3:
            raise ValueError(f"{where}.sources must name two or three distinct candidates")
        seen = set()
        for i, source in enumerate(sources):
            if not isinstance(source, dict) or source.get("candidate") not in CANDIDATE_IDS:
                raise ValueError(f"{where}.sources[{i}].candidate must be A, B or C")
            if source["candidate"] in seen:
                raise ValueError(f"{where}.sources must name distinct candidates")
            seen.add(source["candidate"])
            _text(source.get("contribution"), f"{where}.sources[{i}].contribution")


def check_comparisons(value):
    """Validate review shape, score ranges and the stated selection."""
    if not isinstance(value, list):
        raise ValueError("comparisons must be a list")
    seen = set()
    for i, item in enumerate(value):
        where = f"comparisons[{i}]"
        if not isinstance(item, dict):
            raise ValueError(f"{where} must be an object")
        path = item.get("path")
        _relative(path, f"{where}.path")
        if path in seen:
            raise ValueError(f"{where}.path {path!r} must be unique")
        seen.add(path)
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 3:
            raise ValueError(f"{where}.candidates must contain exactly three candidates")
        for j, candidate in enumerate(candidates):
            _candidate(candidate, path, f"{where}.candidates[{j}]")
        by_id = {c["id"]: c for c in candidates}
        if set(by_id) != set(CANDIDATE_IDS):
            raise ValueError(f"{where}.candidates must contain A, B and C once each")
        if "merged" in item:
            _candidate(item["merged"], path, f"{where}.merged", merged=True)
            by_id["merged"] = item["merged"]
        selected = item.get("selected")
        if not isinstance(selected, str) or selected not in by_id:
            raise ValueError(f"{where}.selected must name an existing candidate")
        _text(item.get("reason"), f"{where}.reason")
        _digest(item.get("final_sha256"), f"{where}.final_sha256")
        if not by_id[selected]["eligible"]:
            raise ValueError(f"{where}.selected candidate is not eligible")
        eligible = [c for c in candidates if c["eligible"]]
        if not eligible:
            raise ValueError(f"{where} has no eligible standalone candidate")
        best = max(score_total(c) for c in eligible)
        score = score_total(by_id[selected])
        if selected == "merged" and score <= best:
            raise ValueError(f"{where}: merged selection must score above the best standalone candidate")
        if selected != "merged":
            def rank(candidate):
                return (score_total(candidate), candidate["scores"]["fidelity"]["score"],
                        candidate["scores"]["structure"]["score"])
            if rank(by_id[selected]) < max(rank(c) for c in eligible):
                raise ValueError(f"{where}: selected candidate must rank highest by total, fidelity and structure")
        merged = by_id.get("merged")
        if selected != "merged" and merged and merged["eligible"] and score_total(merged) > score:
            raise ValueError(f"{where}: an eligible merged candidate scores above the selected candidate")


def _bounded_file(base, path):
    """Keep symlink targets inside the fixed candidate or original root."""
    file = base / path
    try:
        if not file.resolve().is_relative_to(base):
            raise ValueError(f"{file} resolves outside {base}")
    except (OSError, RuntimeError) as e:
        raise ValueError(f"cannot resolve {file}: {e}") from e
    if not file.is_file():
        raise ValueError(f"{file} is missing or is not a file")
    return file


def _candidate_problems(file, candidate, entry, original, rules):
    import detect
    import preserve_check

    path, label = entry["path"], candidate["id"]
    prefix = f"candidate {label} {path}"
    errors = []
    content = file.read_bytes()
    if sha256_bytes(content) != candidate["sha256"]:
        errors.append(f"{prefix}: SHA-256 differs from the reviewed text; review and score again")
    if not candidate["eligible"]:
        return errors
    genres = {path: entry["genre"]} if "genre" in entry else {}
    scan = detect.scan([file], file.parent, rules, candidate.get("exemptions", []), genres,
                       paths=[path], contents=[content])
    for hit in scan["hits"]:
        if not hit["exempt"]:
            errors.append(f"{prefix}: open hit {hit['rule']} at line {hit['line']}")
    md = is_markdown(path)
    current = decode_text(content)
    before, after = preserve_check.facts(original, md), preserve_check.facts(current, md)
    acknowledged = {(a["kind"], a["value"]) for a in candidate.get("preservation", [])}
    if before["code_block"] != after["code_block"]:
        errors.append(f"{prefix}: code_block changed and cannot be exempted")
    for diff in preserve_check.compare(before, after, original, md):
        if diff["kind"] != "code_block" and (diff["kind"], diff["value"]) not in acknowledged:
            errors.append(f"{prefix}: {diff['change']} {diff['kind']} {diff['value']!r} not acknowledged in preservation")
    return errors


def problems(out, data, snap, work):
    """Recheck candidate bytes and gates, then bind the winner to the output."""
    reviews = data.get("comparisons", [])
    try:
        check_comparisons(reviews)
    except ValueError as e:
        return [str(e)]
    entries = {entry["path"]: entry for entry in snap["files"]}
    reviewed = {item["path"] for item in reviews}
    errors = [f"comparison names {path!r}, which is not in snapshot.json" for path in sorted(reviewed - entries.keys())]
    if snap.get("workflow") == "compare-three":
        errors += [f"comparison missing for {path}" for path in sorted(entries.keys() - reviewed)]
    if not reviews:
        return errors
    out, work = Path(out).resolve(), Path(work)
    rules = load_rules()
    for item in reviews:
        path = item["path"]
        if path not in entries:
            continue
        entry = entries[path]
        try:
            original_file = _bounded_file(out / "original", path)
            content = original_file.read_bytes()
            if sha256_bytes(content) != entry["sha256"]:
                errors.append(f"original/{path} no longer matches snapshot.json")
                continue
            original = decode_text(content)
            candidates = item["candidates"] + ([item["merged"]] if "merged" in item else [])
            selected_digest = None
            for candidate in candidates:
                try:
                    file = _bounded_file(out / "candidates" / candidate["id"], path)
                    errors.extend(_candidate_problems(file, candidate, entry, original, rules))
                    if candidate["id"] == item["selected"]:
                        # Bind the final copy to reviewed bytes, not a later reread.
                        selected_digest = candidate["sha256"]
                except (OSError, ValueError) as e:
                    errors.append(f"candidate {candidate['id']} {path}: {e}")
            final_file = _bounded_file(work, path)
            digest = sha256_file(final_file)
            if digest != item["final_sha256"]:
                errors.append(f"{path}: final_sha256 differs from the working copy; review and score again")
            if selected_digest is not None and digest != selected_digest:
                errors.append(f"{path}: working copy differs from selected candidate {item['selected']}")
        except (OSError, ValueError) as e:
            errors.append(f"comparison {path}: {e}")
    return errors


def report_lines(out, data, lang):
    """Render score totals, reasons, reviews and links without truncation."""
    reviews = data.get("comparisons", [])
    if not reviews:
        return []
    check_comparisons(reviews)
    ja = lang == "ja"
    labels = (dict(zip(SCORE_LIMITS, ("忠実さ", "構成", "明瞭さ", "著者の声", "簡潔さ"))) if ja else
              dict(zip(SCORE_LIMITS, ("Fidelity", "Structure", "Clarity", "Voice", "Concision"))))
    title = "再構成案の比較" if ja else "Rewrite comparison"
    note = "点数は編集上の評価です。AI検出器のスコアではありません。" if ja else "Scores are editorial judgments, not AI-detector scores."
    lines = [f"## {title}", "", note, ""]
    for item in reviews:
        path = item["path"]
        candidates = item["candidates"] + ([item["merged"]] if "merged" in item else [])
        cols = ["案", "構成方針", "採用条件"] if ja else ["Candidate", "Approach", "Eligibility"]
        cols += [f"{labels[key]} / {maximum}" for key, maximum in SCORE_LIMITS.items()]
        cols += ["合計 / 100" if ja else "Total / 100"]
        lines += [f"### {markdown_code(path)}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for candidate in candidates:
            link = quote(f"candidates/{candidate['id']}/{path}", safe="/")
            status = ("適格" if candidate["eligible"] else "不適格") if ja else ("Eligible" if candidate["eligible"] else "Ineligible")
            values = [f"[{candidate['id']}]({link})", _inline(candidate["approach"]), status]
            values += [str(candidate["scores"][key]["score"]) for key in SCORE_LIMITS]
            values += [str(score_total(candidate))]
            lines.append("| " + " | ".join(values) + " |")
        decision = "採用" if ja else "Selected"
        lines += ["", f"{decision}: {item['selected']} — {_inline(item['reason'])}", ""]
        for candidate in candidates:
            lines += [f"#### {candidate['id']}", ""]
            for key, label in (("strengths", "長所" if ja else "Strengths"),
                               ("weaknesses", "弱点" if ja else "Weaknesses"),
                               ("review_note", "内容の確認" if ja else "Content review")):
                lines.append(f"- {label}: {_inline(candidate[key])}")
            lines += [f"- {labels[key]}: {_inline(candidate['scores'][key]['reason'])}" for key in SCORE_LIMITS]
            for source in candidate.get("sources", []):
                label = "統合元" if ja else "Source"
                lines.append(f"- {label} {source['candidate']}: {_inline(source['contribution'])}")
            lines.append("")
    return lines


def init(out):
    """Publish three complete copies of the exact verified original bytes."""
    out = Path(out).resolve()
    snap, _ = load_snapshot(out)
    if snap.get("workflow") != "compare-three":
        raise ValueError("comparison init requires a compare-three snapshot")
    candidates = out / "candidates"
    if candidates.exists() or candidates.is_symlink():
        raise ValueError(f"{candidates} already exists; candidate drafts will not be overwritten")
    with tempfile.TemporaryDirectory(prefix=".candidates-", dir=out) as temporary:
        staged = Path(temporary) / "candidates"
        for entry in snap["files"]:
            original = _bounded_file(out / "original", entry["path"])
            content = original.read_bytes()
            if sha256_bytes(content) != entry["sha256"]:
                raise ValueError(f"original/{entry['path']} no longer matches snapshot.json")
            for candidate in CANDIDATE_IDS:
                target = staged / candidate / entry["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        staged.rename(candidates)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    parser = sub.add_parser("init")
    parser.add_argument("run")
    args = ap.parse_args(argv)
    try:
        init(args.run)
    except (OSError, ValueError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"three candidates initialized under {Path(args.run) / 'candidates'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
