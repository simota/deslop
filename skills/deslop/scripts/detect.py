#!/usr/bin/env python3
"""Find AI-writing tells in prose documents.

The deterministic half of DETECT and VERIFY: the regex rules and density
metrics in rules.json, applied to prose with front matter, code and URLs
masked. Hits are candidates; REWRITE decides each one in context.

    detect.py PATH... [--genre [PATH=]GENRE]... [--exempt findings.json] [--out detect.json]
    detect.py --snapshot <out> [--exempt <out>/findings.json] [--out FILE]
    detect.py - [--stdin-name docs/notes.md] < notes.md
    detect.py docs/ --baseline detect.baseline.json [--format github]

A baseline is an earlier --out result: the open hits it lists are accepted
one for one (lexical hits by path, rule and text; density hits by path and
rule), so a docs tree with existing tells can gate only new ones.
--format github prints open hits and cues as GitHub Actions annotations.

The genre of each document (from --genre, the snapshot, or the file name)
tightens or relaxes density limits and exempts the conventions it needs;
those hits stay listed, marked with the genre.

Each file also gets perspective cues (cues.py): lines where a structural or
content perspective probably applies. Cues are printed and recorded but are
not hits, and never change the exit code.

Exit 0 when no unexempted hit remains, 1 when some do, 2 on usage errors.
"""
import argparse
import bisect
import functools
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import cues
import findings
from common import (assign_genres, clear_caches, code_blocks, decode_text, genre_table, infer_genre, is_markdown, iter_docs,
                    load_json, load_rules, load_snapshot, sha256_bytes, write_json)
from markdown_spans import LINK_LABEL, _escaped, _reference_definitions, http_url_spans, inline_block_spans, protected_inline_spans

FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n.*?^(?:---|\.\.\.)[ \t]*\r?$", re.M | re.S)
BOLD = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
BOLDLEAD = re.compile(r"^[^\S\r\n]*(?:[-*+]|\d+[.)])\s+\*\*[^*\n]+(?:\*\*\s*[:：]|[:：]\*\*)", re.M)
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
# A blockquote can open on its list item's line: "- > quoted".
QUOTE_LINE = re.compile(r"\s*(?:(?:[-*+]|\d{1,9}[.)])\s+)*>")
HEADING = re.compile(r"^#{1,6}\s")
# After a blank line, so a setext heading underline is not counted.
HR = re.compile(r"(?:\A|(?<=\n)[ \t]*\n) {0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$", re.M)
KANA = re.compile(r"[぀-ヿ]")
KANJI = re.compile(r"[一-鿿]")
LATIN_WORD = re.compile(r"[A-Za-z]+")
TRIAD = re.compile(r"\b[\w-]+(?: [\w-]+){0,2}, [\w-]+(?: [\w-]+){0,2},? and [\w-]+")
LIST_TAIL = re.compile(r",\s*(?:[\w'-]+ ){0,3}$")
# A 。 inside 「」 or 『』 belongs to the quotation, not to the sentence around it.
# An opening bracket matches one way only, so a line of brackets cannot backtrack.
SENTENCE_JA = re.compile(r"(?:「[^「」\n]*」|『[^『』\n]*』|「(?![^「」\n]*」)|『(?![^『』\n]*』)"
                         r"|[^。！？!?\n「『])+[。！？!?]")
ASCII_EDGE = re.compile(r"[A-Za-z0-9]")
SENTENCE_EN = re.compile(r"[^.!?\n]+(?:[.!?]+(?=\s|$))")
SENTENCE_TERMINAL_JA = re.compile(r"[。！？!?]")
SENTENCE_TERMINAL_EN = re.compile(r"[.!?]")
PARAGRAPH = re.compile(r"(?:^[ \t]*\S.*(?:\n|\Z))+", re.M)
# A single figure, not one end of a range such as 15-30%.
STAT_AMOUNT = r"[0-9０-９]+(?:[.,][0-9０-９]+)?"
STAT_UNIT = r"(?:%|％|percent\b|パーセント|割(?!引)|倍)"
STAT = re.compile(r"(?<![A-Za-z0-9０-９.\-–〜~])" + STAT_AMOUNT + r"\s?" + STAT_UNIT +
                  r"(?!\s?[-–〜~]\s?[0-9])", re.I)
STAT_RANGE = re.compile(r"(?<![A-Za-z0-9０-９.,])" + STAT_AMOUNT + r"(?:\s*" + STAT_UNIT + r")?\s*[-–〜~]\s*" +
                        STAT_AMOUNT + r"(?:\s*" + STAT_UNIT + r")?", re.I)
# A figure reads as a claim when its sentence names a population or a change.
# 約 reads as "about" only before an amount; 規約 and 予約 are ordinary words.
CLAIM = re.compile(r"企業|会社|ユーザー|利用者|回答者|開発者|組織|チーム|人が|人の|向上|削減|改善|増加|減少|短縮|高速|効率|成長|最大"
                   r"|約\s?[0-9０-９一二三四五六七八九十百千万半数]|程度|およそ|全体的"
                   r"|\b(?:compan|team|user|developer|people|respondent|organi[sz]ation|business|increas|decreas|reduc|improv|boost)"
                   r"|\b(?:up to|faster|growth|cut(?:s|ting)?|sav(?:e[sd]?|ings?)|more|less(?:en(?:s|ed|ing)?)?|fewer|about|approximately|roughly|overall)\b", re.I)
# A link, footnote, named source, stated assumption or measurement in the paragraph counts as support.
SOURCE = re.compile(r"\]\(|\]\[|https?://|\[\^|出典|引用元|参照|※|仮定|想定|試算|見込み|計測|測定|ベンチマーク"
                    r"|\b(?:source|according to|cited?|assum|estimat|measured|benchmark)"
                    r"|[0-9]\s?(?:ms|µs|ns|s|秒|ミリ秒|MB|GB|KB|fps|rps|req/s)\b|[0-9][^\n]{0,20}(?:→|->)\s?[0-9]", re.I)
SENTENCE_END = re.compile(r"[。！？!?]|\.(?:\s|$)")


def blank(text, start, end):
    """Replace text[start:end] with spaces, keeping newlines and offsets."""
    return blank_spans(text, [(start, end)])


def blank_spans(text, spans):
    """Blank every (start, end) span in one pass over text.

    Blanking is idempotent, so overlapping spans blank their union, exactly
    as blanking them one at a time would, without copying the whole text
    once per span.
    """
    pieces, end = [], 0
    for start, stop in sorted(spans):
        if stop <= end:
            continue
        start = max(start, end)
        pieces.extend((text[end:start], re.sub(r"[^\n]", " ", text[start:stop])))
        end = stop
    return "".join(pieces) + text[end:]


def mask_front_matter(text):
    """Mask metadata before interpreting its contents as Markdown blocks."""
    m = FRONT_MATTER.match(text)
    return blank(text, 0, m.end()) if m else text


def mask_blocks(text, markdown=True):
    """Mask front matter and fenced code, keeping paragraph boundaries."""
    text = mask_front_matter(text)
    return blank_spans(text, [(start, end) for start, end, _, _ in code_blocks(text, indented=markdown)])


def mask_code(text, markdown=True, *, url_spans=None):
    """Mask code and optionally collect URL spans before changing inline syntax."""
    source = mask_front_matter(text)
    text = mask_blocks(source, markdown)
    # Resolve code and destinations in the same order as the fact checker.
    # A backtick inside a URL cannot open code in the following prose. Keep
    # the URL itself visible here: artifact rules must still see its tokens.
    codes = []
    for kind, start, end, _ in reversed(list(protected_inline_spans(text, source=source, markdown=markdown))):
        if kind == "inline_code":
            codes.append((start, end))
        elif url_spans is not None:
            url_spans.append((start, end))
    return blank_spans(text, codes)


def mask_urls(text, *, url_spans=None):
    """Mask complete destinations; keep labels, titles and invalid links as prose."""
    if url_spans is None:
        url_spans = [(start, end) for kind, start, end, _ in protected_inline_spans(text) if kind == "url"]
    # An explicit link span can enclose a bare HTTP URL. Mask their
    # union once, preserving all original offsets even when they overlap.
    return blank_spans(text, [*url_spans, *http_url_spans(text)])


@functools.lru_cache(maxsize=1)
def masked_views(text, markdown=True):
    """(code_masked, prose) for one document: code blanked, then URLs too.

    scan_text and perspective_cues read the same views of a document, so
    the most recent result is kept instead of parsing its inline spans
    twice; scan() releases it after each file. Masking front matter first
    does not change them: a blanked header cannot match again.
    """
    url_spans = []
    code_masked = mask_code(text, markdown, url_spans=url_spans)
    # Reuse the original decisions: blanking code can make invalid link
    # syntax look like a real destination and hide its surrounding prose.
    return code_masked, mask_urls(code_masked, url_spans=url_spans)


def language(text):
    """Japanese when the text has kana and its kana and kanji outnumber its
    Latin words, at any length: an English text quoting some Japanese stays
    English, and Latin product names do not outvote a Japanese sentence."""
    kana = len(KANA.findall(text))
    return "ja" if kana and kana + len(KANJI.findall(text)) > len(LATIN_WORD.findall(text)) else "en"


def paragraph_langs(prose, default):
    """Return a function from an offset to the language of its paragraph, so
    an English paragraph in a Japanese document gets the English rules."""
    spans = [(m.start(), m.end(), language(m.group(0))) for m in PARAGRAPH.finditer(prose)]
    starts = [s for s, _, _ in spans]

    def at(offset):
        i = bisect.bisect_right(starts, offset) - 1
        return spans[i][2] if i >= 0 and offset < spans[i][1] else default
    return at


def line_context(line):
    if QUOTE_LINE.match(line):
        return "quote"
    s = line.lstrip()
    if HEADING.match(s):
        return "heading"
    if LIST_ITEM.match(line):
        return "list"
    return "prose"


# Every character inline_quotation_spans acts on: line ends, backslashes,
# and each opening or closing quotation mark.
QUOTATION_MARK = re.compile(r"""[\r\n\\"'“”‘’「」『』]""")


def inline_quotation_spans(prose):
    """Balanced inline quotations, excluding escaped marks and apostrophes.

    Keep these local to a line: an unmatched quotation mark must not exempt
    later paragraphs. The caller has already masked code and URLs.
    """
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’", "「": "」", "『": "』"}
    stack, spans = [], []
    open_by_closer = {}
    escaped, previous = False, -1
    # Any other character only ends a pending escape, so step from one
    # mark to the next: a gap between them means such a character came.
    for match in QUOTATION_MARK.finditer(prose):
        i, char = match.start(), match.group()
        if i > previous + 1:
            escaped = False
        previous = i
        if char in "\r\n":
            stack.clear()
            open_by_closer.clear()
            escaped = False
            continue
        if char == "\\":
            escaped = not escaped
            continue
        if escaped:
            escaped = False
            continue
        before, after = prose[i - 1:i] if i else "", prose[i + 1:i + 2]
        if char in ("'", "’") and before.isalnum() and after.isalnum():
            continue
        matching = open_by_closer.get(char)
        if matching:
            closing = matching[-1]
            _, start = stack[closing]
            # An elision such as '90s must not block a matching outer quote.
            while len(stack) > closing:
                opening, _ = stack.pop()
                open_by_closer[pairs[opening]].pop()
            spans.append((start + 1, i))
        elif char in pairs and not (char == "'" and before.isalnum()):
            open_by_closer.setdefault(pairs[char], []).append(len(stack))
            stack.append((char, i))
    return spans


def enclosed_by(spans):
    """Return a test for whether some (lo, hi) span holds start..end.

    Sorts and prunes spans in place. A span inside another can never be the
    only one to hold a range, so keep each span that reaches further than
    all before it: starts and ends then both increase, and the last span
    starting at or before start reaches furthest. Each test is a binary
    search instead of a pass over every span, and no index is allocated.
    """
    spans.sort()
    kept = 0
    for i in range(len(spans)):
        if not kept or spans[i][1] > spans[kept - 1][1]:
            spans[kept] = spans[i]
            kept += 1
    del spans[kept:]

    def holds(start, end):
        i = bisect.bisect_right(spans, (start, float("inf"))) - 1
        return i >= 0 and spans[i][1] >= end
    return holds


def paragraphs(prose, markdown=True):
    """Prose lines grouped into paragraphs and list items, so a hard-wrapped
    sentence is one sentence."""
    out = []
    for line in cues.normalized_headings(prose, markdown).split("\n"):
        s = line.strip()
        if not s or HEADING.match(s) or s.startswith("|"):
            out.append([])
            continue
        if LIST_ITEM.match(line) or not out:
            out.append([])
        out[-1].append(LIST_ITEM.sub("", s).lstrip("> "))
    return [p for p in out if p]


def join_lines(lines, lang):
    """Japanese lines join without a space unless both edges are Latin letters or digits."""
    if lang != "ja":
        return " ".join(lines)
    text = lines[0]
    for line in lines[1:]:
        both = ASCII_EDGE.match(text[-1:]) and ASCII_EDGE.match(line[:1])
        text += (" " if both else "") + line
    return text


def sentences(prose, lang, markdown=True):
    pattern = SENTENCE_JA if lang == "ja" else SENTENCE_EN
    terminal = SENTENCE_TERMINAL_JA if lang == "ja" else SENTENCE_TERMINAL_EN
    out = []
    for para in paragraphs(prose, markdown):
        s = join_lines(para, lang)
        # Every sentence ends in a terminal mark. Without one the pattern
        # cannot match, but would retry from every offset: quadratic time.
        if not terminal.search(s):
            continue
        out.extend(m.group(0).strip() for m in pattern.finditer(s) if len(m.group(0).strip()) > 3)
    return out


def sections(prose):
    """Prose split at headings and table rows: a run of matching sentence
    endings does not continue across a new section or a table."""
    out, cur = [], []
    for line in prose.split("\n"):
        s = line.strip()
        if HEADING.match(s) or s.startswith("|"):
            out.append("\n".join(cur))
            cur = []
        else:
            cur.append(line)
    out.append("\n".join(cur))
    return out


def ending_run(sents):
    """Longest run of consecutive sentences sharing their last three characters."""
    best, run, prev = 0, 0, None
    for s in sents:
        tail = s.rstrip("。！？!? ")[-3:]
        run = run + 1 if tail == prev else 1
        prev = tail
        best = max(best, run)
    return best


def triads(prose):
    """Lists of exactly three; the tail of a longer list does not count."""
    return sum(
        not LIST_TAIL.search(prose[max(0, m.start() - 40):m.start()])
        for m in TRIAD.finditer(prose)
    )


def metrics(prose, lang, markdown=True, *, source=None):
    prose = cues.normalized_headings(prose, markdown, source=source)
    lines = [l for l in prose.split("\n") if l.strip()]
    body = [l for l in lines if not HEADING.match(l.lstrip()) and not l.lstrip().startswith("|")]
    chars = sum(len(l.strip()) for l in body)
    sents = sentences(prose, lang, markdown)
    lengths = [len(s) if lang == "ja" else len(s.split()) for s in sents]
    per = 1000 / chars if chars else 0
    return {
        "chars": chars,
        "sentences": len(sents),
        "bold_per_1000": len(BOLD.findall(prose)) * per,
        "dash_per_1000": prose.count("—") * per,
        "exclaim_ratio": (sum(s.endswith(("!", "！")) for s in sents) / len(sents)) if sents else 0,
        "boldlead_items": len(BOLDLEAD.findall(prose)),
        "heading_per_1000": sum(bool(HEADING.match(l.lstrip())) for l in lines) * per,
        "list_ratio": (sum(bool(LIST_ITEM.match(l)) for l in body) / len(body)) if len(body) >= 10 else 0,
        "ending_run": max((ending_run(sentences(part, lang, markdown)) for part in sections(prose)), default=0),
        "length_cv": (statistics.pstdev(lengths) / statistics.mean(lengths)) if len(lengths) >= 8 else None,
        "triad_count": triads(prose) if lang == "en" else 0,
        "hr_count": len(HR.findall(prose)),
    }


def sentence_around(prose, start, end, lo, hi):
    """The sentence of prose[lo:hi] that holds start..end."""
    left = max((m.end() for m in SENTENCE_END.finditer(prose, lo, start)), default=lo)
    right = SENTENCE_END.search(prose, end, hi)
    return prose[left:right.end() if right else hi]


def paragraph_spans(text, markdown=True):
    """Nonblank paragraphs, split further at shared Markdown block boundaries."""
    source = mask_front_matter(text)
    visible = mask_blocks(source, markdown)
    boundaries = sorted({point for span in inline_block_spans(visible, source=source, markdown=markdown)
                         for point in span})
    for p in PARAGRAPH.finditer(visible):
        start = p.start()
        for i in range(bisect.bisect_right(boundaries, start), bisect.bisect_left(boundaries, p.end())):
            yield start, boundaries[i]
            start = boundaries[i]
        yield start, p.end()


def unsourced_stats(text, code_masked, prose, markdown=True):
    """Spans of figures stated as claims, in prose paragraphs that cite nothing."""
    # Masked inline code can leave blank lines inside a real paragraph. Only
    # block-level masking should separate a claim from a following citation.
    for start, end in paragraph_spans(text, markdown):
        if SOURCE.search(code_masked, start, end):
            continue
        # Spaces around a range delimiter do not make its upper endpoint a
        # standalone claim. Track whole ranges so later figures still count.
        ranges = iter(STAT_RANGE.finditer(prose, start, end))
        current_range = next(ranges, None)
        for m in STAT.finditer(prose, start, end):
            while current_range and current_range.end() <= m.start():
                current_range = next(ranges, None)
            if current_range and current_range.start() <= m.start() < current_range.end():
                continue
            line = prose[prose.rfind("\n", 0, m.start()) + 1:m.start()]
            if line.lstrip().startswith("|"):
                continue
            if CLAIM.search(sentence_around(prose, m.start(), m.end(), start, end)):
                yield m.span()


CHECKS = {"unsourced_stat": unsourced_stats}


def applies(rule, lang):
    return rule["lang"] in ("any", lang)


def compile_rules(rules):
    out = []
    for rule in rules["rules"]:
        if "pattern" in rule:
            flags = (re.I if "i" in rule["flags"] else 0) | (re.M if "m" in rule["flags"] else 0)
            out.append((rule, re.compile(rule["pattern"], flags)))
        else:
            out.append((rule, None))
    return out


def scan_text(text, compiled, min_chars, markdown=True, limits=None):
    """Return (lang, metrics, hits) for one document's text. Pattern rules
    follow each paragraph's language, density rules the document's. limits
    replaces a density rule's bounds by rule id."""
    code_masked, prose = masked_views(text, bool(markdown))
    in_quotation = enclosed_by(inline_quotation_spans(prose))
    lang = language(prose)
    raw_lines = text.split("\n")
    starts = [0]
    for line in raw_lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    lang_at = paragraph_langs(prose, lang)
    hits = []
    for rule, rx in compiled:
        if "metric" in rule:
            continue
        source = code_masked if rule["tier"] == "artifact" else prose
        if rx is None:
            spans = CHECKS[rule["check"]](text, code_masked, prose, markdown)
        else:
            spans = (m.span() for m in rx.finditer(source))
        for start, end in spans:
            while start < end and source[start].isspace():
                start += 1
            while end > start and source[end - 1].isspace():
                end -= 1
            if start == end or not applies(rule, lang_at(start)):
                continue
            i = bisect.bisect_right(starts, start) - 1
            context = line_context(raw_lines[i])
            if in_quotation(start, end):
                context = "quote"
            hits.append({
                "line": i + 1, "col": start - starts[i] + 1, "rule": rule["id"],
                "tier": rule["tier"], "text": text[start:end], "context": context,
            })
    # Only real reference definitions resolve shortcuts: examples inside
    # code, metadata and HTML, or invalid destinations, cannot hide a field.
    if any(h["rule"] == "ART-07" and h["text"].startswith("[") for h in hits):
        source = mask_front_matter(text)
        # Container indentation can include a tab partly consumed by its
        # prefix; find the raw label within the already validated span.
        defined = {" ".join(LINK_LABEL.search(source, start, end).group().lstrip()[1:-2].split()).casefold()
                   for start, (end, _, _) in _reference_definitions(source, markdown).items()}
        hits = [h for h in hits if not (h["rule"] == "ART-07" and h["text"].startswith("[")
                                        and " ".join(h["text"][1:-1].split()).casefold() in defined
                                        and not _escaped(text, starts[h["line"] - 1] + h["col"] - 1))]
    m = metrics(prose, lang, markdown, source=mask_front_matter(text))
    if m["chars"] >= min_chars:
        for rule, _ in compiled:
            if "metric" not in rule or not applies(rule, lang):
                continue
            # A rule may need more prose than the rest: in a short document
            # one heading or list moves a structural share past any limit.
            if m["chars"] < rule.get("min_chars", 0):
                continue
            value = m[rule["metric"]]
            if value is None:
                continue
            rule = {**rule, **(limits or {}).get(rule["id"], {})}
            if ("max" in rule and value > rule["max"]) or ("min" in rule and value < rule["min"]):
                bound = f"max {rule['max']}" if "max" in rule else f"min {rule['min']}"
                hits.append({
                    "line": 1, "col": 1, "rule": rule["id"], "tier": "density",
                    "text": f"{rule['metric']}={round(value, 2)} ({bound})", "context": "document",
                })
    hits.sort(key=lambda h: (h["line"], h["col"], h["rule"]))
    return lang, m, hits


def perspective_cues(text, lang, chars, min_chars, markdown=True, quiet=()):
    # The cue parser also classifies code blocks. It must see the same
    # metadata boundary as the detector, so a fence inside YAML cannot
    # consume the document body. Blanking preserves body text and offsets.
    prose = masked_views(text, bool(markdown))[1]
    text = mask_front_matter(text)
    return cues.find(text, prose, lang, lambda part, language: sentences(part, language, markdown),
                     markdown, chars, min_chars, quiet)


def covers(phrase, hit, source, line_start=0):
    """True when phrase surrounds this exact hit, including across lines."""
    start = line_start + hit["col"] - 1
    end = start + len(hit["text"])
    if not source.startswith(hit["text"], start):
        return False
    # Only starts in this window can enclose the hit. Do not search the
    # whole document or let a later occurrence stand in for this one.
    i = source.find(phrase, max(0, end - len(phrase)), start + len(phrase))
    return 0 <= i <= start


def exemption_for(hit, path, exemptions, line="", *, line_start=0):
    """Return the reason a hit is exempt, or None. An exemption's text must
    match part of the hit or surround that occurrence in the source;
    artifacts are exempt only inside quotations. line may be the full
    document when line_start gives the hit's line offset."""
    for e in exemptions:
        if e.get("path") != path or e.get("rule") != hit["rule"]:
            continue
        if (e.get("text") and e["text"] not in hit["text"]
                and not covers(e["text"], hit, line, line_start)):
            continue
        if hit["tier"] == "artifact" and hit["context"] != "quote":
            return None
        return e.get("reason") or None
    return None


def scan(files, root, rules, exemptions, genres=None, *, paths=None, contents=None):
    """Scan exact file bytes, optionally supplied by a caller checking their hash."""
    compiled = compile_rules(rules)
    table = genre_table(rules)
    if paths is None:
        paths = [Path(f).resolve().relative_to(root).as_posix() for f in files]
    if len(paths) != len(files):
        raise ValueError("each scanned file must have one document path")
    if contents is not None and len(contents) != len(files):
        raise ValueError("each scanned file must have one byte content")
    genres = {**{rel: infer_genre(rel, rules) for rel in paths}, **(genres or {})}
    result = {"tool": "deslop-detect", "rules_version": rules["version"], "root": str(root), "files": [], "hits": [], "cues": []}
    for index, (f, rel) in enumerate(zip(files, paths)):
        if genres[rel] not in table:
            raise ValueError(f"{rel}: unknown genre {genres[rel]!r}")
        genre = table[genres[rel]]
        content = Path(f).read_bytes() if contents is None else contents[index]
        try:
            text = decode_text(content)
        except UnicodeDecodeError as e:
            bom = 3 if content.startswith(b"\xef\xbb\xbf") else 0
            raise ValueError(f"{f} is not UTF-8 text ({e.reason} at byte {e.start + bom})") from e
        lang, m, hits = scan_text(text, compiled, rules["min_chars"], is_markdown(f), genre["limits"])
        result["files"].append({"path": rel, "sha256": sha256_bytes(content), "lang": lang, "genre": genre["id"], "metrics": m})
        quiet = {p["id"] for p in rules["perspectives"] if genre["id"] in p.get("quiet", [])}
        for c in perspective_cues(text, lang, m["chars"], rules["min_chars"], is_markdown(f), quiet):
            result["cues"].append({"path": rel, **c})
        # Keep no document's text alive while the next one is scanned.
        masked_views.cache_clear()
        clear_caches()
        lines = text.split("\n")
        line_starts = [0]
        for line in lines[:-1]:
            line_starts.append(line_starts[-1] + len(line) + 1)
        for h in hits:
            h["path"] = rel
            if h["rule"] in genre["exempt"]:
                h["exempt"], h["exempt_by"] = f"{genre['name']}: {genre['exempt'][h['rule']]}", "genre"
            else:
                h["exempt"] = exemption_for(h, rel, exemptions, text, line_start=line_starts[h["line"] - 1])
            result["hits"].append(h)
    result["summary"] = summarize(result)
    return result


def summarize(result):
    open_hits = [h for h in result["hits"] if not h["exempt"]]
    by_rule = {}
    for h in open_hits:
        by_rule[h["rule"]] = by_rule.get(h["rule"], 0) + 1
    return {
        "files": len(result["files"]), "total": len(result["hits"]), "open": len(open_hits),
        "exempt": len(result["hits"]) - len(open_hits), "by_rule": dict(sorted(by_rule.items())),
        "cues": len(result["cues"]),
    }


def baseline_key(hit):
    """A density value moves with every edit; a lexical hit is its text."""
    return (hit["path"], hit["rule"]) + (() if hit["tier"] == "density" else (hit["text"],))


def load_baseline(path):
    """Return the open hits a saved detect.py result accepted, as a multiset."""
    data = load_json(path)
    if not isinstance(data, dict) or data.get("tool") != "deslop-detect" or not isinstance(data.get("hits"), list):
        raise ValueError(f"{path} is not a detect.py result (write one with --out)")
    keys = Counter()
    for i, h in enumerate(data["hits"]):
        if not isinstance(h, dict) or not all(isinstance(h.get(k), str) for k in ("path", "rule", "tier", "text")):
            raise ValueError(f"{path}: hits[{i}] lacks path, rule, tier or text")
        if not h.get("exempt"):
            keys[baseline_key(h)] += 1
    return keys


def apply_baseline(result, keys):
    """Exempt open hits the baseline already holds, one for one, and count
    the baseline hits no longer found so the baseline can be tightened."""
    remaining = Counter(keys)
    for h in result["hits"]:
        key = baseline_key(h)
        if not h["exempt"] and remaining[key] > 0:
            remaining[key] -= 1
            h["exempt"], h["exempt_by"] = "baseline: present when the baseline was recorded", "baseline"
    result["summary"] = summarize(result)
    result["summary"]["baseline"] = sum(1 for h in result["hits"] if h.get("exempt_by") == "baseline")
    result["summary"]["baseline_resolved"] = sum(remaining.values())
    return result


def _gh_escape(value, prop=False):
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(":", "%3A").replace(",", "%2C") if prop else value


def github_lines(result, notes):
    """GitHub Actions workflow commands: open hits as errors, cues as notices."""
    for h in result["hits"]:
        if h["exempt"]:
            continue
        where = f"file={_gh_escape(h['path'], True)},line={h['line']},col={h['col']}"
        title = _gh_escape(f"deslop {h['rule']}", True)
        yield f"::error {where},title={title}::{_gh_escape(notes.get(h['rule'], h['rule']) + ': ' + h['text'])}"
    for c in result["cues"]:
        where = f"file={_gh_escape(c['path'], True)},line={c['line']}"
        title = _gh_escape(f"deslop {c['perspective']} cue", True)
        yield f"::notice {where},title={title}::{_gh_escape(c['why'] + ': ' + c['text'])}"


def scan_snapshot(out, rules, exemptions, originals=False):
    """Scan a run's working copies, or with originals=True its original/ copies."""
    snap, work = load_snapshot(out)
    base = Path(out) / "original" if originals else work
    genres = {f["path"]: f["genre"] for f in snap["files"] if "genre" in f}
    paths = [f["path"] for f in snap["files"]]
    return scan([base / path for path in paths], base.resolve(), rules, exemptions, genres, paths=paths)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", help="files or directories; a lone - reads one document from standard input")
    ap.add_argument("--snapshot", help="run directory: scan its snapshot's working copies")
    ap.add_argument("--root", help="report paths relative to this directory "
                    "(default: the current directory, or the paths' common parent outside it)")
    ap.add_argument("--genre", action="append", metavar="[PATH=]GENRE",
                    help="genre of every document, or of PATH; repeatable (default: from the file name, else general)")
    ap.add_argument("--exempt", help="findings.json whose 'exemptions' apply")
    ap.add_argument("--baseline", metavar="DETECT_JSON",
                    help="an earlier --out result: its open hits are accepted, so only new hits fail")
    ap.add_argument("--stdin-name", metavar="NAME", default="stdin.md",
                    help="path reported for -, which also sets genre and Markdown handling (default: stdin.md)")
    ap.add_argument("--format", choices=("text", "github"), default="text",
                    help="text (path:line:col RULE text) or GitHub Actions annotations")
    ap.add_argument("--explain", action="store_true", help="add each rule's note to text output")
    ap.add_argument("--out", help="write the JSON result here")
    ap.add_argument("--quiet", action="store_true", help="print only the summary line")
    a = ap.parse_args(argv)
    if bool(a.snapshot) == bool(a.paths):
        ap.error("give either PATH... or --snapshot")
    if a.snapshot and a.genre:
        ap.error("--genre is recorded by snapshot.py; a snapshot scan reads it from there")
    if a.snapshot and a.baseline:
        ap.error("--baseline is for standalone scans; a run accounts for every hit in findings.json")
    stdin = "-" in a.paths
    if stdin and len(a.paths) != 1:
        ap.error("- reads one document from standard input and cannot be combined with other paths")
    name = Path(a.stdin_name)
    if stdin and (name.is_absolute() or ".." in name.parts or not name.parts or name.as_posix() != a.stdin_name):
        ap.error("--stdin-name must be a plain relative path such as docs/notes.md")
    rules = load_rules()
    try:
        exemptions = findings.check_record(load_json(a.exempt)).get("exemptions", []) if a.exempt else []
        baseline = load_baseline(a.baseline) if a.baseline else None
        if a.snapshot:
            result = scan_snapshot(a.snapshot, rules, exemptions)
        elif stdin:
            content = sys.stdin.buffer.read()
            root = Path(a.root).resolve() if a.root else Path.cwd().resolve()
            genres = assign_genres(a.genre, [root / a.stdin_name], root, rules)
            result = scan([a.stdin_name], root, rules, exemptions, genres, paths=[a.stdin_name], contents=[content])
        else:
            files = iter_docs(a.paths)
            if not files:
                ap.error("no document files found")
            root = Path(a.root).resolve() if a.root else Path.cwd().resolve()
            if not a.root and not all(f.resolve().is_relative_to(root) for f in files):
                root = Path(os.path.commonpath([f.resolve().parent for f in files]))
            outside = [f for f in files if not f.resolve().is_relative_to(root)]
            if outside:
                ap.error(f"{outside[0]} is outside --root {root}")
            result = scan(files, root, rules, exemptions, assign_genres(a.genre, files, root, rules))
        if baseline is not None:
            apply_baseline(result, baseline)
        if a.out:
            write_json(a.out, result)
    except (OSError, ValueError) as e:
        ap.error(str(e))
    notes = {r["id"]: r["note"] for r in rules["rules"]}
    if a.quiet:
        pass
    elif a.format == "github":
        for line in github_lines(result, notes):
            print(line)
    else:
        for h in result["hits"]:
            if h.get("exempt_by") == "baseline":
                continue  # counted in the summary; listing them would bury the new hits
            mark = f"  [exempt: {h['exempt']}]" if h["exempt"] else ""
            note = f" -- {notes[h['rule']]}" if a.explain and h["rule"] in notes else ""
            print(f"{h['path']}:{h['line']}:{h['col']} {h['rule']} {h['text']}{note}{mark}")
        for c in result["cues"]:
            print(f"{c['path']}:{c['line']} {c['perspective']} cue: {c['why']}: {c['text']}")
    s = result["summary"]
    tail = ""
    if "baseline" in s:
        tail = f", {s['baseline']} in baseline"
        if s["baseline_resolved"]:
            tail += f" ({s['baseline_resolved']} baseline hits gone; rerun with --out to tighten it)"
    print(f"{s['files']} files, {s['total']} hits, {s['open']} open, {s['exempt']} exempt, {s['cues']} cues{tail}",
          file=sys.stderr)
    return 1 if s["open"] else 0


if __name__ == "__main__":
    sys.exit(main())
