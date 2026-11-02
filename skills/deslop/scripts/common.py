"""Shared helpers for the deslop scripts. Standard library only."""
import fnmatch
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parent
RULES = SCRIPTS / "rules.json"
DOC_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "vendor"}
OUTPUT_NAMES = (
    "snapshot.json", "findings.json", "detect.before.json", "detect.after.json",
    "preserve.json", "report.md",
)


# Indented code is a Markdown construct; in these an indented line is prose.
PLAIN_SUFFIXES = {".txt", ".rst", ".adoc"}
# A backtick fence's info string has no backtick, so ```js``` opens nothing.
OPEN_FENCE = re.compile(r"[ \t]*(`{3,}(?=[^`]*$)|~{3,})")
LIST_MARKER = re.compile(r"( *(?:[-*+]|\d{1,9}[.)]))(?= |$)( *)")
QUOTE_MARKER = re.compile(r" {0,3}> ?")
HEADING_LINE = re.compile(r" {0,3}#{1,6}(?:[ \t]|$)")
SETEXT_UNDERLINE = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")
THEMATIC_BREAK = re.compile(r" {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
EXPLICIT_HTML_BLOCKS = (
    (re.compile(r" {0,3}<(?:pre|script|style|textarea)(?=[ \t>]|$)", re.I | re.A),
     re.compile(r"</(?:pre|script|style|textarea)>", re.I | re.A)),
    (re.compile(r" {0,3}<!--"), re.compile(r"-->")),
    (re.compile(r" {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r" {0,3}<![A-Za-z]"), re.compile(r">")),
    (re.compile(r" {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
)
HTML_BLOCK_TAG = re.compile(
    r" {0,3}</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|"
    r"details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|"
    r"header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|"
    r"search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?=[ \t>]|/>|$)", re.I | re.A)
HTML_ATTRIBUTES = (
    r"(?:[ \t]+[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t]*=[ \t]*(?:\"[^\"]*\"|'[^']*'|[^ \t\r\n\"'=<>`]+))?)*")
HTML_COMPLETE_TAG = re.compile(
    r" {0,3}(?:</[A-Za-z][A-Za-z0-9-]*[ \t]*>|"
    r"<(?!(?:pre|script|style|textarea)(?=[ \t/>]))[A-Za-z][A-Za-z0-9-]*"
    + HTML_ATTRIBUTES + r"[ \t]*/?>)[ \t]*$", re.I | re.A)
HTML_BLANK_END = re.compile(r"^[ \t]*\r?$")


def _html_closer(line, in_para=False):
    """Return a block's terminator; complete ordinary tags cannot interrupt prose."""
    for opening, closer in EXPLICIT_HTML_BLOCKS:
        if opening.match(line):
            return closer
    # Keep the outer block's blank-line ending even if its body contains
    # a tag such as <pre>, which would otherwise start a different block.
    if HTML_BLOCK_TAG.match(line) or (not in_para and HTML_COMPLETE_TAG.match(line)):
        return HTML_BLANK_END
    return None


def indent(line):
    line = line.expandtabs(4)
    return len(line) - len(line.lstrip(" "))


def is_markdown(path):
    return Path(path).suffix.lower() not in PLAIN_SUFFIXES


def _continue_containers(line, containers):
    """Match existing list/quote prefixes on an expanded line.

    A fence cannot lazily continue outside its containers. Return the
    content offset and the number of containers that still match; do not
    interpret any additional markers inside a code block's body.
    """
    offset = matched = 0
    for kind, width in containers:
        if kind == "quote":
            marker = QUOTE_MARKER.match(line, offset)
            if not marker:
                break
            offset = marker.end()
        elif not line[offset:].strip():
            offset = len(line)
        elif line[offset:offset + width] == " " * width:
            offset += width
        else:
            break
        matched += 1
    return offset, matched


def _list_marker(line, offset, in_para):
    """Paragraph interruptions need content and, for ordered lists, start one."""
    marker = LIST_MARKER.match(line, offset)
    if marker and in_para:
        if not line[marker.end():].strip():
            return None
        token = marker.group(1).lstrip()
        if token[0].isdigit() and int(token[:-1]) != 1:
            return None
    return marker


def _open_containers(line, offset, containers, in_para=False):
    """Consume new list/quote prefixes before ordinary block content."""
    while indent(line[offset:]) < 4:
        quote = QUOTE_MARKER.match(line, offset)
        if quote:
            containers.append(("quote", 0))
            offset = quote.end()
            in_para = False
            continue
        if THEMATIC_BREAK.match(line[offset:]):
            break
        marker = _list_marker(line, offset, in_para)
        if not marker:
            break
        spaces = len(marker.group(2))
        width = len(marker.group(1)) + (spaces if 1 <= spaces <= 4 else 1)
        containers.append(("list" + marker.group(1)[-1], width))
        offset = min(offset + width, len(line))
        in_para = False
    return offset


def code_blocks(text, indented=True):
    """Return (start, end, body_start, body_end) offsets of every code block.
    start..end spans the block without its last newline; the body leaves out
    the fence lines. Fences open and close within three columns of the content
    of the list/quote containers they sit in; an unclosed fence ends with its
    container. With indented, a block four columns past that content counts
    too, unless it would continue a paragraph. Container prefixes are used
    only for parsing; all returned offsets still address the original text.
    HTML block contents do not open Markdown code blocks."""
    lines = text.split("\n")
    flat_lines = [line.expandtabs(4) for line in lines]
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line) + 1)
    blocks, containers, i, in_para, html_end = [], [], 0, False, None
    while i < len(lines):
        flat = flat_lines[i]
        offset, matched = _continue_containers(flat, containers)
        if html_end is not None:
            if matched == len(containers):
                if html_end.search(flat[offset:]):
                    html_end = None
                i, in_para = i + 1, False
                continue
            # Raw HTML cannot continue after its quote or list ends.
            html_end, in_para = None, False
        continued = matched == len(containers)
        remaining = flat[offset:]
        marker = LIST_MARKER.match(remaining) if indent(remaining) < 4 else None
        # A following item in the same list can start at any number. The
        # start-at-one restriction applies only when opening a new list.
        sibling = (matched < len(containers) and marker
                   and containers[matched][0] == "list" + marker.group(1)[-1])
        interrupt = in_para and not sibling
        block_start = indent(remaining) < 4 and (
            any(rx.match(remaining) for rx in (THEMATIC_BREAK, HEADING_LINE, OPEN_FENCE, QUOTE_MARKER))
            or _list_marker(remaining, 0, interrupt)
            or _html_closer(remaining.rstrip("\r"), in_para=interrupt))
        # Ordinary paragraph lines may omit list indentation or quote
        # markers. Keep those containers until a real block boundary;
        # closing them early would turn later list prose into indented code.
        lazy = matched < len(containers) and in_para and remaining.strip() and not block_start
        if not lazy:
            containers = containers[:matched]
            count = len(containers)
            offset = _open_containers(flat, offset, containers, interrupt)
            if len(containers) > count:
                in_para = False
        line = flat[offset:]
        if not line.strip():
            in_para, i = False, i + 1
            continue
        closer = _html_closer(line.rstrip("\r"), in_para=in_para)
        if closer is not None:
            html_end = None if closer.search(line) else closer
            i, in_para = i + 1, False
            continue
        col = indent(line)
        rule, heading = THEMATIC_BREAK.match(line), HEADING_LINE.match(line)
        # A heading can end its paragraph before an indented code block.
        # Lazy underlines outside the container remain paragraph content.
        setext = in_para and continued and SETEXT_UNDERLINE.match(line.rstrip("\r"))
        fence = OPEN_FENCE.match(line) if col < 4 else None
        if fence:
            mark, j, close = fence.group(1), i + 1, None
            while j < len(lines):
                pos, matched = _continue_containers(flat_lines[j], containers)
                if matched != len(containers):
                    break
                s = flat_lines[j][pos:]
                if indent(s) < 4 and s.strip().startswith(mark) and not s.strip().strip(mark[0]):
                    close = j
                    break
                j += 1
            if close is not None:
                last, body_end = close, starts[close]
            elif j == len(lines):
                last, body_end = j - 1, len(text)
            else:
                last = max(k for k in range(i, j) if lines[k].strip())
                body_end = starts[last] + len(lines[last])
            blocks.append((starts[i], starts[last] + len(lines[last]), min(starts[i + 1], body_end), body_end))
        elif indented and not in_para and col >= 4:
            last, j = i, i + 1
            while j < len(lines):
                pos, matched = _continue_containers(flat_lines[j], containers)
                s = flat_lines[j][pos:]
                if matched != len(containers) or (s.strip() and indent(s) < 4):
                    break
                last = j if s.strip() else last
                j += 1
            blocks.append((starts[i], starts[last] + len(lines[last]), starts[i], starts[last] + len(lines[last])))
        else:
            in_para, i = not (rule or heading or setext), i + 1
            continue
        i, in_para = last + 1, False
    return blocks


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def decode_text(data):
    """Decode saved bytes with the same BOM and newline rules as read_text."""
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def read_text(path):
    """UTF-8 text; a leading byte order mark is not part of the document."""
    return decode_text(Path(path).read_bytes())


def load_json(path):
    return json.loads(read_text(path))


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_text(path, text):
    """Replace path atomically so a failed write never leaves half a record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def load_rules(path=RULES):
    return load_json(path)


def markdown_inline(value):
    """Render complete record text on one line without creating Markdown markup."""
    value = " ".join(str(value if value is not None else "").split())
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for char in ("\\", "|", "`", "[", "]", "*", "_", "~", "#"):
        value = value.replace(char, "\\" + char)
    # Some fields are emitted directly after a list marker. Their leading
    # markers must not open a nested list or turn the whole line into a rule.
    if re.match(r"^[-+](?: |$)", value) or re.fullmatch(r"-+", value):
        value = "\\" + value
    return re.sub(r"^([0-9]{1,9})([.)])(?= |$)", r"\1\\\2", value)


def markdown_code(value):
    """Keep identifier whitespace literal, displaying control characters as JSON."""
    value = str(value)
    # Quote literal quotes too, so an actual newline and a filename spelling
    # the displayed JSON string cannot become indistinguishable.
    if '"' in value or any(ord(char) < 32 for char in value):
        value = json.dumps(value, ensure_ascii=False)

    def span(part):
        if not part:
            return ""
        fence = "`" * (1 + max((len(m[0]) for m in re.finditer(r"`+", part)), default=0))
        # Code spans strip one space from each end only when both ends are
        # spaces and the content is not entirely spaces. Add that padding
        # explicitly when either edge is a space or touches a backtick fence.
        needs_pad = part.strip(" ") and (part.startswith(("`", " ")) or part.endswith(("`", " ")))
        pad = " " if needs_pad else ""
        return f"{fence}{pad}{part}{pad}{fence}"

    # Table parsing treats even code-span pipes as separators. Keep escaped
    # pipes outside the spans, preserving any adjacent literal backslashes.
    return r"\|".join(span(part) for part in value.split("|"))


def genre_table(rules):
    return {g["id"]: g for g in rules["genres"]}


def infer_genre(rel, rules):
    """The first genre whose filename pattern matches, else general."""
    name = PurePosixPath(rel).name.lower()
    for g in rules["genres"]:
        if any(fnmatch.fnmatchcase(name, p) for p in g["match"]):
            return g["id"]
    return "general"


def assign_genres(values, files, root, rules):
    """Map each file's root-relative path to a genre id. values are GENRE (the
    default for every file) or PATH=GENRE; files with neither are inferred
    from their name. PATH is relative to the current directory or to root.
    Raises ValueError on an unknown genre or a PATH that names no target or
    different targets relative to the current directory and root."""
    known, default, named = genre_table(rules), None, {}
    for v in values or []:
        path, _, gid = v.rpartition("=")
        if gid not in known:
            raise ValueError(f"unknown genre {gid!r}; use one of {', '.join(known)}")
        if not path and default:
            raise ValueError(f"two default genres: {default} and {gid}")
        if path:
            named[path] = gid
        else:
            default = gid
    rels = {Path(f).resolve(): Path(f).resolve().relative_to(root).as_posix() for f in files}
    out = {rel: default or infer_genre(rel, rules) for rel in rels.values()}
    for path, gid in named.items():
        try:
            hits = {rels.get(Path(path).resolve()), rels.get((root / path).resolve())} - {None}
        except (OSError, RuntimeError, ValueError) as e:
            raise ValueError(f"cannot resolve --genre path {path!r}: {e}") from e
        if not hits:
            raise ValueError(f"--genre names {path}, which is not a target document")
        if len(hits) > 1:
            raise ValueError(f"--genre names {path}, which is ambiguous between "
                             f"{', '.join(sorted(hits))}; use an absolute path")
        out[hits.pop()] = gid
    return out


def _walk_files(root, skip_dirs=()):
    """Walk regular files without swallowing listing or entry-type errors.

    Do not follow directory symlinks encountered below root. An explicitly
    selected root symlink still works, as do symlinks to ordinary files.
    """
    pending = [Path(root)]
    while pending:
        directories = []
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                if entry.is_dir():
                    if entry.name not in skip_dirs and not entry.is_symlink():
                        directories.append(Path(entry.path))
                elif entry.is_file():
                    yield Path(entry.path)
        pending.extend(sorted(directories, reverse=True))


def iter_docs(paths):
    """Return every document file under paths, sorted, skipping tool directories.
    Missing paths and directory read errors fail instead of being skipped."""
    found = []
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            raise FileNotFoundError(f"{raw} does not exist")
        if p.is_file():
            found.append(p)
            continue
        found.extend(f for f in _walk_files(p, SKIP_DIRS) if f.suffix.lower() in DOC_SUFFIXES)
    unique = {}
    for f in found:
        unique.setdefault(f.resolve(), f)
    return sorted(unique.values())


def _resolve_snapshot_path(path, where):
    try:
        return path.resolve()
    except (OSError, RuntimeError, ValueError) as e:
        raise ValueError(f"snapshot.json: cannot resolve {where}: {e}") from e


def _snapshot_root(value, field):
    if not isinstance(value, str) or not value:
        raise ValueError(f"snapshot.json: {field} must be an absolute path")
    path = Path(value)
    if (not path.is_absolute() or str(path) != value
            or _resolve_snapshot_path(path, field) != path):
        raise ValueError(f"snapshot.json: {field} must be a canonical absolute path")
    return path


def load_snapshot(out):
    """Return a validated (snapshot, work_root) for a run directory."""
    out = _resolve_snapshot_path(Path(out), "run directory")
    snap = load_json(out / "snapshot.json")
    if not isinstance(snap, dict) or snap.get("tool") != "deslop-snapshot":
        raise ValueError("snapshot.json must be a deslop-snapshot object")
    if snap.get("mode") not in ("copy", "in-place"):
        raise ValueError("snapshot.json: mode must be copy or in-place")
    if "workflow" in snap and snap["workflow"] != "compare-three":
        raise ValueError("snapshot.json: workflow must be compare-three when present")
    root = _snapshot_root(snap.get("root"), "root")
    work = _snapshot_root(snap.get("work"), "work")
    if out == root or out.is_relative_to(root) or root.is_relative_to(out):
        raise ValueError("snapshot.json: run directory and root must not contain one another")
    expected = out / "rewritten" if snap["mode"] == "copy" else root
    if work != expected:
        raise ValueError(f"snapshot.json: work must be {expected} for {snap['mode']} mode")
    if not isinstance(snap.get("files"), list) or not snap["files"]:
        raise ValueError("snapshot.json: files must be a non-empty list")
    known_genres = genre_table(load_rules())
    seen = set()
    for i, entry in enumerate(snap["files"]):
        where = f"files[{i}]"
        if not isinstance(entry, dict):
            raise ValueError(f"snapshot.json: {where} must be an object")
        value = entry.get("path")
        if not isinstance(value, str) or not value:
            raise ValueError(f"snapshot.json: {where}.path must be a relative path")
        relative = Path(value)
        if (not relative.parts or relative.is_absolute() or ".." in relative.parts
                or relative.as_posix() != value):
            raise ValueError(f"snapshot.json: {where}.path must be a canonical relative path")
        if value in seen:
            raise ValueError(f"snapshot.json: duplicate path {value!r}")
        seen.add(value)
        genre = entry.get("genre", "general")
        if not isinstance(genre, str) or genre not in known_genres:
            raise ValueError(f"snapshot.json gives {value} the unknown genre {genre!r}")
        digest = entry.get("sha256")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError(f"snapshot.json: {where}.sha256 must be a SHA-256 digest")
        for base in (out / "original", work):
            if not _resolve_snapshot_path(base / relative, f"{base / relative}").is_relative_to(base):
                raise ValueError(f"snapshot.json: {value!r} resolves outside {base}")
    original = out / "original"
    stored = {path.relative_to(original).as_posix() for path in _walk_files(original)}
    unrecorded = stored - seen
    if unrecorded:
        raise ValueError(f"snapshot.json: original/{min(unrecorded)} is not recorded")
    return snap, work
