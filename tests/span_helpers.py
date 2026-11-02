"""Test-only views over markdown_spans. Import after adding the scripts directory to sys.path."""
from markdown_spans import inline_code_candidates, inline_code_content


def inline_code_spans(text):
    """Return (start, end, content) tuples for complete inline code spans.

    Offsets include the delimiters; content retains its original whitespace
    and line endings apart from continuation quote markers. Delimiters must
    have exactly the same length. An
    escaped opening backtick is literal, but backslashes inside a code span
    do not escape its closing delimiter. Callers handle fenced blocks first.
    """
    spans, quote_prefixes, end = [], [], 0
    for start, stop, body_start, body_end in inline_code_candidates(text, quote_prefixes):
        if start >= end:
            spans.append((start, stop, inline_code_content(text, body_start, body_end, quote_prefixes)))
            end = stop
    return spans
