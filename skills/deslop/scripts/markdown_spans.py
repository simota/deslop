"""Shared Markdown span helpers: inline code, URLs, link destinations, reference
definitions and footnotes. Standard library only."""
import bisect
import re
import string

from common import (HEADING_LINE, HTML_ATTRIBUTES, LIST_MARKER, OPEN_FENCE, QUOTE_MARKER, SETEXT_UNDERLINE, THEMATIC_BREAK,
                    _continue_containers, _html_closer, _list_marker, _open_containers, code_blocks, indent)

BACKTICKS = re.compile(r"`+")
HTTP_SCHEME = r"(?ai:https?)://"
HTTP_URL_START = re.compile(r"<?" + HTTP_SCHEME)
HTTP_AUTOLINK = re.compile(r"<" + HTTP_SCHEME + r"[^\s<>]+>")
HTTP_IP_HOST = re.compile(r"(?:[^\s/?#\[\]<>]*@)?\[[^\s\[\]<>]+\]")
LINE_BLOCK = re.compile(
    r" {0,3}(?:#{1,6}(?:[ \t]+|$)|`{3,}|~{3,}"
    r"|(?:[-=]+|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})[ \t]*$)")


def http_url_spans(text, start=0, end=None):
    """Yield HTTP URL offsets, including autolink delimiters and punctuation.

    A bare URL can contain balanced parentheses; an unmatched closing one
    belongs to its surrounding prose. Scan once instead of expanding a
    nested regex, so arbitrarily deep URL paths stay bounded. Other bare
    URL boundaries and trailing punctuation keep their existing meaning,
    except that a bracketed IP host must retain its closing bracket. Callers
    decide whether sentence punctuation belongs to the value.
    """
    end = len(text) if end is None else end
    while match := HTTP_URL_START.search(text, start, end):
        opening, pos = match.start(), match.end()
        if text[opening] == "<":
            autolink = HTTP_AUTOLINK.match(text, opening, end)
            if autolink is not None:
                yield autolink.span()
                start = autolink.end()
                continue
            opening += 1
        host = HTTP_IP_HOST.match(text, pos, end)
        if host is not None:
            pos = host.end()
        depth = 0
        while pos < end:
            char = text[pos]
            if char.isspace() or char in ">]":
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if not depth:
                    break
                depth -= 1
            pos += 1
        if pos > match.end():
            yield opening, pos
        start = pos


def _quoted_prefix_length(line, flat, containers):
    """Raw offset through the last matched quote, including outer lists."""
    _, matched = _continue_containers(flat, containers)
    last_quote = next((i for i in range(matched - 1, -1, -1)
                       if containers[i][0] == "quote"), None)
    if last_quote is None:
        return 0
    columns, _ = _continue_containers(flat, containers[:last_quote + 1])
    column = 0
    for offset, char in enumerate(line):
        column += 4 - column % 4 if char == "\t" else 1
        if column >= columns:
            return offset + 1
    return len(line)


def inline_block_spans(text, quote_prefixes=None, *, source=None, markdown=True):
    """Keep inline spans within paragraphs and ordinary Markdown block starts.

    This is deliberately not a Markdown parser: blank lines, headings,
    separators, fences and new list/quote blocks stop a pending code span.
    Repeated quote markers continue the paragraph; omitted markers can be
    lazy continuation lines, including at a shallower quote depth.
    When blocks are masked, the original source retains their containers.
    Only a code block's opening line can establish those containers; its
    body and closing line cannot add or remove Markdown structure.
    HTML blocks also end inline spans, and their contents cannot open
    Markdown containers or supply quote prefixes for later code.
    """
    if source is not None and len(source) != len(text):
        raise ValueError("inline source and masked text must have the same length")
    blocks = iter(code_blocks(source, indented=markdown)) if source is not None else iter(())
    block = next(blocks, None)
    start = offset = 0
    containers, in_paragraph, html_end = [], False, None
    for line in (text if source is None else source).splitlines(keepends=True):
        while block is not None and block[1] <= offset:
            block = next(blocks, None)
        in_code = block is not None and block[0] <= offset < block[1]
        flat = line.rstrip("\r\n").expandtabs(4)
        end = offset + len(line)
        content, matched = _continue_containers(flat, containers)
        if html_end is not None:
            if matched == len(containers):
                if html_end.search(flat[content:]):
                    html_end = None
                start, offset, in_paragraph = end, end, False
                continue
            # Raw HTML cannot lazily continue after its outer container.
            html_end, in_paragraph = None, False
        if in_code and offset > block[0]:
            # The opening line has already ended any pending inline span.
            offset += len(line)
            start, in_paragraph = offset, False
            continue
        remaining = flat[content:]
        shallow = indent(remaining) < 4
        marker = LIST_MARKER.match(remaining) if shallow else None
        sibling = (matched < len(containers) and marker
                   and containers[matched][0] == "list" + marker.group(1)[-1])
        interrupt = in_paragraph and not sibling
        block_start = shallow and (
            LINE_BLOCK.match(remaining) or QUOTE_MARKER.match(remaining)
            or _list_marker(remaining, 0, interrupt) or _html_closer(remaining, in_para=interrupt))
        lazy = (matched < len(containers) and in_paragraph
                and remaining.strip() and not block_start)
        new_block = not in_paragraph
        if not lazy:
            new_block |= matched < len(containers)
            containers = containers[:matched]
            count = len(containers)
            content = _open_containers(flat, content, containers, interrupt)
            new_block |= len(containers) > count
        body = flat[content:]
        closer = None if in_code else _html_closer(body, in_para=not new_block)
        if closer is not None:
            yield start, offset
            html_end = None if closer.search(body) else closer
            start, offset, in_paragraph = end, end, False
            continue
        if quote_prefixes is not None:
            prefix = _quoted_prefix_length(line, flat, containers)
            if prefix:
                quote_prefixes.append((offset, offset + prefix))
        if in_code or not body.strip() or LINE_BLOCK.match(body):
            yield start, offset
            yield offset, end
            start = end
            in_paragraph = False
        else:
            if new_block:
                yield start, offset
                start = offset
            in_paragraph = True
        offset = end
    yield start, len(text)


def _escaped(text, index):
    slashes = 0
    while index > 0 and text[index - 1] == "\\":
        index -= 1
        slashes += 1
    return slashes % 2 == 1


def inline_code_candidates(text, quote_prefixes=None, *, source=None, markdown=True, blocks=None):
    """Yield (start, end, body_start, body_end) for every matching code pair.

    Candidates can overlap. Keep only offsets so callers can skip an opener
    inside another opaque construct without copying every candidate's body.
    An optional list collects source offsets of quote prefixes for content
    extraction, so callers need not scan the document again for each span.
    An optional same-length source supplies block/container boundaries;
    backtick candidates are still read from the possibly masked text.
    Callers that already collected block boundaries can supply them directly.
    """
    if blocks is None:
        blocks = inline_block_spans(text, quote_prefixes, source=source, markdown=markdown)
    for lo, hi in blocks:
        runs = list(BACKTICKS.finditer(text, lo, hi))
        closings = [None] * len(runs)
        next_by_width = {}
        # Index raw closing widths once; escaped openers lose one backtick.
        for i in range(len(runs) - 1, -1, -1):
            run = runs[i]
            raw_width = run.end() - run.start()
            width = raw_width - _escaped(text, run.start())
            closings[i] = next_by_width.get(width)
            next_by_width[raw_width] = i
        for i, opening in enumerate(runs):
            closing = closings[i]
            if closing is not None:
                start = opening.start() + _escaped(text, opening.start())
                end = runs[closing]
                yield start, end.end(), opening.end(), end.start()


def inline_code_content(text, start, end, quote_prefixes=None):
    """Return raw code content without its surrounding quote continuations.

    The prefix offsets come from the paragraph's actual containers, even
    when the opener sits on a lazy line without a marker. Literal greater-
    than signs and other whitespace inside the code remain content.
    """
    content = text[start:end]
    if "\n" not in content:
        return content
    if quote_prefixes is None:
        quote_prefixes = []
        for _ in inline_block_spans(text, quote_prefixes):
            pass
    pieces, pos = [], start
    index = bisect.bisect_left(quote_prefixes, (start,))
    while index < len(quote_prefixes):
        lo, hi = quote_prefixes[index]
        if lo >= end:
            break
        pieces.append(text[pos:lo])
        pos = min(hi, end)
        index += 1
    pieces.append(text[pos:end])
    return "".join(pieces)


# Link destinations, reference definitions and footnotes: the spans both the
# detector and the fact check must treat as protected, so they live here
# rather than in either command.
# Find the start of a URL alongside prose literals; http_url_spans supplies
# its complete boundary when the path contains balanced parentheses.
URL = re.compile(rf"(?P<autolink><{HTTP_SCHEME}[^\s<>]+>)|(?P<bare>{HTTP_SCHEME}[^\s)>\]]+)")
LINK_LABEL = re.compile(r" {0,3}\[(?!\^)(?:\\[^\r\n]|[^\[\]\\\r\n])+\]:")
LINK_SPACE = re.compile(r"[ \t]*(?:\r?\n[ \t]*)?")
BLANK_LINE = re.compile(r"\r?\n[ \t]*\r?\n")
# Escapes, line ends and brackets: protected_inline_spans acts only on these
# characters outside the code, definition and autolink starts it indexes.
STRUCTURAL = re.compile(r"[\\\r\n\[\]]")
# What _bare_destination_ends reads: escapes, parentheses and everything that
# ends a bare destination (whitespace, control characters and "<"). \s is
# exactly str.isspace() for str patterns.
DESTINATION_MARK = re.compile(r"[\\()<\s\x00-\x1f]")
FOOTNOTE = re.compile(r"\[\^[^\]\s]+\]")
FOOTNOTE_DEFINITION = re.compile(r" {0,3}(" + FOOTNOTE.pattern + r"):")
INLINE_HTML = re.compile(
    r"</[A-Za-z][A-Za-z0-9-]*[ \t\r\n]*>|"
    r"<[A-Za-z][A-Za-z0-9-]*" + HTML_ATTRIBUTES.replace(r"[ \t]", r"[ \t\r\n]") + r"[ \t\r\n]*/?>|"
    r"<!--(?:>|->|[\s\S]*?-->)|<\?[\s\S]*?\?>|"
    r"<![A-Za-z][^>]*>|<!\[CDATA\[[\s\S]*?\]\]>")


def link_target(url):
    """An explicit destination as written, without its <> delimiters."""
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1]
    return url


def _escaped_character(text, pos):
    return text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in string.punctuation


def _bare_destination_ends(text):
    """Index balanced targets once so repeated unmatched openers stay linear.

    Any other character ends where the character after it does, so a run of
    them shares the end of the next character here and is filled at once.
    """
    ends = [len(text)] * (len(text) + 1)
    # Link each such character to the one before it in ends itself, then
    # walk the links back: each slot is final before anything reads it.
    pos = -1
    for match in DESTINATION_MARK.finditer(text):
        ends[match.start()] = pos
        pos = match.start()
    after = len(text)
    while pos >= 0:
        previous = ends[pos]
        if pos + 1 < after:
            ends[pos + 1:after] = [ends[after]] * (after - pos - 1)
        char = text[pos]
        if _escaped_character(text, pos):
            ends[pos] = ends[pos + 2]
        elif char == "(":
            close = ends[pos + 1]
            ends[pos] = ends[close + 1] if 0 <= close < len(text) and text[close] == ")" else -1
        elif char == "\\":
            ends[pos] = ends[pos + 1]
        else:
            ends[pos] = pos
        after, pos = pos, previous
    if after:
        ends[:after] = [ends[after]] * after
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
    code_starts, definition_starts = sorted(codes), sorted(definitions)

    def next_stop(pos):
        """The first offset from pos where the loop below does more than
        step forward: a structural character, a code or definition start,
        or the next autolink. Leaving a block only clears the pending
        brackets, which the next stop still does before reading any."""
        stop = STRUCTURAL.search(text, pos)
        stop = len(text) if stop is None else stop.start()
        for starts in (code_starts, definition_starts):
            i = bisect.bisect_left(starts, pos)
            if i < len(starts) and starts[i] < stop:
                stop = starts[i]
        if protected is not None and pos <= protected[0] < stop:
            stop = protected[0]
        return stop

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
            pos = next_stop(pos + 1)
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
        pos = next_stop(pos + 1)
