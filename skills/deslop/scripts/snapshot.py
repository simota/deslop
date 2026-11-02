#!/usr/bin/env python3
"""Record the documents of a run before anything is rewritten.

    snapshot.py <out> --root <dir> [--copy] [--compare] [--genre [PATH=]GENRE]... PATH...

Copies every document under PATH into <out>/original/ and writes
<out>/snapshot.json (root, working directory, mode, SHA-256 and genre per
file). A file without --genre gets the genre its name implies, else general.
In-place mode rewrites the files under --root; --copy rewrites copies in
<out>/rewritten/ and leaves the originals untouched. Refuses a run directory
that is not empty, one inside --root, and a PATH that does not exist.
"""
import argparse
import sys
import tempfile
from pathlib import Path

from common import assign_genres, iter_docs, load_rules, sha256_bytes, write_json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--root", required=True, help="directory the documents belong to")
    ap.add_argument("--copy", action="store_true", help="rewrite copies under <out>/rewritten/")
    ap.add_argument("--compare", action="store_true", help="require three reviewed candidates per document")
    ap.add_argument("--genre", action="append", metavar="[PATH=]GENRE",
                    help="genre of every document, or of PATH; repeatable (genres are listed in rules.json)")
    a = ap.parse_args(argv)
    try:
        out, root = Path(a.out).resolve(), Path(a.root).resolve()
        if not root.is_dir():
            ap.error(f"--root {root} is not a directory")
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            ap.error(f"{out} is not empty; start a new run directory")
        out_mode = out.stat().st_mode if out.exists() else None
        if out == root or out.is_relative_to(root):
            ap.error(f"run directory {out} is inside --root {root}; put it outside the documents")
        files = sorted({f.resolve() for f in iter_docs(a.paths)})
        if not files:
            ap.error("no document files found")
        for f in files:
            if not f.is_relative_to(root):
                ap.error(f"{f} is outside --root {root}")
            if not f.is_file():
                ap.error(f"{f} is not a document file")
        work = out / "rewritten" if a.copy else root
        genres = assign_genres(a.genre, files, root, load_rules())
        # Publish the complete run in one rename. Read/write failures leave
        # the requested destination absent or empty so the same command can
        # be retried; a competing nonempty destination is never overwritten.
        out.parent.mkdir(parents=True, exist_ok=True)
        # Leave room for tempfile's suffix even when out already uses NAME_MAX.
        with tempfile.TemporaryDirectory(dir=out.parent, prefix=f".{out.name[:32]}.") as tmp:
            staged = Path(tmp) / "run"
            staged.mkdir()
            entries = []
            for f in files:
                rel = f.relative_to(root)
                # Read once so both saved copies and the digest describe
                # exactly the same bytes even if the source changes.
                content = f.read_bytes()
                copies = [staged / "original" / rel]
                if a.copy:
                    copies.append(staged / "rewritten" / rel)
                for dest in copies:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
                entries.append({"path": rel.as_posix(), "sha256": sha256_bytes(content),
                                "genre": genres[rel.as_posix()]})
            write_json(staged / "snapshot.json", {
                "tool": "deslop-snapshot", "root": str(root), "work": str(work),
                "mode": "copy" if a.copy else "in-place", "files": entries,
                **({"workflow": "compare-three"} if a.compare else {}),
            })
            if out_mode is not None:
                staged.chmod(out_mode)
            staged.replace(out)
    except (OSError, RuntimeError, ValueError) as e:
        ap.error(str(e))
    print(f"{len(entries)} files recorded; rewrite under {work}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
