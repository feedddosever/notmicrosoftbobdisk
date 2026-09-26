"""Tests for tools/import_bob_export.py on a small synthetic Bob IDE export (fake user jdoe).

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import check_evidence as E  # noqa: E402
import import_bob_export as I  # noqa: E402

# Assembled at run time: CI's personal-data step rejects any literal non-noreply address in the repo.
FAKE_EMAIL = "jdoe" + "@" + "example.com"
HEADER = ("| Task | Member | Mode | Subagents | Files changed | Commit | Gauge before | Gauge after "
          "| Screenshot | Export | Status |\n|---|---|---|---|---|---|---|---|---|---|---|\n")


def _user(mode, text):
    return {"id": "u", "role": "user", "data": {"content": text, "_meta": {"mode": {"id": mode, "name": mode}}}}


def _call(cid, tool, **args):
    return {"id": "a" + cid, "role": "assistant",
            "data": {"content": "", "toolCalls": [{"id": cid, "name": tool, "arguments": args}]}}


def _result(cid, name, text, error=False):
    return {"id": "r" + cid, "role": "tool",
            "data": {"content": text, "toolUsage": {"signature": {"id": cid, "name": name, "isError": error}}}}


def make_export():
    main = {"task": {"id": "abc123", "parentId": None, "title": "Plan the service", "status": "active",
                     "workspace": "file:c:\\Users\\jdoe\\Desktop\\repo",
                     "env": {"modeId": "plan", "workspace": "c:\\users\\jdoe\\desktop\\repo"},
                     "costs": {"cost": 0.84321, "contextWindowBreakdown": {
                         "key": ("0123456789abcdef" * 2) + "|plan|1344334112|443597102|2169253608"}}},
            "messages": [
                {"id": "s", "role": "system", "data": {"content": "Active file: c:\\Users\\jdoe\\repo\\x.py"}},
                _user("plan", "read file:///c%3A/Users/jdoe/Desktop/repo/a.md, mail " + FAKE_EMAIL),
                _call("1", "write_file", path="docs/design/service_plan.md", content="x"),
                _result("1", "write_file", "ok"),
                _call("2", "apply_diff", path="harness/common.py", diff="d"),
                _result("2", "apply_diff", "SheetShift guard blocked this call: protected path", error=True),
                _user("agent", "go on; commit as 1+m1@users.noreply.github.com"),
                _call("3", "write_file", path="./service/sheetshift_ho3/units/u1.py", content="x"),
                _result("3", "write_file", "ok"),
                _call("4", "write_file", path="service\\sheetshift_ho3\\units\\u2.py", content="x"),
                _result("4", "write_file", "ok"),
                _call("5", "spawn_subagent", description="u3", name="general"),
                _result("5", "spawn_subagent", [{"type": "text", "text": "done"}]),
                _call("6", "read_file", path="C:/Users/jdoe/secret.txt"),
                _result("6", "read_file", "boom", error=True),
            ]}
    child = {"task": {"id": "def456", "parentId": "abc123", "title": "u3", "costs": {"cost": 0.2}},
             "messages": [_call("7", "write_file", path="service/sheetshift_ho3/units/u3.py", content="x"),
                          _result("7", "write_file", "ok")]}
    return {"version": 1, "exportedAt": 1, "workspace": "file:c:\\Users\\jdoe\\Desktop\\repo",
            "tasks": [main, child]}


@pytest.fixture()
def sessions(tmp_path):
    d = tmp_path / "bob_sessions"
    d.mkdir()
    (d / "roster.json").write_text(json.dumps({"team_slug": "teamx", "members": [{"handle": "m1"}]}))
    (d / "INDEX.md").write_text("# Bob task index\n\n" + HEADER, encoding="utf-8")
    raw = tmp_path / "bob-task-abc123-2026-09-26.json"
    raw.write_text(json.dumps(make_export(), indent=2), encoding="utf-8")
    return d, raw


def test_scrub_removes_every_home_path_form_and_keeps_json():
    raw = json.dumps(make_export(), indent=2)
    assert "jdoe" in raw
    text, n_home, n_mail, n_key = I.scrub(raw)
    assert "jdoe" not in text.replace("<home>", "")
    assert n_home >= 5 and n_mail == 1 and n_key == 1
    assert '"key": "<context cache key>"' in text and "|plan|" not in text
    assert not E.HOME_RE.search(text)
    assert "1+m1@users.noreply.github.com" in text          # noreply addresses stay
    assert I.load_export(text)["tasks"][0]["task"]["id"] == "abc123"


def test_summary_counts_modes_cost_subagents_files_and_errors():
    s = I.summarize(make_export())
    assert s["task_id"] == "abc123" and s["title"] == "Plan the service"
    assert s["modes"] == ["plan", "agent"]
    assert s["cost"] == pytest.approx(0.84321) and s["child_costs"] == [0.2]
    assert s["subagents"] == 1
    assert s["files"] == ["docs/design/service_plan.md", "service/sheetshift_ho3/units/u1.py",
                          "service/sheetshift_ho3/units/u2.py", "service/sheetshift_ho3/units/u3.py"]
    assert (s["failed"], s["blocked"]) == (2, 1)
    assert I.files_cell(s["files"], s["blocked"]) == (
        "docs/design/service_plan.md, service/sheetshift_ho3/units/ (3); 1 call blocked by the guard")
    assert I.cost_cell(s) == "task cost 0.84 (+0.20 in 1 subagent task)"


def test_import_writes_scrubbed_export_and_refuses_overwrite(sessions, capsys):
    d, raw = sessions
    assert I.main([str(raw), "--task", "T01", "--desc", "plan"], sessions=str(d)) == 0
    out = d / "teamx_task01_plan_m1_history.json"
    text = out.read_text(encoding="utf-8")
    assert "jdoe" not in text.replace("<home>", "") and json.loads(text)["version"] == 1
    assert E.EXPORT_RE.match(out.name)
    assert "INDEX.md row: | T01 | m1 | plan, agent | 1 |" in capsys.readouterr().out
    assert I.main([str(raw), "--task", "T01", "--desc", "plan"], sessions=str(d)) == 1
    assert I.main([str(raw), "--task", "T01", "--desc", "plan", "--force"], sessions=str(d)) == 0


def test_index_needs_the_screenshot_then_replaces_the_row(sessions):
    d, raw = sessions
    args = [str(raw), "--task", "T01", "--desc", "plan", "--index", "--force"]
    assert I.main(args, sessions=str(d)) == 0
    assert E.parse_index(str(d / "INDEX.md")) == []                  # no PNG yet: row only printed
    (d / "teamx_task01_plan_m1_summary.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    assert I.main(args, sessions=str(d)) == 0
    idx = d / "INDEX.md"
    idx.write_text(idx.read_text(encoding="utf-8").replace("| – | – | task cost", "| abc1234 | 40.0 | task cost"),
                   encoding="utf-8")                                 # a person fills in commit and gauge
    assert I.main(args + ["--status", "re-run"], sessions=str(d)) == 0
    rows = E.parse_index(str(idx))
    assert len(rows) == 1
    r = rows[0]
    assert (r["task"], r["mode"], r["subagents"], r["status"]) == ("T01", "plan, agent", "1", "re-run")
    assert (r["commit"], r["gauge_before"]) == ("abc1234", "40.0")
    assert r["gauge_after"].startswith("task cost 0.84")
    assert r["export"] == "teamx_task01_plan_m1_history.json"
    assert r["screenshot"] == "teamx_task01_plan_m1_summary.png"


def test_rejects_a_file_that_is_not_an_export(sessions, tmp_path):
    d, _ = sessions
    bad = tmp_path / "bob-task-x.json"
    bad.write_text('{"hello": 1}', encoding="utf-8")
    assert I.main([str(bad), "--task", "T01", "--desc", "plan"], sessions=str(d)) == 1
    assert not (d / "teamx_task01_plan_m1_history.json").exists()
