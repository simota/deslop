"""Perspective cues: places where a structural or content perspective
probably applies, found from the shape of the whole document.

Cues are not hits. They change no exit code and need no finding or
exemption; they tell the whole-document read in DETECT and VERIFY where to
look first. A perspective cued in the originals cannot be recorded as N/A.
"""
import re
from collections import Counter

from common import SETEXT_UNDERLINE, code_blocks

HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
BREAK = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
TOKEN = {
    "ja": re.compile(r"[一-龯々〆ヵヶ]{2,}|[ァ-ヴー]{2,}|[A-Za-z][A-Za-z0-9'-]{2,}"),
    "en": re.compile(r"[A-Za-z][A-Za-z'-]{3,}"),
}
STOP = set("""this that with from have will your they them their there what when which would about
into more than then also only each such some very just been were does here these those over
used using make makes while where other""".split())

ANNOUNCE = {
    "en": re.compile(r"^(?:In this (?:guide|article|post|tutorial|document|page|section|README)\b"
                     r"|This (?:guide|article|post|tutorial|document|page|section|README) (?:will |is going to )?"
                     r"(?:covers?|explains?|describes?|shows?|walks?|introduces?|provides?|discusses?|looks? at|goes over|outlines?)\b"
                     r"|(?:Below|Here),? (?:we|you)(?:['’]ll| will)\b)", re.I),
    "ja": re.compile(r"^(?:ここでは|このページでは|本ページでは|本章では|この章では|本節では|以下では|本書では"
                     r"|本記事では|この記事では|本稿では|本ドキュメントでは|このドキュメントでは)"),
}
SUMMARY = re.compile(r"^(?:conclusions?|summary|in summary|recap|wrap(?:ping)?[- ]up|final thoughts|closing thoughts"
                     r"|(?:key )?takeaways?|まとめ|おわりに|終わりに|結論|総括|最後に)\b", re.I)
MORAL = {
    "en": re.compile(r"^(?:This|That|These|Such|Doing so|As a result|Ultimately|Together)\b[^.!?]{0,120}?"
                     r"\b(?:makes?|ensures?|allows?|helps?|enables?|keeps?|lets?|gives?|means?|leads? to|results? in|improves?)\b"
                     r"|^(?:This|That) is (?:why|what|how)\b"),
    "ja": re.compile(r"^(?:これにより|これによって|こうすることで|このため|そのため|その結果|これで|こうして|結果として)"
                     r"|(?:ようになります|やすくなります|につながります|に役立ちます|を実現できます|が向上します|が高まります)。$"),
}
RESTATE = re.compile(r"^(?:In other words|Put simply|Simply put|To put it (?:another way|simply)|That is to say|Put another way)\b")
QUESTION = re.compile(r"(?:[?？]|とは|とは何か)\s*$")
COVERAGE = re.compile(r"\b(?:benefits|advantages|disadvantages|pros and cons|use cases|best practices|security considerations"
                      r"|future (?:work|outlook|directions|prospects)|frequently asked questions|FAQs?)\b|^why (?:use|choose)\b"
                      r"|メリット|デメリット|利点|活用(?:事例|シーン|方法|例)|ユースケース|ベストプラクティス|今後の展望|将来性|よくある質問",
                      re.I)
# A pattern that repeats through a document is shown at its first few places.
PER_PERSPECTIVE = 5
POLITE = re.compile(r"(?:です|ます|でした|ました|ません|でしょう|ください|ましょう)$")
PLAIN = re.compile(r"(?:だ|である|だった|であった|ない|なかった|[うくすつぬふむゆるぐぶたい])$")
DETAILS = re.compile(r"^ {0,3}<details(?:[ \t>]|$)", re.I)
SUMMARY_END = re.compile(r"</summary>[ \t]*$", re.I)
# About one screen of a rendered description.
FOLD_LINES = 20
# Qualities a prompt can demand without saying what meets them.
QUALITY = re.compile(r"\b(?:robust|scalable|maintainable|readable|clean|efficient|elegant|high-quality|professional"
                     r"|secure|performant|reliable|extensible|flexible|optimal)\b"
                     r"|堅牢|拡張性|保守性|可読性|高品質|効率的|洗練|美しい|安全(?:性|な)|高性能|信頼性|柔軟|読みやすい"
                     r"|わかりやすい|分かりやすい|最適", re.I)
# Directions that leave the decision to whoever reads them.
VAGUE = re.compile(r"\b(?:appropriately|properly|as (?:needed|appropriate|necessary)|if (?:needed|necessary)|nicely"
                   r"|in a good way|whatever (?:is|seems) best)\b"
                   r"|適切に|適宜|いい感じに|良い感じに|よしなに|うまく|きれいに|ちゃんと|しっかり(?:と)?|必要に応じて", re.I)
STACK = 3


def code_lines(text, markdown=True):
    """Zero-based numbers of the lines that code blocks cover."""
    code, pos, line = set(), 0, 0
    # Blocks come in document order: count newlines from the previous block
    # instead of from the start of the text for each one.
    for start, end, _, _ in code_blocks(text, indented=markdown):
        line += text.count("\n", pos, start)
        last = line + text.count("\n", start, max(start, end - 1))
        code.update(range(line, last + 1))
        pos = start
    return code


def parse(text, prose, markdown=True):
    """Headings and blocks (para, list, code, table, quote) in document order.
    prose is text with code and URLs blanked, so offsets and lines agree."""
    code = code_lines(text, markdown)
    out, cur, gap = [], None, False
    for i, line in enumerate(prose.split("\n")):
        n, s = i + 1, line.strip()
        if i in code:
            if not cur or cur["kind"] != "code":
                cur = {"kind": "code", "line": n, "lines": []}
                out.append(cur)
            gap = False
            continue
        if not s:
            gap = True
            if cur and cur["kind"] != "list":
                cur = None
            continue
        if cur and cur["kind"] == "para" and not gap and SETEXT_UNDERLINE.match(line.rstrip("\r")):
            # An underline completes the preceding paragraph as one heading;
            # a blank line before it still makes dashes a thematic break.
            cur.update(kind="heading", level=1 if s.startswith("=") else 2,
                       text=" ".join(cur.pop("lines")).strip(), end_line=n)
            cur, gap = None, False
            continue
        h = HEADING.match(line)
        if h or BREAK.match(line):
            cur, gap = None, False
            if h:
                out.append({"kind": "heading", "line": n, "level": len(h.group(1)), "text": h.group(2).strip()})
            continue
        m = LIST_ITEM.match(line)
        if cur and cur["kind"] == "list":
            if m and len(m.group(1)) < cur["indent"] + 2:
                cur["items"] += 1
            elif not m and gap and len(line) - len(line.lstrip()) < 2:
                cur = None
            if cur:
                cur["lines"].append(s)
                gap = False
                continue
        if m:
            cur = {"kind": "list", "line": n, "lines": [s], "items": 1, "indent": len(m.group(1))}
            out.append(cur)
            gap = False
            continue
        kind = "table" if s.startswith("|") else "quote" if s.startswith(">") else "para"
        if not cur or cur["kind"] != kind or gap:
            cur = {"kind": kind, "line": n, "lines": []}
            out.append(cur)
        cur["lines"].append(s)
        gap = False
    return out


def normalized_headings(prose, markdown=True, *, source=None):
    """Project Setext headings to ATX for sentence and density calculations.

    This projection is only for metrics: cue locations retain the original
    first heading line, and detection offsets still use unmodified prose.
    """
    lines = prose.split("\n")
    if not any(SETEXT_UNDERLINE.match(line.rstrip("\r")) for line in lines):
        return prose
    for entry in parse(prose if source is None else source, prose, markdown):
        if entry["kind"] == "heading" and "end_line" in entry:
            lines[entry["line"] - 1] = "#" * entry["level"] + " " + entry["text"]
            for i in range(entry["line"], entry["end_line"]):
                lines[i] = ""
    return "\n".join(lines)


def sections(entries):
    """One entry per heading: its own blocks up to the next heading, and
    everything up to the next heading at its level or above."""
    out = []
    for i, h in enumerate(entries):
        if h["kind"] != "heading":
            continue
        own, nested = [], []
        for e in entries[i + 1:]:
            if e["kind"] == "heading" and e["level"] <= h["level"]:
                break
            if e["kind"] == "heading" or nested:
                nested.append(e)
            else:
                own.append(e)
        out.append({"heading": h, "own": own, "all": own + nested, "children": bool(nested)})
    return out


def tokens(text, lang):
    words = (w.lower().removesuffix("'s").removesuffix("’s") for w in TOKEN[lang].findall(text))
    return {w[:-1] if lang == "en" and len(w) > 4 and w.endswith("s") else w for w in words if w not in STOP}


def body(block):
    return "\n".join(block["lines"])


def line_of(block, sentence):
    """The line of block where sentence starts, or the block's first line."""
    head = sentence.strip()[:8]
    for k, line in enumerate(block["lines"]):
        if head and head in line:
            return block["line"] + k
    return block["line"]


def find(text, prose, lang, split, markdown=True, chars=0, min_chars=0, quiet=()):
    """Return the cues for one document. split(text, lang) gives sentences;
    quiet names perspectives the document's genre does not cue. Cues that
    rest on proportions need min_chars of prose, as density rules do."""
    entries = parse(text, prose, markdown)
    blocks = [e for e in entries if e["kind"] != "heading"]
    paras = [b for b in blocks if b["kind"] == "para"]
    secs = sections(entries)
    raw = text.split("\n")
    sents = {id(b): split(body(b), lang) for b in paras}
    out, shown = [], Counter()

    def cue(line, perspective, why):
        shown[perspective] += 1
        if perspective not in quiet and shown[perspective] <= PER_PERSPECTIVE:
            out.append({"line": line, "perspective": perspective, "text": raw[line - 1].strip()[:80], "why": why})

    # STR-01: the first paragraph, before any heading but the title.
    title, first = None, None
    for k, e in enumerate(entries):
        if e["kind"] == "heading":
            if k == 0 and e["level"] == 1:
                title = e["text"]
                continue
            break
        if e["kind"] == "para":
            first = e
        break
    if first and sents[id(first)]:
        s0 = sents[id(first)][0]
        if ANNOUNCE[lang].search(s0):
            cue(first["line"], "STR-01", "the opening sentence announces what the document will do")
        elif title:
            f = tokens(s0, lang)
            if len(f) >= 2 and len(f & tokens(title, lang)) / len(f) >= 0.5:
                cue(first["line"], "STR-01", "the opening sentence mostly repeats the title")

    # STR-02: a last section named as a summary, or short and made of words already used.
    last = secs[-1] if secs else None
    closing = None
    if last and last["heading"]["level"] >= 2 and last["own"] and not last["children"] \
            and all(b["kind"] == "para" for b in last["own"]):
        if SUMMARY.search(last["heading"]["text"]):
            cue(last["heading"]["line"], "STR-02", "the last section is a summary by name")
        else:
            closing, start = last["own"], last["heading"]["line"]
    elif not last and len(blocks) >= 4 and blocks[-1]["kind"] == "para":
        closing, start = [blocks[-1]], blocks[-1]["line"]
    if closing and sum(len(sents[id(b)]) for b in closing) <= 3:
        before = "\n".join(prose.split("\n")[:start - 1])
        c = tokens("\n".join(body(b) for b in closing), lang)
        if len(c) >= 5 and len(c & tokens(before, lang)) / len(c) >= 0.85:
            cue(closing[0]["line"], "STR-02", "the closing repeats words the body already used")

    # STR-14 and CON-05: what the headings say.
    headings = [e for e in entries if e["kind"] == "heading" and e["level"] >= 2]
    for h in headings:
        if QUESTION.search(h["text"]):
            cue(h["line"], "STR-14", "heading phrased as the reader's question")
    stock = [h for h in headings if COVERAGE.search(h["text"])]
    if len(stock) >= 2:
        for h in stock:
            cue(h["line"], "CON-05", f"one of {len(stock)} headings naming a stock section")

    # STR-11: a sentence that says the previous one again.
    for b in paras:
        ss = sents[id(b)]
        for a, s in zip(ss, ss[1:]):
            ta, ts = tokens(a, lang), tokens(s, lang)
            if (lang == "en" and RESTATE.match(s)) or \
                    (len(ta) >= 4 and len(ts) >= 4 and len(ta & ts) / len(ta | ts) >= 0.5):
                cue(line_of(b, s), "STR-11", "this sentence restates the one before it")

    # STR-17: a long description with nothing folded, or a fold that hides its point or its Markdown.
    if markdown:
        code = code_lines(text, markdown)
        live = [(i, line) for i, line in enumerate(raw) if i not in code and line.strip()]
        folds = [i for i, line in live if DETAILS.match(line)]
        filled = sum(1 for line in raw if line.strip())
        if not folds and filled >= FOLD_LINES:
            cue(live[0][0] + 1, "STR-17", f"{filled} lines and nothing folded into <details>")
        if folds and not any(b["line"] <= folds[0] for b in paras):
            cue(folds[0] + 1, "STR-17", "nothing before the fold says what the change does")
        for i, line in live:
            after = raw[i + 1].strip() if i + 1 < len(raw) else ""
            if SUMMARY_END.search(line) and after and not after.startswith("<"):
                cue(i + 2, "STR-17", "no blank line after </summary>, so this is not rendered as Markdown")

    # STR-18: an instruction whose success nobody could check.
    for b in blocks:
        if b["kind"] not in ("para", "list"):
            continue
        for s in split(body(b), lang):
            if re.search(r"\d", s):
                continue
            qualities = {m.group().lower() for m in QUALITY.finditer(s)}
            vague = VAGUE.search(s)
            if len(qualities) >= STACK:
                cue(line_of(b, s), "STR-18", f"{len(qualities)} qualities demanded and nothing says when they are met")
            elif vague:
                cue(line_of(b, s), "STR-18", f"'{vague.group()}' leaves the decision to the model")

    if chars < min_chars:
        return sorted(out, key=lambda c: (c["line"], c["perspective"]))

    # STR-03: paragraphs that close by judging what they said.
    multi = [b for b in paras if len(sents[id(b)]) >= 2]
    moral = [b for b in multi if MORAL[lang].search(sents[id(b)][-1])]
    if len(multi) >= 3 and len(moral) >= 2 and len(moral) / len(multi) >= 0.4:
        for b in moral:
            cue(line_of(b, sents[id(b)][-1]), "STR-03",
                f"one of {len(moral)} of {len(multi)} paragraphs ending on an evaluation")

    # STR-04: lists of exactly three, again and again.
    lists = [b for b in blocks if b["kind"] == "list"]
    three = [b for b in lists if b["items"] == 3]
    if len(three) >= 2 and len(three) / len(lists) >= 0.6:
        for b in three:
            cue(b["line"], "STR-04", f"one of {len(three)} of {len(lists)} lists with exactly three items")

    # STR-05: headings over a sentence or two of prose.
    subs = [s for s in secs if s["heading"]["level"] >= 2]
    thin = [s for s in subs if s["own"] and not s["children"] and all(b["kind"] == "para" for b in s["own"])
            and sum(len(sents[id(b)]) for b in s["own"]) <= 2]
    if len(thin) >= 2 and len(thin) / len(subs) >= 0.5:
        for s in thin:
            cue(s["heading"]["line"], "STR-05", f"one of {len(thin)} sections holding two sentences or fewer")

    # STR-06: sibling sections built the same way.
    level = Counter(s["heading"]["level"] for s in subs).most_common(1)
    peers = [s for s in subs if level and s["heading"]["level"] == level[0][0]]
    if len(peers) >= 4:
        def shape(s):
            return tuple(f"p{min(len(sents[id(b)]), 4)}" if b["kind"] == "para" else
                         f"l{b['items']}" if b["kind"] == "list" else b["kind"][0] for b in s["all"])
        sig, n = Counter(shape(s) for s in peers).most_common(1)[0]
        if len(sig) >= 2 and n / len(peers) >= 0.75:
            match = next(s for s in peers if shape(s) == sig)
            cue(match["heading"]["line"], "STR-06", f"{n} of {len(peers)} sections are built the same way ({' '.join(sig)})")

    # STR-13: every paragraph the same number of sentences.
    if len(paras) >= 5:
        k, n = Counter(len(sents[id(b)]) for b in paras).most_common(1)[0]
        if k >= 2 and n / len(paras) >= 0.8:
            cue(paras[0]["line"], "STR-13", f"{n} of {len(paras)} paragraphs have {k} sentences")

    # STR-16: polite and plain endings mixed in Japanese prose.
    if lang == "ja":
        polite, plain = [], []
        for b in paras:
            for s in sents[id(b)]:
                end = s.rstrip("。！？!?」』）) ")
                (polite if POLITE.search(end) else plain if PLAIN.search(end) else []).append((b, s))
        minority = min(polite, plain, key=len)
        if len(polite) + len(plain) >= 6 and len(minority) >= 2 and len(minority) / (len(polite) + len(plain)) >= 0.15:
            b, s = minority[0]
            cue(line_of(b, s), "STR-16", f"{len(polite)} polite and {len(plain)} plain sentence endings in prose")

    return sorted(out, key=lambda c: (c["line"], c["perspective"]))
