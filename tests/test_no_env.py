"""The deployed code reads no environment variables (README: "The app reads no environment variables").

Fails if os.environ, getenv, environ[...] or `from os import environ` appears in any .py file
under service/ or api/ (comments included, so the rule stays simple and visible).
Passes trivially while service/ does not exist yet.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = re.compile(r"os\.environ|\bgetenv\b|\benviron\s*\[|from\s+os\s+import\s+[^\n]*\benviron\b|\benvironb\b")
SCOPES = ("service", "api")


def python_files():
    for scope in SCOPES:
        top = os.path.join(ROOT, scope)
        for d, dirs, files in os.walk(top):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(d, f)


def test_no_environment_access():
    hits = []
    for path in python_files():
        with open(path, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                if FORBIDDEN.search(line):
                    hits.append("%s:%d: %s" % (os.path.relpath(path, ROOT), n, line.strip()))
    assert not hits, "environment access in deployed code:\n" + "\n".join(hits)


def test_api_entry_point_is_scanned():
    assert os.path.join(ROOT, "api", "index.py") in set(python_files())
