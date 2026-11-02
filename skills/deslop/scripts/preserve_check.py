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
import bisect
import hashlib
import re
import string
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from common import (HEADING_LINE, HTML_ATTRIBUTES, LIST_MARKER, OPEN_FENCE, QUOTE_MARKER, SETEXT_UNDERLINE, THEMATIC_BREAK,
                    _continue_containers, _html_closer, _list_marker, _open_containers, code_blocks, indent,
                    decode_text, is_markdown, load_json, load_snapshot, read_text, sha256_bytes, write_json)
from findings import check_record
from markdown_spans import (HTTP_SCHEME, _escaped, http_url_spans, inline_block_spans,
                            inline_code_candidates, inline_code_content)

# Find the start of a URL alongside prose literals; http_url_spans supplies
# its complete boundary when the path contains balanced parentheses.
URL = re.compile(rf"(?P<autolink><{HTTP_SCHEME}[^\s<>]+>)|(?P<bare>{HTTP_SCHEME}[^\s)>\]]+)")
LINK_LABEL = re.compile(r" {0,3}\[(?!\^)(?:\\[^\r\n]|[^\[\]\\\r\n])+\]:")
LINK_SPACE = re.compile(r"[ \t]*(?:\r?\n[ \t]*)?")
BLANK_LINE = re.compile(r"\r?\n[ \t]*\r?\n")
FOOTNOTE = re.compile(r"\[\^[^\]\s]+\]")
FOOTNOTE_DEFINITION = re.compile(r" {0,3}(" + FOOTNOTE.pattern + r"):")
INLINE_HTML = re.compile(
    r"</[A-Za-z][A-Za-z0-9-]*[ \t\r\n]*>|"
    r"<[A-Za-z][A-Za-z0-9-]*" + HTML_ATTRIBUTES.replace(r"[ \t]", r"[ \t\r\n]") + r"[ \t\r\n]*/?>|"
    r"<!--(?:>|->|[\s\S]*?-->)|<\?[\s\S]*?\?>|"
    r"<![A-Za-z][^>]*>|<!\[CDATA\[[\s\S]*?\]\]>")
NUMBER_BODY = r"(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?"
# A hyphen after a digit or identifier belongs to a date, range or name.
NUMBER = re.compile(rf"(?<![A-Za-z0-9_.,])[+-]{NUMBER_BODY}|{NUMBER_BODY}")
KINDS = ("code_block", "inline_code", "url", "footnote", "number")
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
    marked, previous = [], ""
    for c in text:
        tag = unicodedata.decomposition(c).partition(" ")[0]
        script = tag if tag in ("<super>", "<sub>") else ""
        if script != previous:
            marked.append("^")
        marked.append(c)
        previous = script
    return unicodedata.normalize("NFKC", "".join(marked)).replace("\u2212", "-")


def link_target(url):
    """An explicit destination as written, without its <> delimiters."""
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1]
    return url


def _escaped_character(text, pos):
    return text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in string.punctuation


def _bare_destination_ends(text):
    """Index balanced targets once so repeated unmatched openers stay linear."""
    ends = [len(text)] * (len(text) + 1)
    for pos in range(len(text) - 1, -1, -1):
        char = text[pos]
        if _escaped_character(text, pos):
            ends[pos] = ends[pos + 2]
        elif char == "(":
            close = ends[pos + 1]
            ends[pos] = ends[close + 1] if 0 <= close < len(text) and text[close] == ")" else -1
        elif char == ")" or char.isspace() or ord(char) < 32 or char == "<":
            ends[pos] = pos
        else:
            ends[pos] = ends[pos + 1]
    return ends


def _destination_end(text, pos, bare_ends, limit=None):
    """Read one inline or reference destination without interpreting its contents."""
    limit = len(text) if limit is None else limit
    if pos < limit and text[pos] == "<":
        pos += 1
        while pos < limit:
            char = text[pos]
            if _escaped_character(text, pos):
                pos += 2
                continue
            if char == ">":
                pos += 1
                break
            if char in "<\r\n":
                return None
            pos += 1
        else:
            return None
    else:
        pos = bare_ends[pos]
        if pos < 0 or pos > limit:
            return None
    return pos


def _inline_destination(text, opening, bare_ends, limit):
    """Read a destination and its closing syntax, leaving titles as prose."""
    start = LINK_SPACE.match(text, opening + 1, limit).end()
    pos = _destination_end(text, start, bare_ends, limit)
    if pos is None:
        return None
    end = pos
    tail = LINK_SPACE.match(text, pos, limit).end()
    if tail > pos and tail < limit and text[tail] in "\"'(":
        delimiter = ")" if text[tail] == "(" else text[tail]
        pos = tail + 1
        while pos < limit:
            if _escaped_character(text, pos):
                pos += 2
                continue
            if text[pos] == delimiter:
                break
            if (delimiter == ")" and text[pos] == "(") or BLANK_LINE.match(text, pos, limit):
                return None
            pos += 1
        if pos >= limit:
            return None
        tail = LINK_SPACE.match(text, pos + 1, limit).end()
    if tail < limit and text[tail] == ")":
        return start, end, tail + 1
    return None


def _reference_content(body, column, offset):
    """Remove container columns without expanding tabs in the destination."""
    raw = width = 0
    while width < column:
        width += 4 - width % 4 if body[raw] == "\t" else 1
        raw += 1
    extra = width - column
    return " " * extra + body[raw:], offset + raw - extra


def _reference_lines(text, markdown=True):
    """Project lines with paragraph state committed by the reference reader.

    Send the last consumed line only after a valid definition. Failed
    candidates start an ordinary paragraph; tentative lookahead does not
    open containers or reset that paragraph.
    """
    raw_lines = text.splitlines(keepends=True)
    starts = [0]
    for line in raw_lines:
        starts.append(starts[-1] + len(line))
    blocks = code_blocks(text, indented=markdown)
    block_starts = [block[0] for block in blocks]

    def block_at(offset):
        index = bisect.bisect_right(block_starts, offset) - 1
        return blocks[index] if index >= 0 and offset < blocks[index][1] else None

    containers, index, in_para, html_end = [], 0, False, None
    while index < len(raw_lines):
        offset = starts[index]
        body = raw_lines[index].rstrip("\r\n")
        flat = body.expandtabs(4)
        column, matched = _continue_containers(flat, containers)
        if html_end is not None:
            if matched == len(containers):
                content, content_offset = _reference_content(body, column, offset)
                if html_end.search(content):
                    html_end = None
                # HTML bodies cannot open Markdown containers or definitions.
                yield index, content, content_offset, False, None
                index, in_para = index + 1, False
                continue
            # HTML cannot lazily continue outside its original container.
            html_end, in_para = None, False
        block = block_at(offset)
        if block is not None and offset > block[0]:
            # Code content cannot open containers or reference definitions.
            yield index, "", offset, False, None
            index, in_para = index + 1, False
            continue
        continued = matched == len(containers)
        remaining = flat[column:]
        marker = LIST_MARKER.match(remaining) if indent(remaining) < 4 else None
        sibling = (matched < len(containers) and marker
                   and containers[matched][0] == "list" + marker.group(1)[-1])
        interrupt = in_para and not sibling
        block_start = indent(remaining) < 4 and (
            any(rx.match(remaining) for rx in (THEMATIC_BREAK, HEADING_LINE, OPEN_FENCE, QUOTE_MARKER))
            or _list_marker(remaining, 0, interrupt) or _html_closer(remaining, in_para=interrupt))
        # Match code_blocks: omitted paragraph prefixes do not end a list
        # or quote until a real block boundary closes the container.
        lazy = matched < len(containers) and in_para and remaining.strip() and not block_start
        if not lazy:
            containers = containers[:matched]
            count = len(containers)
            column = _open_containers(flat, column, containers, interrupt)
            if len(containers) > count:
                in_para = False
        content, content_offset = _reference_content(body, column, offset)
        if block is not None:
            content = ""
        else:
            closer = _html_closer(content, in_para=in_para)
            if closer is not None:
                html_end = None if closer.search(content) else closer
                yield index, content, content_offset, False, None
                index, in_para = index + 1, False
                continue

        def following(at):
            if at == index:
                return content, content_offset
            if at >= len(raw_lines) or block_at(starts[at]) is not None:
                return None
            line = raw_lines[at].rstrip("\r\n")
            flat = line.expandtabs(4)
            column, matched = _continue_containers(flat, containers)
            if matched != len(containers):
                return None
            opened = list(containers)
            _open_containers(flat, column, opened, in_para=True)
            if len(opened) != len(containers):
                return None
            body, offset = _reference_content(line, column, starts[at])
            if (_html_closer(body, in_para=True) is not None
                    or any(rx.match(body) for rx in (HEADING_LINE, THEMATIC_BREAK, SETEXT_UNDERLINE))):
                return None
            return body, offset

        consumed = yield index, content, content_offset, not in_para, following
        if consumed is not None:
            index, in_para = consumed + 1, False
            continue
        # A Setext underline needs a paragraph in this same container;
        # omitted quote/list prefixes cannot lazily supply the underline.
        setext = in_para and continued and SETEXT_UNDERLINE.match(content)
        in_para = bool(content.strip()) and not setext and not any(
            rx.match(content) for rx in (HEADING_LINE, THEMATIC_BREAK))
        index += 1


def _reference_title_end(line_at, index, pos):
    """A title may wrap within its container, but never across a blank line."""
    text, _ = line_at(index)
    delimiter = ")" if text[pos] == "(" else text[pos]
    pos += 1
    while True:
        while pos < len(text):
            if _escaped_character(text, pos):
                pos += 2
                continue
            if text[pos] == delimiter:
                return (index, pos + 1) if not text[pos + 1:].strip() else None
            if delimiter == ")" and text[pos] == "(":
                return None
            pos += 1
        index += 1
        line = line_at(index)
        if line is None or not line[0].strip():
            return None
        text, _ = line
        pos = 0


def _reference_definitions(text, markdown=True):
    """Map each reference label to its destination and complete definition span."""
    if "]:" not in text:
        return {}
    lines = _reference_lines(text, markdown)
    definitions, consumed = {}, None
    while True:
        try:
            index, body, offset, eligible, line_at = lines.send(consumed)
        except StopIteration:
            break
        consumed = None
        if not eligible:
            continue
        label = LINK_LABEL.match(body)
        if not label:
            continue
        start, current = offset + label.start(), index
        pos = label.end()
        pos += len(body[pos:]) - len(body[pos:].lstrip(" \t"))
        if pos == len(body):
            current += 1
            line = line_at(current)
            if line is None:
                continue
            body, offset = line
            pos = len(body) - len(body.lstrip(" \t"))
        end = _destination_end(body, pos, _bare_destination_ends(body))
        if end is None or end == pos:
            continue
        target, target_end = link_target(body[pos:end]), offset + end
        tail = end + len(body[end:]) - len(body[end:].lstrip(" \t"))
        finish = current, len(body)
        if tail < len(body):
            if tail == end or body[tail] not in "\"'(":
                continue
            finish = _reference_title_end(line_at, current, tail)
            if finish is None:
                continue
        else:
            following = line_at(current + 1)
            if following is not None:
                title = following[0]
                title_start = len(title) - len(title.lstrip(" \t"))
                if title_start < len(title) and title[title_start] in "\"'(":
                    finish = _reference_title_end(line_at, current + 1, title_start) or finish
        consumed, final_column = finish
        definitions[start] = target_end, line_at(consumed)[1] + final_column, target
    return definitions


def _inline_html_spans(source, visible, markdown, titles):
    """Recognize complete raw HTML syntax within existing inline blocks.

    Match source syntax, not blanks left by masking code or URLs. An opener
    inside code, a destination or a link title cannot consume later prose.
    Quote continuation prefixes are structural whitespace, as for links.
    """
    quote_prefixes = []
    blocks = list(inline_block_spans(source, quote_prefixes, source=source, markdown=markdown))
    pieces, end = [], 0
    for start, stop in quote_prefixes:
        pieces.extend((source[end:start], " " * (stop - start)))
        end = stop
    projected = "".join(pieces) + source[end:]
    title_starts = [start for start, _ in titles]
    # HTML-looking text inside a label belongs to that label. HTML that
    # starts outside it is still recognized first and can contain literals.
    labels = [match.span() for match in FOOTNOTE.finditer(visible) if not _escaped(visible, match.start())]
    label_starts = [start for start, _ in labels]
    for start, stop in blocks:
        last_closers = {">": projected.rfind(">", start, stop)}
        pos = start
        while pos < stop:
            pos = projected.find("<", pos, stop)
            if pos < 0 or pos > last_closers[">"]:
                break
            title = bisect.bisect_right(title_starts, pos) - 1
            in_title = title >= 0 and pos < titles[title][1]
            label = bisect.bisect_right(label_starts, pos) - 1
            in_label = label >= 0 and pos < labels[label][1]
            if visible[pos] != "<" or in_title or in_label or _escaped(source, pos):
                pos += 1
                continue
            # Repeated unclosed comments must not rescan the whole paragraph
            # for the same missing terminator at each opener.
            closer = next((ending for opening, ending in (("<!--", "-->"), ("<?", "?>"),
                                                          ("<![CDATA[", "]]>"))
                           if projected.startswith(opening, pos)), None)
            if closer is not None and not projected.startswith(("<!-->", "<!--->"), pos):
                if closer not in last_closers:
                    last_closers[closer] = projected.rfind(closer, start, stop)
                if pos > last_closers[closer]:
                    pos += 1
                    continue
            match = INLINE_HTML.match(projected, pos, stop)
            if match is None:
                pos += 1
            else:
                yield match.span()
                pos = match.end()


def _footnote_context(source, visible, markdown, titles):
    """Locate definition labels and literal regions in the original context.

    Footnote definitions may interrupt a paragraph, unlike link reference
    definitions. Neither code/URL masking nor a colon in prose can move a
    label to the start of its line. Link titles and raw HTML syntax cannot
    supply either role; their other prose facts remain visible to facts().
    """
    references = _reference_definitions(source, markdown)
    literals = sorted([*titles, *_inline_html_spans(source, visible, markdown, titles)])
    excluded = list(literals)
    literal_starts = [start for start, _ in literals]
    line_ends, end = [], 0
    for line in source.splitlines(keepends=True):
        end += len(line)
        line_ends.append(end)
    lines = _reference_lines(source, markdown)
    starts, consumed = set(), None
    while True:
        try:
            index, body, offset, _, line_at = lines.send(consumed)
        except StopIteration:
            break
        consumed = None
        reference = references.get(offset)
        if reference is not None:
            consumed = bisect.bisect_left(line_ends, reference[1])
            continue
        if line_at is None:
            excluded.append((line_ends[index - 1] if index else 0, line_ends[index]))
            continue
        definition = FOOTNOTE_DEFINITION.match(body)
        if definition is not None:
            start = offset + definition.start(1)
            literal = bisect.bisect_right(literal_starts, start) - 1
            in_literal = literal >= 0 and start < literals[literal][1]
            if not in_literal and visible.startswith(definition.group(1), start):
                starts.add(start)
                consumed = index
    return starts, sorted(excluded)


def protected_inline_spans(text, *, source=None, markdown=True, title_spans=None):
    """Yield code and URL facts in document order, keeping their contents opaque.

    If blocks are masked, source retains the original container prefixes at
    the same offsets. References after a block still belong to its list.
    An optional list collects the suffix containing each parsed link title;
    its text carries prose facts, but cannot contain Markdown footnotes.
    """
    source = text if source is None else source
    if len(source) != len(text):
        raise ValueError("inline source and masked text must have the same length")
    quote_prefixes = []
    blocks = list(inline_block_spans(text, quote_prefixes, source=source, markdown=markdown))
    codes = {start: (end, body_start, body_end) for start, end, body_start, body_end in
             inline_code_candidates(text, blocks=blocks)}
    # Parse continuation prefixes as whitespace without moving any source
    # offsets or changing literal greater-than signs in a destination.
    pieces, end = [], 0
    for start, stop in quote_prefixes:
        pieces.extend((text[end:start], " " * (stop - start)))
        end = stop
    destinations = "".join(pieces) + text[end:]
    bare_ends = _bare_destination_ends(destinations)
    definitions = _reference_definitions(source, markdown)
    autolinks = ((start, stop) for start, stop in http_url_spans(text) if text[start] == "<")
    protected = next(autolinks, None)
    block_iter = iter(blocks)
    block = next(block_iter, None)
    brackets, pos = [], 0
    while pos < len(text):
        while block is not None and block[1] <= pos:
            brackets.clear()
            block = next(block_iter, None)
        while protected is not None and protected[1] <= pos:
            protected = next(autolinks, None)
        if protected is not None and protected[0] <= pos:
            # A URL's literal brackets/backticks do not start nested syntax.
            yield "url", *protected, link_target(text[protected[0]:protected[1]])
            pos = protected[1]
            continue
        if pos in codes:
            end, body_start, body_end = codes[pos]
            yield "inline_code", pos, end, inline_code_content(text, body_start, body_end, quote_prefixes)
            while protected is not None and protected[0] < end:
                protected = next(autolinks, None)
            pos = end
            continue
        if pos in definitions:
            end, stop, target = definitions[pos]
            yield "url", pos, end, target
            if title_spans is not None:
                title_spans.append((end, stop))
            pos = stop
            continue
        if _escaped_character(text, pos):
            pos += 2
            continue
        if BLANK_LINE.match(text, pos):
            brackets.clear()
        if block is None or pos < block[0]:
            pos += 1
            continue
        if text[pos] == "[":
            brackets.append(pos)
        elif text[pos] == "]" and brackets:
            brackets.pop()
            if pos + 1 < len(text) and text[pos + 1] == "(":
                destination = _inline_destination(destinations, pos + 1, bare_ends, block[1])
                if destination is not None:
                    start, end, pos = destination
                    if title_spans is not None:
                        title_spans.append((end, pos))
                    if end > start:
                        yield "url", start, end, link_target(text[start:end])
                    continue
        pos += 1


def code(text, markdown=True):
    """Code block bodies, and text with every block masked at its original offsets."""
    spans = code_blocks(text, indented=markdown)
    rest = text
    for start, end, _, _ in reversed(spans):
        rest = rest[:start] + re.sub(r"[^\r\n]", " ", rest[start:end]) + rest[end:]
    return [text[b:e] for _, _, b, e in spans], rest


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


def check(out):
    out = Path(out)
    snap, work = load_snapshot(out)
    findings = out / "findings.json"
    acks = check_record(load_json(findings)).get("preservation", []) if findings.exists() else []
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
