"""Tests for tools/check_evidence.py: the home-path scrub check, the naming-rule hints and JSON exports.

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


def test_json_exports_are_accepted_and_parsed(tmp_path, monkeypatch):
    assert E.EXPORT_RE.match("teamalpha_task01_plan_m1_history.json")
    assert E.EXPORT_RE.match("teamalpha_task01_plan_m1_history.md")
    assert not E.EXPORT_RE.match("teamalpha_task01_plan_m1_history.txt")
    assert "_m1_history.json" in E.naming_hint("teamalpha_task01_plan_history.json")
    monkeypatch.setattr(E, "SESSIONS", str(tmp_path))
    (tmp_path / "t_task01_a_m1_history.json").write_text('{"version": 1, "tasks": []}', encoding="utf-8")
    (tmp_path / "t_task02_b_m1_history.json").write_text('{"version": 1,', encoding="utf-8")
    rep = E.Report(final=False)
    E.check_exports(rep, ["t_task01_a_m1_history.json", "t_task02_b_m1_history.json"])
    assert len(rep.errors) == 1 and "t_task02_b_m1_history.json is not valid JSON" in rep.errors[0]
