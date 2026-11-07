"""Inline ignore directives for standalone detect.py scans.

An author who keeps a flagged phrase on purpose can say so where it stands:

    <!-- deslop-ignore EN-04: "robust statistics" is the field's term -->
    <!-- deslop-ignore-file DEN-05, DEN-06: a glossary, one heading per term -->

`deslop-ignore` covers the line it shares with other text, or else the next
nonblank line after the comment. `deslop-ignore-file` covers the whole
document, density rules included. A directive names rule IDs only, never a
tier or family, and must give a reason after the colon. Artifact rules
cannot be ignored this way: chat residue is exempt only inside a quotation.

Directives are read from text with front matter and code masked, so a
directive shown as an example inside code does nothing. Hits inside a
directive comment (its reason, say) are dropped. A directive whose rule
covers no hit is reported as unused, and a malformed one as invalid; neither
changes the exit code. Rewrite runs never read directives: their contract
accounts for every hit in findings.json.
"""
import bisect
import re

DIRECTIVE = re.compile(r"<!--[ \t]*deslop-ignore(?P<file>-file)?(?![\w-])(?P<body>[\s\S]*?)-->")
RULE_ID = re.compile(r"[A-Z]{2,4}-\d{2}")


def _line_starts(text):
    return [0, *(m.end() for m in re.finditer("\n", text))]


def find(code_masked, tiers):
    """Directives in one document's code-masked text.

    tiers maps every known rule ID to its tier. Returns (directives, spans):
    directive records, and the (start, end) offsets of every directive
    comment, so hits inside them can be dropped.
    """
    matches = list(DIRECTIVE.finditer(code_masked)) if "deslop-ignore" in code_masked else []
    if not matches:
        return [], []
    starts = _line_starts(code_masked)
    lines = code_masked.split("\n")
    out, spans = [], []
    for m in matches:
        spans.append(m.span())
        line = bisect.bisect_right(starts, m.start()) - 1
        end_line = bisect.bisect_right(starts, m.end() - 1) - 1
        record = {"line": line + 1, "scope": "file" if m.group("file") else "line"}
        names, colon, reason = m.group("body").partition(":")
        rules = [r.strip() for r in names.replace(",", " ").split()]
        reason = " ".join(reason.split())
        if not colon or not reason:
            record["error"] = "give a reason after a colon: deslop-ignore RULE: why it stays"
        elif not rules:
            record["error"] = "name at least one rule ID before the colon"
        elif bad := [r for r in rules if not RULE_ID.fullmatch(r) or r not in tiers]:
            record["error"] = f"unknown rule {bad[0]!r}; name rule IDs such as EN-04"
        elif art := [r for r in rules if tiers[r] == "artifact"]:
            record["error"] = f"{art[0]} is an artifact rule; chat residue is exempt only inside a quotation"
        if "error" in record:
            out.append(record)
            continue
        record.update(rules=list(dict.fromkeys(rules)), reason=reason)
        if record["scope"] == "line":
            before = code_masked[starts[line]:m.start()]
            after = code_masked[m.end():starts[end_line + 1] - 1 if end_line + 1 < len(starts) else len(code_masked)]
            if before.strip() or after.strip():
                record["target_line"] = line + 1 if before.strip() else end_line + 1
            else:
                following = next((n for n in range(end_line + 1, len(lines)) if lines[n].strip()), None)
                if following is None:
                    record["error"] = "no line follows this directive"
                    out.append(record)
                    continue
                record["target_line"] = following + 1
        out.append(record)
    return out, spans


def apply(hits, directives, spans, line_starts):
    """Drop hits inside directive comments and exempt the hits a valid
    directive covers. Records each directive's rules that covered nothing
    under 'unused'. Returns the remaining hits."""
    def offset(h):
        return line_starts[h["line"] - 1] + h["col"] - 1

    if spans:
        hits = [h for h in hits if h["tier"] == "density"
                or not any(lo <= offset(h) < hi for lo, hi in spans)]
    for d in directives:
        if "error" in d:
            continue
        used = set()
        for h in hits:
            if h["exempt"] or h["rule"] not in d["rules"]:
                continue
            if d["scope"] == "line" and h["line"] != d["target_line"]:
                continue
            h["exempt"], h["exempt_by"] = f"inline: {d['reason']}", "inline"
            used.add(h["rule"])
        d["unused"] = [r for r in d["rules"] if r not in used]
    return hits
