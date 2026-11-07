"""Render a detect.py result as a Markdown diagnosis.

The diagnosis-only request ("where does this read as AI-written?") is
answered by document and section. This puts each open hit under the
heading it falls in, with the rule's note, lists document-wide density
measures with their limits, the perspective cues to read first, and what
stayed exempt and why. It reads the result and the documents' outlines
only; it changes nothing. The output is GitHub-flavoured Markdown, so it
can be pasted into a chat, a PR comment or $GITHUB_STEP_SUMMARY.
"""
import bisect
import html
from collections import Counter


def cell(value):
    """Text safe inside a Markdown table cell."""
    text = html.escape(" ".join(str(value).split()), quote=False)
    return text.replace("\\", "\\\\").replace("|", "\\|")


def code(value):
    """A literal, shown as code without breaking out of a table cell."""
    text = html.escape(" ".join(str(value).split()), quote=False).replace("|", "&#124;")
    return f"<code>{text}</code>" if text else ""


def section_at(outline, line):
    """The heading path (outermost first) of the section holding line."""
    lines = [entry[0] for entry in outline]
    i = bisect.bisect_right(lines, line) - 1
    if i < 0:
        return ""
    path, level = [], outline[i][1] + 1
    for entry_line, entry_level, text in reversed(outline[:i + 1]):
        if entry_level < level:
            path.append(text)
            level = entry_level
    path.reverse()
    # A lone level-1 heading is the document's title, not a section.
    if len(path) > 1 and sum(1 for entry in outline if entry[1] == 1) == 1 and outline[0][1] == 1:
        path = path[1:]
    return " › ".join(path)


def render(result, rules, outlines=None):
    """The diagnosis for one detect.py result, as one Markdown string."""
    outlines = outlines or {}
    notes = {r["id"]: r["note"] for r in rules["rules"]}
    names = {p["id"]: p["name"] for p in rules["perspectives"]}
    genres = {g["id"]: g["name"] for g in rules["genres"]}
    s = result["summary"]
    out = ["# deslop diagnosis", ""]
    head = (f"{s['files']} documents, {s['total']} hits: **{s['open']} open**, {s['exempt']} exempt; "
            f"{s['cues']} perspective cues.")
    if "baseline" in s:
        head += f" {s['baseline']} hits are accepted by the baseline and not listed"
        head += f"; {s['baseline_resolved']} baseline hits are gone." if s["baseline_resolved"] else "."
    if result.get("selection"):
        sel = result["selection"]
        parts = [f"only {', '.join(sel['select'])}"] if sel.get("select") else []
        parts += [f"without {', '.join(sel['ignore'])}"] if sel.get("ignore") else []
        head += f" Rules scanned: {'; '.join(parts)}."
    out += [head, ""]
    if s["open"]:
        out += ["Hits are candidates read in context, not verdicts. Most are fixed by deleting the "
                "sentence or word; see `reference/patterns.md` for each rule.", ""]
    hits_by, cues_by, ignores_by = {}, {}, {}
    for h in result["hits"]:
        hits_by.setdefault(h["path"], []).append(h)
    for c in result["cues"]:
        cues_by.setdefault(c["path"], []).append(c)
    for d in result.get("ignores", []):
        ignores_by.setdefault(d["path"], []).append(d)

    out += ["| Document | Genre | Language | Prose chars | Open | Exempt | Cues |", "|---|---|---|---:|---:|---:|---:|"]
    for f in result["files"]:
        hits = [h for h in hits_by.get(f["path"], []) if h.get("exempt_by") != "baseline"]
        open_n = sum(1 for h in hits if not h["exempt"])
        out.append(f"| {code(f['path'])} | {cell(f['genre'])} | {f['lang']} | {f['metrics']['chars']:,} "
                   f"| {open_n} | {len(hits) - open_n} | {len(cues_by.get(f['path'], []))} |")
    out.append("")

    for f in result["files"]:
        path = f["path"]
        hits = [h for h in hits_by.get(path, []) if h.get("exempt_by") != "baseline"]
        open_hits = [h for h in hits if not h["exempt"]]
        density = [h for h in open_hits if h["tier"] == "density"]
        located = [h for h in open_hits if h["tier"] != "density"]
        exempt = [h for h in hits if h["exempt"]]
        file_cues = cues_by.get(path, [])
        outline = outlines.get(path, [])
        out += [f"## {code(path)}", "",
                f"{genres.get(f['genre'], f['genre'])} (`{f['genre']}`), {f['lang']}, "
                f"{f['metrics']['chars']:,} prose characters in {f['metrics']['sentences']} sentences.", ""]
        if not hits and not file_cues:
            out += ["No hits and no cues.", ""]
        if located:
            counts = Counter(h["rule"] for h in located)
            out += ["### Open hits by section", "",
                    "Most frequent: " + ", ".join(f"{rule} ×{n}" for rule, n in counts.most_common(5)) + ".", "",
                    "| Line | Section | Rule | Text | What it is |", "|---:|---|---|---|---|"]
            for h in located:
                where = "quote" if h["context"] == "quote" else ""
                section = section_at(outline, h["line"]) or "(before the first heading)"
                out.append(f"| {h['line']}:{h['col']} | {cell(section)} | {h['rule']}{' (' + where + ')' if where else ''} "
                           f"| {code(h['text'])} | {cell(notes.get(h['rule'], ''))} |")
            out.append("")
        if density:
            out += ["### Density across the document", "", "| Rule | Measure (limit) | What it is |", "|---|---|---|"]
            for h in density:
                out.append(f"| {h['rule']} | {code(h['text'])} | {cell(notes.get(h['rule'], ''))} |")
            out.append("")
        if file_cues:
            out += ["### Where to read for perspectives", "",
                    "Cues are not hits. They name lines where a content or structural perspective "
                    "probably applies (`reference/content.md`, `reference/structure.md`).", "",
                    "| Line | Section | Perspective | Why | Line text |", "|---:|---|---|---|---|"]
            for c in file_cues:
                section = section_at(outline, c["line"]) or "(before the first heading)"
                name = names.get(c["perspective"], "")
                out.append(f"| {c['line']} | {cell(section)} | {c['perspective']} {cell(name)} | {cell(c['why'])} "
                           f"| {code(c['text'])} |")
            out.append("")
        if exempt:
            out += ["<details><summary>Exempt hits (" + str(len(exempt)) + ")</summary>", "",
                    "| Line | Rule | Text | Reason |", "|---:|---|---|---|"]
            for h in exempt:
                out.append(f"| {h['line']}:{h['col']} | {h['rule']} | {code(h['text'])} | {cell(h['exempt'])} |")
            out += ["", "</details>", ""]
        problems = [d for d in ignores_by.get(path, []) if "error" in d or d.get("unused")]
        if problems:
            out += ["### Inline ignores to fix", "", "| Line | Problem |", "|---:|---|"]
            for d in problems:
                why = d["error"] if "error" in d else f"covers no hit of {', '.join(d['unused'])}; remove it"
                out.append(f"| {d['line']} | {cell(why)} |")
            out.append("")
    return "\n".join(out).rstrip() + "\n"
