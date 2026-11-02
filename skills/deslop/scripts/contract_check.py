#!/usr/bin/env python3
"""Check that a run directory meets the deslop run contract.

    contract_check.py <out>

Recomputes rather than trusts: detection runs again on original/ and on the
current working copies, and so does the fact comparison. Fails when any rule
hit is still open, any unexempted hit in the originals is unaccounted for,
a recorded genre is unknown, any
perspective is unrecorded or recorded N/A where detect.py cues it in the
originals, any fact change is unacknowledged, the originals
no longer match the snapshot or a working copy is missing, the record names a
file outside the snapshot, or report.md differs from a fresh render of the
current record.
"""
import argparse
import sys
from pathlib import Path

import comparison
import detect
import findings
import preserve_check
from common import OUTPUT_NAMES, genre_table, load_json, load_rules, load_snapshot, read_text, sha256_file


def problems(out):
    try:
        return _problems(out)
    except (OSError, ValueError) as e:
        return [f"cannot check run: {e}"]


def _problems(out):
    out = Path(out)
    missing = [n for n in OUTPUT_NAMES if not (out / n).is_file()]
    if missing:
        return [f"missing {n}" for n in missing]
    errs = []
    try:
        data = findings.check_record(load_json(out / "findings.json"))
    except (findings.RecordError, ValueError) as e:
        return [f"findings.json: {e}"]
    rules = load_rules()
    snap, work = load_snapshot(out)
    if data["meta"]["mode"] != snap["mode"]:
        errs.append(f"meta.mode {data['meta']['mode']} differs from snapshot mode {snap['mode']}")
    for entry in snap["files"]:
        original = out / "original" / entry["path"]
        if not original.is_file() or sha256_file(original) != entry["sha256"]:
            errs.append(f"original/{entry['path']} no longer matches snapshot.json")
        if not (work / entry["path"]).is_file():
            errs.append(f"working copy {entry['path']} is missing")
        if entry.get("genre", "general") not in genre_table(rules):
            errs.append(f"snapshot.json gives {entry['path']} the unknown genre {entry['genre']!r}")
    if errs:
        return errs

    errs.extend(comparison.problems(out, data, snap, work))

    paths = {entry["path"] for entry in snap["files"]}
    for key in ("findings", "exemptions", "preservation"):
        for item in data.get(key, []):
            if item["path"] not in paths:
                errs.append(f"{key} names {item['path']!r}, which is not in snapshot.json")

    after = detect.scan_snapshot(out, rules, data.get("exemptions", []))
    for h in after["hits"]:
        if not h["exempt"]:
            errs.append(f"open hit {h['path']}:{h['line']} {h['rule']} {h['text']!r}")

    accounted = {(f["path"], f["rule"]) for f in data.get("findings", []) if f["action"] != "exempted"}
    before = detect.scan_snapshot(out, rules, data.get("exemptions", []), originals=True)
    for h in before["hits"]:
        if not h["exempt"] and (h["path"], h["rule"]) not in accounted:
            errs.append(f"before-hit {h['path']}:{h['line']} {h['rule']} has no finding or exemption")

    exempt_pairs = {(e["path"], e["rule"]) for e in data.get("exemptions", [])}
    for f in data.get("findings", []):
        if f["action"] == "exempted" and (f["path"], f["rule"]) not in exempt_pairs:
            errs.append(f"{f['id']} is exempted but no exemption entry covers {f['path']} {f['rule']}")

    recorded = {p["id"]: p for p in data.get("perspectives", [])}
    for p in rules["perspectives"]:
        if p["id"] not in recorded:
            errs.append(f"perspective {p['id']} ({p['name']}) not recorded")
    for c in before["cues"]:
        if recorded.get(c["perspective"], {}).get("result") == "N/A":
            errs.append(f"perspective {c['perspective']} is N/A but detect.py cues it at {c['path']}:{c['line']}")
    if any(p["result"] == "not checked" for p in recorded.values()) and not data.get("limitations"):
        errs.append("a perspective is 'not checked' but limitations is empty")

    kept = preserve_check.check(out)
    for f in kept["files"]:
        for d in f["diffs"]:
            if not d["acknowledged"]:
                role = f" {d['role']}" if d.get("role") else ""
                errs.append(f"{f['path']}: {d['change']} {d['kind']}{role} {d['value']!r} not acknowledged in preservation")

    if read_text(out / "report.md") != findings.build_report(out)[0]:
        errs.append("report.md differs from a fresh render of the current record; run findings.py report")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run")
    a = ap.parse_args(argv)
    errs = problems(a.run)
    for e in errs:
        print(f"FAIL {e}")
    print("contract ok" if not errs else f"{len(errs)} contract failures", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
