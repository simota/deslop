"""Small shared Markdown span helpers; standard library only."""
import bisect
import re

from common import (_continue_containers, _html_closer, _list_marker, _open_containers,
                    LIST_MARKER, QUOTE_MARKER, code_blocks, indent)

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
        marker = LIST_MARKER.match(remaining) if indent(remaining) < 4 else None
        sibling = (matched < len(containers) and marker
                   and containers[matched][0] == "list" + marker.group(1)[-1])
        interrupt = in_paragraph and not sibling
        block_start = indent(remaining) < 4 and (
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
