"""Hash a directory tree; writes harness/EXPECTED_TREE_SHA256 with --write.

usage: python3 harness/_hash_tree.py [DIR] [--write]

The hash is sha256 over the sorted lines "relative/path<TAB>sha256(file)" for every file
under DIR (default: this harness/ directory), skipping __pycache__/, *.pyc, temp files and
EXPECTED_TREE_SHA256 itself. harness.certify recomputes it and turns the certificate RED if
it differs from the committed EXPECTED_TREE_SHA256. Run --write only after a person has
reviewed a harness change.

Standalone: standard library only, no package imports; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED = os.path.join(HERE, "EXPECTED_TREE_SHA256")
SKIP_NAMES = ("EXPECTED_TREE_SHA256",)
SKIP_DIRS = ("__pycache__", ".pytest_cache")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_files(top, skip=SKIP_NAMES):
    out = []
    for d, dirs, files in os.walk(top):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for f in sorted(files):
            if f in skip or f.endswith((".pyc", ".pyo")) or f.startswith(".tmp_"):
                continue
            out.append(os.path.join(d, f))
    return sorted(out, key=lambda p: os.path.relpath(p, top).replace("\\", "/"))


def tree_sha256(top, skip=SKIP_NAMES):
    """None if `top` is not a directory."""
    if not top or not os.path.isdir(top):
        return None
    lines = ["%s\t%s" % (os.path.relpath(p, top).replace("\\", "/"), file_sha256(p))
             for p in tree_files(top, skip)]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def expected():
    if not os.path.exists(EXPECTED):
        return None
    with open(EXPECTED, encoding="utf-8") as f:
        return f.read().strip() or None


def main(argv):
    args = [a for a in argv if a != "--write"]
    top = os.path.abspath(args[0]) if args else HERE
    h = tree_sha256(top)
    if "--write" in argv:
        if top != HERE:
            sys.exit("--write only applies to the harness directory")
        with open(EXPECTED, "w", encoding="utf-8", newline="\n") as f:
            f.write(h + "\n")
    print(h)


if __name__ == "__main__":
    main(sys.argv[1:])
