#!/usr/bin/env python3
"""Show how far a run has come and what to do next.

    status.py <out> [--json]

Reads a run directory at any point after snapshot.py and recomputes what
it can from the current files: whether detection ran on these originals,
whether candidates exist and differ from the original, which before-hits
still need a finding, which perspectives are unrecorded (and which are
cued, so cannot be N/A), which comparisons are missing, open hits and
unacknowledged fact changes in the working copies, and whether the outputs
and report are current. Each step prints done or todo with the next command.

It never writes. When every step is done it runs contract_check, so exit 0
means the contract passes; 1 means work remains; 2 means the run directory
cannot be read.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import comparison
import contract_check
import detect
import findings
import preserve_check
from common import load_json, load_rules, load_snapshot, read_text, sha256_file

SCRIPTS = Path(__file__).resolve().parent


def _cmd(script, *args):
    return " ".join([f"python3 {SCRIPTS / script}", *map(str, args)])


def _step(name, done, summary, todo=(), next_cmd=None):
    return {"step": name, "done": done, "summary": summary, "todo": list(todo), "next": None if done else next_cmd}


def _fresh(path, files, digests):
    """True when a saved scan describes exactly the given file digests."""
    try:
        saved = load_json(path)
    except (OSError, ValueError):
        return False
    if not isinstance(saved, dict) or not isinstance(saved.get("files"), list):
        return False
    return {f.get("path"): f.get("sha256") for f in saved["files"] if isinstance(f, dict)} == {
        p: digests.get(p) for p in files}


def _lines(hits):
    lines = sorted({h["line"] for h in hits})
    shown = ", ".join(map(str, lines[:6]))
    return f"line {shown}" + (f" (+{len(lines) - 6})" if len(lines) > 6 else "")


def collect(out):
    """Return {"run", "complete", "steps", "next"} for a run directory."""
    out = Path(out).resolve()
    snap, work = load_snapshot(out)
    rules = load_rules()
    paths = [f["path"] for f in snap["files"]]
    compare = snap.get("workflow") == "compare-three"
    steps = []
    genres = Counter(f.get("genre", "general") for f in snap["files"])
    steps.append(_step("snapshot", True, f"{len(paths)} document{'s' if len(paths) != 1 else ''}, {snap['mode']} mode"
                       + (", three candidates required" if compare else "")
                       + "; genres " + ", ".join(f"{g} {n}" for g, n in sorted(genres.items()))))

    originals = {f["path"]: f["sha256"] for f in snap["files"]}
    record_file = out / "findings.json"
    data, record_error = None, None
    if record_file.is_file():
        try:
            data = findings.check_record(load_json(record_file))
        except (findings.RecordError, ValueError) as e:
            record_error = str(e)
    exemptions = (data or {}).get("exemptions", [])
    before = detect.scan_snapshot(out, rules, exemptions, originals=True)

    fresh = _fresh(out / "detect.before.json", paths, originals)
    s = before["summary"]
    by_genre = sum(1 for h in before["hits"] if h.get("exempt_by") == "genre")
    steps.append(_step(
        "detect.before", fresh,
        f"{s['total']} hits in the originals, {by_genre} exempt by genre, {s['cues']} perspective cues",
        [] if fresh else ["detect.before.json is missing or was not made from these originals"],
        _cmd("detect.py", "--snapshot", out, "--out", out / "detect.before.json")))

    if compare:
        todo = []
        for path in paths:
            for cid in comparison.CANDIDATE_IDS:
                file = out / "candidates" / cid / path
                if not file.is_file():
                    todo.append(f"candidates/{cid}/{path} is missing")
                elif sha256_file(file) == originals[path]:
                    todo.append(f"candidates/{cid}/{path} is still the original")
        missing_dir = not (out / "candidates").is_dir()
        steps.append(_step(
            "candidates", not todo,
            f"{len(paths) * 3 - len(todo)} of {len(paths) * 3} candidate files rewritten",
            ["candidates/ does not exist"] if missing_dir else todo,
            _cmd("comparison.py", "init", out) if missing_dir else "rewrite each listed candidate from the original"))

    if data is None:
        steps.append(_step("record", False, "findings.json " + ("is invalid" if record_error else "does not exist"),
                           [record_error] if record_error else ["merge a first fragment with meta and voice"],
                           _cmd("findings.py", "merge", record_file, "<fragment.json>")))
        data = {}
    else:
        steps.append(_step("record", True, f"{len(data.get('findings', []))} findings, "
                           f"{len(data['voice']['rules'])} voice rules ({data['voice']['source']})"))

    accounted = {(f["path"], f["rule"]) for f in data.get("findings", []) if f["action"] != "exempted"}
    pending = {}
    for h in before["hits"]:
        if not h["exempt"] and (h["path"], h["rule"]) not in accounted:
            pending.setdefault((h["path"], h["rule"]), []).append(h)
    groups = len({(h["path"], h["rule"]) for h in before["hits"] if not h["exempt"]})
    steps.append(_step(
        "accounting", not pending, f"{groups - len(pending)} of {groups} (path, rule) groups have a finding or exemption",
        [f"{path} {rule} x{len(hits)} at {_lines(hits)}: {hits[0]['text']!r}"
         for (path, rule), hits in sorted(pending.items())],
        _cmd("findings.py", "merge", record_file, "<fragment.json>")))

    recorded = {p["id"]: p for p in data.get("perspectives", [])}
    cued = {}
    for c in before["cues"]:
        cued.setdefault(c["perspective"], []).append(f"{c['path']}:{c['line']}")
    todo = []
    for p in rules["perspectives"]:
        where = cued.get(p["id"])
        hint = f" (cued at {', '.join(where[:3])}{' …' if len(where) > 3 else ''}; cannot be N/A)" if where else ""
        if p["id"] not in recorded:
            todo.append(f"{p['id']} {p['name']} not recorded{hint}")
        elif recorded[p["id"]]["result"] == "N/A" and where:
            todo.append(f"{p['id']} {p['name']} is N/A{hint}")
    if any(p["result"] == "not checked" for p in recorded.values()) and not data.get("limitations"):
        todo.append("a perspective is 'not checked' but limitations is empty")
    total = len(rules["perspectives"])
    steps.append(_step("perspectives", not todo, f"{sum(p['id'] in recorded for p in rules['perspectives'])} of {total} recorded",
                       todo, _cmd("findings.py", "merge", record_file, "<fragment.json>")))

    if compare:
        reviewed = {c["path"] for c in data.get("comparisons", []) if isinstance(c, dict)}
        todo = [f"no comparison for {p}" for p in paths if p not in reviewed]
        if reviewed and data:
            todo += [e for e in comparison.problems(out, data, snap, work) if not e.startswith("comparison missing for ")]
        steps.append(_step("comparisons", not todo, f"{len(reviewed & set(paths))} of {len(paths)} documents reviewed and selected",
                           todo, "review A, B and C, select, copy the winner to the working file, then merge the comparison"))

    # A missing working copy is a verify todo (preserve_check lists it), not
    # an unreadable run: scan the copies that exist.
    after = detect.scan_snapshot(out, rules, exemptions, only={p for p in paths if (work / p).is_file()})
    open_hits = [h for h in after["hits"] if not h["exempt"]]
    kept = preserve_check.check(out, data)
    facts = [f"{f['path']}: {d['change']} {d['kind']} {d['value']!r}"
             for f in kept["files"] for d in f["diffs"] if not d["acknowledged"]]
    facts += [f"{f['path']}: {f['missing']} missing" for f in kept["files"] if f.get("missing")]
    steps.append(_step(
        "verify", not open_hits and not facts,
        f"{len(open_hits)} open hits and {len(facts)} unacknowledged fact changes in the working copies",
        [f"open hit {h['path']}:{h['line']}:{h['col']} {h['rule']} {h['text']!r}" for h in open_hits] + facts,
        "rewrite, delete or exempt each open hit; acknowledge or revert each fact change"))

    current = {p: sha256_file(work / p) for p in paths if (work / p).is_file()}
    todo = []
    if not _fresh(out / "detect.after.json", paths, current):
        todo.append("detect.after.json is missing or older than the working copies")
    if not _fresh(out / "preserve.json", paths, current):
        todo.append("preserve.json is missing or older than the working copies")
    report = out / "report.md"
    if not data:
        todo.append("report.md needs a valid findings.json first")
    elif len(current) < len(paths):
        todo.append("report.md needs every working copy first")
    elif not report.is_file() or read_text(report) != findings.build_report(out)[0]:
        todo.append("report.md is missing or differs from a fresh render of findings.json")
    outputs_cmd = " && ".join([
        _cmd("detect.py", "--snapshot", out, "--exempt", record_file, "--out", out / "detect.after.json"),
        _cmd("preserve_check.py", out), _cmd("findings.py", "report", out)])
    steps.append(_step("outputs", not todo, "detect.after.json, preserve.json and report.md "
                       + ("are current" if not todo else "need refreshing"), todo, outputs_cmd))

    complete = all(s["done"] for s in steps)
    if complete:
        problems = contract_check.problems(out)
        steps.append(_step("contract", not problems, "contract ok" if not problems else f"{len(problems)} contract failures",
                           problems, _cmd("contract_check.py", out)))
        complete = not problems
    first = next((s for s in steps if not s["done"]), None)
    return {"tool": "deslop-status", "run": str(out), "complete": complete, "steps": steps,
            "next": first and {"step": first["step"], "do": first["next"]}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run")
    ap.add_argument("--json", action="store_true", help="print the status as JSON")
    ap.add_argument("--limit", type=int, default=10, help="todo items shown per step (default 10; 0 shows all)")
    a = ap.parse_args(argv)
    try:
        result = collect(a.run)
    except (OSError, ValueError) as e:
        print(f"cannot read run: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"run {result['run']}")
        for s in result["steps"]:
            print(f"[{'done' if s['done'] else 'todo'}] {s['step']:<13} {s['summary']}")
            shown = s["todo"] if a.limit <= 0 else s["todo"][:a.limit]
            for item in shown:
                print(f"       - {item}")
            if len(shown) < len(s["todo"]):
                print(f"       … {len(s['todo']) - len(shown)} more (--limit 0 shows all)")
        if result["next"]:
            print(f"next: {result['next']['step']}: {result['next']['do']}")
        else:
            print("complete: contract ok")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
