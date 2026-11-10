#!/usr/bin/env python3
"""Regenerate the derived parts of site/data.js from the skill's own sources.

    python3 site/build_data.py           # rewrite site/data.js
    python3 site/build_data.py --check   # exit 1 if site/data.js is stale

The static page cannot call detect.py, so data.js carries copies: the rules
and genres from rules.json, each rule's and perspective's entry from
reference/patterns.md, structure.md and content.md, and every sample's text
and scan. Those are rebuilt here. Each sample's label, short label, language
and genre, and its `preserved` and `dropped_stats` notes, are editorial and
kept as written; `shortLabel` names the file the sample is read from, and an
examples/before.* sample takes its after text from the matching after.* file.
"""
import argparse
import json
import re
import sys

import serve

DATA = serve.SITE / "data.js"
REFERENCE = serve.ROOT / "skills" / "deslop" / "reference"
PREFIX, SUFFIX = "window.DESLOP_DATA = ", ";\n"
ENTRY = re.compile(r"### `([A-Z]+-\d+)`[ \t]*$")


def read_data(path=DATA):
    src = path.read_text(encoding="utf-8")
    if not (src.startswith(PREFIX) and src.endswith(SUFFIX)):
        raise ValueError(f"{path} must be '{PREFIX}{{...}}{SUFFIX.strip()}'")
    return json.loads(src[len(PREFIX):-len(SUFFIX)])


def render(data):
    return PREFIX + json.dumps(data, indent=2, ensure_ascii=False) + SUFFIX


def rounded(value):
    """Floats compared to 9 places: Python versions differ in the last digit."""
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v) for v in value]
    return value


def entries(path):
    """Each `### \\`ID\\`` entry's paragraphs, each paragraph on one line."""
    found, current, lines = {}, None, []
    for line in path.read_text(encoding="utf-8").split("\n") + ["#"]:
        if line.startswith("#"):
            if current:
                paragraphs = "\n".join(lines).strip().split("\n\n")
                found[current] = " ".join(" ".join(part.split()) for part in paragraphs if part.strip())
            match = ENTRY.match(line)
            current, lines = (match.group(1) if match else None), []
        elif current:
            lines.append(line)
    return found


def build(current):
    docs = entries(REFERENCE / "patterns.md")
    groups = {}
    for group in ("structure", "content"):
        for pid, doc in entries(REFERENCE / f"{group}.md").items():
            docs[pid], groups[pid] = doc, group
    samples = {}
    for key, sample in current["samples"].items():
        before_path = serve.ROOT / sample["shortLabel"]
        after_path = before_path.with_name(before_path.name.replace("before.", "after.", 1))
        before = before_path.read_text(encoding="utf-8")
        after = after_path.read_text(encoding="utf-8") if after_path != before_path and after_path.exists() else None
        rebuilt = {**sample, "before": before, "after": after,
                   "before_scan": serve.run_detection(before, sample["genre"], True)}
        rebuilt.pop("after_scan", None)
        if after is not None:
            rebuilt["after_scan"] = serve.run_detection(after, sample["genre"], True)
        samples[key] = rebuilt
    return {
        "rules": [{**rule, "doc": docs[rule["id"]]} for rule in serve.RULES["rules"]],
        "perspectives": [{**p, "doc": docs[p["id"]], "group": groups[p["id"]]} for p in serve.RULES["perspectives"]],
        "genres": serve.RULES["genres"],
        "samples": samples,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report whether data.js is current; write nothing")
    args = ap.parse_args(argv)
    try:
        current = read_data()
        built = build(current)
    except (OSError, KeyError, ValueError) as e:
        print(f"build_data: {e}", file=sys.stderr)
        return 2
    if args.check:
        if rounded(built) != rounded(current) or render(current) != DATA.read_text(encoding="utf-8"):
            print("site/data.js is stale; run python3 site/build_data.py", file=sys.stderr)
            return 1
        print("site/data.js is current")
        return 0
    DATA.write_text(render(built), encoding="utf-8")
    print(f"wrote {DATA.relative_to(serve.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
