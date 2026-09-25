"""Separation of duties in git history: Bob's commits never touch the grader (plan section 6.8).

usage: python3 tools/check_protected.py [--range BASE..HEAD] [--no-hash]

1. Every commit whose message carries a `Bob-Task:` trailer is checked: it fails if it adds,
   changes, deletes or renames any path under PROTECTED (the workbook, manual, harness, golden
   data, decisions, tools, the Bob pack, CI, AGENTS.md, sheetshift.json). Default range: the
   whole history reachable from HEAD.
2. The harness tree hash (harness/_hash_tree.py) must equal harness/EXPECTED_TREE_SHA256
   (skip with --no-hash). A person updates that file after reviewing a harness change.

Merge commits are checked like any other commit (against their first parent).
Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTECTED = ("workbook/", "manual/", "harness/", "golden/", "decisions/", "tools/", ".bob/",
             ".github/", "AGENTS.md", "sheetshift.json")
TRAILER = re.compile(r"^Bob-Task:", re.M)


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), out.stderr.decode("utf-8", "replace").strip()))
    return out.stdout.decode("utf-8", "replace")


def is_protected(path):
    return any(path == p.rstrip("/") or path.startswith(p) for p in PROTECTED)


def bob_commits(rev_range):
    """[(sha, subject)] for commits in the range whose message has a Bob-Task trailer."""
    log = git("log", "--format=%H%x00%s%x00%B%x1e", rev_range)
    out = []
    for rec in log.split("\x1e"):
        parts = rec.strip("\n").split("\x00")
        if len(parts) >= 3 and TRAILER.search(parts[2]):
            out.append((parts[0], parts[1]))
    return out


def touched(sha):
    """Every path a commit adds, changes, deletes or renames (both sides of a rename)."""
    raw = git("diff-tree", "--no-commit-id", "-r", "--root", "-M", "--name-status", "-m", "--first-parent", sha)
    paths = set()
    for line in raw.splitlines():
        cols = line.split("\t")
        paths.update(c for c in cols[1:] if c)
    return sorted(paths)


def check_history(rev_range):
    problems = []
    commits = bob_commits(rev_range)
    for sha, subject in commits:
        bad = [p for p in touched(sha) if is_protected(p)]
        if bad:
            problems.append("%s %r (Bob-Task) touches protected paths: %s" % (sha[:10], subject[:60], ", ".join(bad)))
    return commits, problems


def check_harness_hash():
    sys.path.insert(0, os.path.join(ROOT, "harness"))
    import _hash_tree  # standalone module, stdlib only
    actual, expected = _hash_tree.tree_sha256(_hash_tree.HERE), _hash_tree.expected()
    if expected is None:
        return ["harness/EXPECTED_TREE_SHA256 is missing or empty"]
    if actual != expected:
        return ["harness tree hash %s differs from harness/EXPECTED_TREE_SHA256 %s" % (actual[:12], expected[:12])]
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bob-Task commits must not touch protected paths")
    ap.add_argument("--range", default="HEAD", help="git revision range (default: all of HEAD's history)")
    ap.add_argument("--no-hash", action="store_true", help="skip the harness tree hash check")
    a = ap.parse_args(argv)
    try:
        git("rev-parse", "--verify", "-q", "HEAD")
        commits, problems = check_history(a.range)
    except RuntimeError as e:
        print("check_protected: no git history to check (%s)" % e)
        commits, problems = [], []
    if not a.no_hash:
        problems += check_harness_hash()
    for p in problems:
        print("ERROR: " + p)
    print("check_protected: %d Bob-Task commit(s) checked; %s" % (len(commits), "FAIL" if problems else "ok"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
