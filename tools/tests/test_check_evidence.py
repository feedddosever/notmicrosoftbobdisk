"""Tests for tools/check_evidence.py: the home-path scrub check and the naming-rule hints.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import check_evidence as E  # noqa: E402


@pytest.mark.parametrize("text,flagged", [
    ("Opened c:\\Users\\jdoe\\repo", True),        # lower-case drive letter (VS Code fsPath)
    ("\"C:\\\\Users\\\\jdoe\\\\repo\"", True),     # JSON-escaped
    ("d:\\Users\\jdoe", True),                     # another drive
    ("C:/Users/jdoe/x", True),
    ("/Users/jdoe/x", True),
    ("/home/jdoe/x", True),
    ("/home/<home>/x", False),                     # already scrubbed
    ("C:\\Users\\<home>\\x", False),
    ("<home>\\repo\\x", False),
    ("no paths here", False),
])
def test_home_re(text, flagged):
    assert bool(E.HOME_RE.search(text)) is flagged


def test_naming_hints():
    assert "_m1_summary.png" in E.naming_hint("teamalpha_task01_login_flow_summary.png")
    assert "lower case" in E.naming_hint("Teamalpha_task01_login_flow_m1_summary.png")
    assert E.SCREENSHOT_RE.match("teamalpha_task01_login_flow_m1_summary.png")
    assert "teamalpha_task01_login_flow_m1_summary.png" in E.NAMING_HELP
