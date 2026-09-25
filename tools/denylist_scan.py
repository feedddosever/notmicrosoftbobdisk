"""Denylist scan: fails when a tracked file's text or name holds a denylisted token.

usage: python3 tools/denylist_scan.py [--hash TOKEN --scope text|name]

The denylist (.github/denylist.sha256) holds only salted sha256 hashes, one per line as
"<scope> <hex>", so the words themselves never appear in the repository or in CI logs.
Scope "text": single tokens ([a-z0-9_]+) and adjacent word pairs ("a b") of every tracked text
file, lower-cased. Scope "name": the same tokens taken from each tracked path. A hit prints
only the path and line number. --hash prints the line to add for a new token.
Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, ".github", "denylist.sha256")
SALT = "sheetshift-denylist-v1:"
TOKEN = re.compile(r"[a-z0-9_]+")
WORD = re.compile(r"[a-z0-9]+")


def h(token):
    return hashlib.sha256((SALT + token).encode("utf-8")).hexdigest()


def tokens(text):
    """Lower-cased tokens and adjacent word pairs of one line or path."""
    low = text.lower()
    out = set(TOKEN.findall(low)) | set(WORD.findall(low))
    words = WORD.findall(low)
    out |= {"%s %s" % (a, b) for a, b in zip(words, words[1:])}
    return out


def load():
    scopes = {"text": set(), "name": set()}
    with open(LIST, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0] in scopes:
                scopes[parts[0]].add(parts[1])
    return scopes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hash")
    ap.add_argument("--scope", default="text", choices=("text", "name"))
    a = ap.parse_args(argv)
    if a.hash:
        print("%s %s" % (a.scope, h(a.hash.lower())))
        return 0
    deny = load()
    files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, stdout=subprocess.PIPE,
                           check=True).stdout.decode("utf-8", "replace").split("\0")
    hits = 0
    for rel in filter(None, files):
        if any(h(t) in deny["name"] or h(t) in deny["text"] for t in tokens(rel)):
            print("::error::denylisted token found in the path %s" % rel)
            hits += 1
        path = os.path.join(ROOT, rel)
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue  # binary
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if any(h(t) in deny["text"] for t in tokens(line)):
                print("::error::denylisted token found in %s:%d" % (rel, n))
                hits += 1
    print("denylist scan: %d files, %d hits" % (len([f for f in files if f]), hits))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
