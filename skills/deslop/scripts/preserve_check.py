#!/usr/bin/env python3
"""Compare rewritten documents with their snapshot for facts that must survive.

    preserve_check.py <out> [--out <out>/preserve.json]

For each snapshot file, compares numbers, URLs and link targets, inline code,
code blocks (fenced or indented, also inside list items), and footnote
references and definitions between <out>/original/ and the working copy.
A lost value no longer appears anywhere in the document; an added value did
not appear anywhere in the original, so the rewrite brought it in.
Each must be acknowledged in findings.json `preservation` with a reason, or
the check fails. Code block changes, including added or removed repeats,
always fail. Exit 0 when nothing is unacknowledged, 1 otherwise, 2 when the
run directory cannot be read or the output cannot be written.
"""
import argparse
import hashlib
import itertools
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from common import code_blocks, decode_text, is_markdown, load_json, load_snapshot, read_text, sha256_bytes, write_json
from findings import KINDS, check_record
from markdown_spans import (FOOTNOTE, URL, _escaped, _footnote_context, http_url_spans, link_target,
                            protected_inline_spans)

NUMBER_BODY = r"(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?"
# A hyphen after a digit or identifier belongs to a date, range or name.
NUMBER = re.compile(rf"(?<![A-Za-z0-9_.,])[+-]{NUMBER_BODY}|{NUMBER_BODY}")
LITERAL_TOKEN = re.compile(
    r'(?<!\S)(?:[([{<*_]*(?:"(?:\\[^\r\n]|[^"\\\r\n])*"|'
    r"'(?:\\[^\r\n]|[^'\\\r\n])*'|“[^“”\r\n]*”|"
    r"‘[^‘’\r\n]*’|「[^「」\r\n]*」|『[^『』\r\n]*』)\S*|\S+)")
PROSE_QUOTATION = (
    r'(?<!\\)"(?:\\[^\r\n]|[^"\\\r\n])*"|'
    r"(?<![\w\\])'(?:\\[^\r\n]|[^'\\\r\n])*'|"
    r"“[^“”\r\n]*”|‘[^‘’\r\n]*’|「[^「」\r\n]*」|『[^『』\r\n]*』")
PROSE_EMPHASIS = (
    r"(?<![\\*])(?P<stars>\*+)(?!\*)(?=\S)"
    r"(?:\\[^\r\n]|(?!(?P=stars))[^\\\r\n])+(?<!\s)(?P=stars)(?!\*)|"
    r"(?<![\w\\_])(?P<underscores>_+)(?!_)(?=\S)"
    r"(?:(?!(?P=underscores)(?![\w_]))"
    # The alternatives must be disjoint: a repeated intraword underscore
    # otherwise doubles the backtracking paths when the closing marker is absent.
    r"(?:\\[^\r\n]|(?<=\w)_(?=\w)|(?!(?<=\w)_(?=\w))(?!(?P=underscores))[^\\\r\n]))+"
    r"(?<!\s)(?P=underscores)(?![\w_])")
PROSE_LITERAL = re.compile(
    f"(?P<quoted>{PROSE_QUOTATION})|(?P<emphasis>{PROSE_EMPHASIS})|{URL.pattern}")
LITERAL_QUOTES = {'"': '"', "'": "'", "`": "`"}
PROSE_PAIRS = {**LITERAL_QUOTES, "(": ")", "[": "]", "{": "}", "<": ">",
               "“": "”", "‘": "’", "「": "」", "『": "』", "*": "*", "_": "_"}
# A footnote's definition is compared apart from its references, so a claim
# cannot lose its citation while the definition stays. Both report as kind
# footnote, so one preservation entry covers a footnote removed whole.
ROLES = {"footnote_definition": ("footnote", "definition")}


def _number_text(text):
    """Fold full-width digits and signs without joining distinct script runs."""
    # Classify each distinct character once; most text has no super- or
    # subscript at all, and then nothing needs marking.
    scripts = {}
    for c in set(text):
        tag = unicodedata.decomposition(c).partition(" ")[0]
        if tag in ("<super>", "<sub>"):
            scripts[c] = tag
    if scripts:
        marked, previous = [], ""
        for script, run in itertools.groupby(text, lambda c: scripts.get(c, "")):
            if script != previous:
                marked.append("^")
            marked.append("".join(run))
            previous = script
        text = "".join(marked)
    return unicodedata.normalize("NFKC", text).replace("\u2212", "-")


def code(text, markdown=True):
    """Code block bodies, and text with every block masked at its original offsets."""
    spans = code_blocks(text, indented=markdown)
    # Blocks do not overlap: build the masked text in one pass instead of
    # copying the whole document once per block.
    pieces, pos = [], 0
    for start, end, _, _ in spans:
        pieces.extend((text[pos:start], re.sub(r"[^\r\n]", " ", text[start:end])))
        pos = end
    pieces.append(text[pos:])
    return [text[b:e] for _, _, b, e in spans], "".join(pieces)


def facts(text, markdown=True):
    blocks, rest = code(text, markdown)
    titles = []
    spans = list(protected_inline_spans(rest, source=text, markdown=markdown, title_spans=titles))
    # A wrapped code span reads as one line, so rewrapping the prose keeps it.
    inline = [re.sub(r"[ \t]*\r?\n[ \t]*", " ", value) for kind, _, _, value in spans
              if kind == "inline_code"]
    urls = [value for kind, _, _, value in spans if kind == "url"]
    pieces, end = [], 0
    for _, start, stop, _ in spans:
        pieces.extend((rest[end:start], re.sub(r"[^\n]", " ", rest[start:stop])))
        end = stop
    rest = "".join(pieces) + rest[end:]
    pieces, end = [], 0
    for start, stop in http_url_spans(rest):
        value = rest[start:stop]
        urls.append(link_target(value) if value.startswith("<") else value.rstrip(".,;:"))
        pieces.extend((rest[end:start], " " * (stop - start)))
        end = stop
    # Keep offsets into the original source for footnote definition roles.
    rest = "".join(pieces) + rest[end:]
    notes = {"footnote": [], "footnote_definition": []}
    definitions, excluded = _footnote_context(text, rest, markdown, titles) if FOOTNOTE.search(rest) else (set(), [])
    excluded_index = 0

    def footnote(match):
        nonlocal excluded_index
        while excluded_index < len(excluded) and excluded[excluded_index][1] <= match.start():
            excluded_index += 1
        if excluded_index < len(excluded) and excluded[excluded_index][0] < match.end():
            return match.group(0)
        if _escaped(rest, match.start()):
            return match.group(0)
        kind = "footnote_definition" if match.start() in definitions else "footnote"
        notes[kind].append(match.group(0))
        return " " * len(match.group(0))

    rest = FOOTNOTE.sub(footnote, rest)
    return {
        "code_block": Counter("sha256:" + hashlib.sha256(b.encode()).hexdigest()[:12] for b in blocks),
        "inline_code": Counter(inline),
        "url": Counter(urls),
        "footnote": Counter(notes["footnote"]),
        "footnote_definition": Counter(notes["footnote_definition"]),
        "number": Counter(NUMBER.findall(_number_text(rest))),
    }


def _literal_tokens(text, prose, excluded=()):
    if prose:
        spans = [match.span() for match in LITERAL_TOKEN.finditer(text)]
        pieces, end = [], 0
        for start, stop in excluded:
            pieces.extend((text[end:start], re.sub(r"[^\r\n]", " ", text[start:stop])))
            end = stop
        masked = "".join(pieces) + text[end:]
        # Consume quotes, emphasis and bare URLs in source order, so a URL
        # cannot extend beyond its formatting into the following prose.
        regions = [(0, len(masked))]
        while regions:
            start, stop = regions.pop()
            while match := PROSE_LITERAL.search(masked, start, stop):
                start = match.end()
                if match.group("quoted") or match.group("emphasis"):
                    spans.append(match.span())
                else:
                    start = next(http_url_spans(masked, match.start(), stop))[1]
                if match.group("emphasis"):
                    # Emphasis remains prose: a quoted value within a longer
                    # emphasized sentence is independent too. URL/code stay opaque.
                    width = len(match.group("stars") or match.group("underscores"))
                    regions.append((match.start() + width, match.end() - width))
        yield from sorted(set(spans))
        return
    # Keep quotes/escapes inside a code token opaque even in unfamiliar
    # assignments or concatenations. Their contents are not separate tokens.
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        start, quote = pos, None
        while pos < len(text):
            char = text[pos]
            if char == "\\":
                pos = min(pos + 2, len(text))
                continue
            if quote is not None:
                if char == quote:
                    quote = None
            elif char in LITERAL_QUOTES:
                quote = char
            elif char.isspace():
                break
            pos += 1
        yield start, pos


def _literal_url_values(text, *, prose=False, excluded=()):
    """Whole tokens outside protected spans, with optional surrounding punctuation."""
    pairs = PROSE_PAIRS if prose else LITERAL_QUOTES
    index = 0
    for token_start, token_end in _literal_tokens(text, prose, excluded):
        while index < len(excluded) and excluded[index][1] <= token_start:
            index += 1
        if index < len(excluded) and excluded[index][0] < token_end:
            continue
        value = text[token_start:token_end]
        start, end, quoted_value, formatted = 0, len(value), False, False
        while start < end:
            if prose and not quoted_value:
                while start < end and value[end - 1] in ".,;:。、":
                    end -= 1
            if quoted_value and value[start] not in "*_":
                break
            if end - start < 2 or pairs.get(value[start]) != value[end - 1]:
                break
            quoted = value[start] in "\"'`“‘「『"
            if quoted:
                closing = start + 1
                while closing < end:
                    if value[closing] == "\\":
                        closing += 2
                    elif value[closing] == pairs[value[start]]:
                        break
                    else:
                        closing += 1
                if closing != end - 1:
                    break
            formatted = formatted or quoted or value[start] in "*_"
            start, end = start + 1, end - 1
            if quoted:
                # Code is literal after one unquote. Prose may still contain
                # Markdown emphasis, but its other inner punctuation is data.
                if not prose:
                    break
                quoted_value = True
        if prose and not quoted_value and URL.search(value):
            # Existing bare URL facts authorize their complete values. Prose
            # tokens and emphasis cannot extend them with sentence delimiters.
            bare = next(http_url_spans(value, start, end), None) if formatted else None
            if bare != (start, end) or value[start] == "<":
                continue
        if start < end:
            yield value[start:end]


def _restated_url_values(original, markdown):
    """Independent literals can be linked; parts of existing URLs cannot."""
    blocks, rest = code(original, markdown)
    values = set()
    for body in blocks:
        values.update(_literal_url_values(body))
    excluded = []
    for kind, start, stop, value in protected_inline_spans(rest, source=original, markdown=markdown):
        if kind == "inline_code":
            values.add(value)
            values.update(_literal_url_values(value))
        excluded.append((start, stop))
    # Test the original token boundaries: blanking these spans could create
    # an independent token from text attached to a code span or destination.
    # Bare URLs remain whole tokens, so prose quotes/emphasis may surround
    # them without allowing a prefix or suffix to become an independent value.
    values.update(_literal_url_values(rest, prose=True, excluded=sorted(excluded)))
    return values


def compare(before, after, original, markdown=True):
    """Values that vanished or appeared. Repeating or dropping a repeat of a
    value the document still states is not a fact change, and neither is
    quoting in inline code an identifier the original's code already contained.
    Prose words newly wrapped in backticks count as added: that would hide them
    from detect.py. Code blocks must keep their occurrence counts as well."""
    code_text = "\n".join(code(original, markdown)[0])
    new_urls = after["url"].keys() - before["url"].keys()
    restated_urls = _restated_url_values(original, markdown) if new_urls else set()
    diffs = []
    for key in (*KINDS, *ROLES):
        kind, role = ROLES.get(key, (key, None))
        extra = {"role": role} if role else {}
        if kind == "code_block":
            for change, values in (("lost", before[key] - after[key]),
                                   ("added", after[key] - before[key])):
                for value, count in sorted(values.items()):
                    diffs.append({"kind": kind, "change": change, "value": value, "count": count})
            continue
        for value in sorted(before[key].keys() - after[key].keys()):
            diffs.append({"kind": kind, "change": "lost", "value": value, "count": before[key][value], **extra})
        for value in sorted(after[key].keys() - before[key].keys()):
            if kind == "inline_code" and re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", code_text):
                continue
            if kind == "url" and value in restated_urls:
                continue
            diffs.append({"kind": kind, "change": "added", "value": value, "count": after[key][value], **extra})
    return diffs


def check(out, record=None):
    """Fact changes in each working copy. record is an already-checked
    findings.json (status.py passes {} for an invalid one); by default it is
    read and checked from the run directory."""
    out = Path(out)
    snap, work = load_snapshot(out)
    findings = out / "findings.json"
    if record is None:
        record = check_record(load_json(findings)) if findings.exists() else {}
    acks = record.get("preservation", [])
    acked = {(a["path"], a["kind"], a["value"]) for a in acks if a.get("reason")}
    files, unacked = [], 0
    for entry in snap["files"]:
        path = entry["path"]
        current, kept = work / path, out / "original" / path
        missing = [name for name, p in (("original", kept), ("working copy", current)) if not p.is_file()]
        if missing:
            files.append({"path": path, "sha256": None, "diffs": [], "missing": " and ".join(missing)})
            unacked += 1
            continue
        original = read_text(kept)
        content = current.read_bytes()
        md = is_markdown(path)
        diffs = compare(facts(original, md), facts(decode_text(content), md), original, md)
        for d in diffs:
            d["acknowledged"] = d["kind"] != "code_block" and (path, d["kind"], d["value"]) in acked
            unacked += not d["acknowledged"]
        files.append({"path": path, "sha256": sha256_bytes(content), "diffs": diffs})
    return {"tool": "deslop-preserve", "files": files, "unacknowledged": unacked}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run")
    ap.add_argument("--out", help="default: <run>/preserve.json")
    a = ap.parse_args(argv)
    try:
        result = check(a.run)
        write_json(a.out or Path(a.run) / "preserve.json", result)
    except (OSError, ValueError) as e:
        ap.error(str(e))
    for f in result["files"]:
        if f.get("missing"):
            print(f"{f['path']}: {f['missing']} missing")
        for d in f["diffs"]:
            if not d["acknowledged"]:
                role = f" {d['role']}" if d.get("role") else ""
                print(f"{f['path']}: {d['change']} {d['kind']}{role} {d['value']!r} x{d['count']}")
    print(f"{result['unacknowledged']} unacknowledged changes", file=sys.stderr)
    return 1 if result["unacknowledged"] else 0


if __name__ == "__main__":
    sys.exit(main())
