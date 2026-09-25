"""Tests for the PreToolUse guard (.bob/hooks/guard.py), run in CI and by `make check`.

Each case is piped in with both payload shapes ({event, tool, input} and
{hook_event_name, tool_name, tool_input}) and must give the expected exit code. The hooks are
copied into a temporary repo so the audit log never touches this checkout.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import glob
import json
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS = os.path.join(REPO, ".bob", "hooks")
PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIEow" + "IBAAKCAQEA\n-----END " + "RSA PRIVATE KEY-----"


@pytest.fixture(scope="module")
def fake_repo(tmp_path_factory):
    """A temp repo with the real hooks under .bob/hooks and a few protected dirs."""
    root = tmp_path_factory.mktemp("repo")
    shutil.copytree(HOOKS, str(root / ".bob" / "hooks"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    for d in ("harness", "workbook", "service/sheetshift_ho3", "reports"):
        (root / d).mkdir(parents=True, exist_ok=True)
    os.symlink(str(root / "harness"), str(root / "service" / "sneaky"))
    return root


def run_guard(root, tool, tool_input, shape="bob", raw=None):
    """Pipe one payload into guard.py (cwd = repo root); return the exit code."""
    if raw is None:
        if shape == "bob":
            payload = {"event": "PreToolUse", "session_id": "ses_test", "tool": tool,
                       "input": tool_input}
        else:
            payload = {"hook_event_name": "PreToolUse", "session_id": "ses_test",
                       "tool_name": tool, "tool_input": tool_input}
        raw = json.dumps(payload)
    proc = subprocess.run([sys.executable, str(root / ".bob" / "hooks" / "guard.py")],
                          input=raw.encode("utf-8"), cwd=str(root),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    return proc.returncode


def write(path, content="x"):
    return ("write_file", {"path": path, "content": content})


def cmd(command):
    return ("execute_command", {"command": command})


# The core cases first (.bob/rules/30-protected-paths.md), then extra cases.
CASES = [
    ("harness/x.py", write("harness/x.py"), 2),
    ("absolute harness/x.py", None, 2),
    ("workbook\\a.xlsx", write("workbook\\a.xlsx"), 2),
    (".bob/hooks/guard.py", write(".bob/hooks/guard.py"), 2),
    ("private-key body", write("service/sheetshift_ho3/k.py", PRIVATE_KEY), 2),
    ("git push", cmd("git push origin HEAD"), 2),
    ("decide.py", cmd("python3 tools/decide.py D-001 --option adopt-manual"), 2),
    ("harness.run with redirect", cmd("python3 -m harness.run --golden > reports/x.txt"), 0),
    ("service rater.py", write("service/sheetshift_ho3/rater.py"), 0),
    # extras
    ("apply_diff on tools/", ("apply_diff", {"path": "tools/decide.py", "diff": "x"}), 2),
    ("AGENTS.md", ("search_and_replace", {"path": "AGENTS.md", "search": "a", "replace": "b"}), 2),
    ("insert into Makefile", ("insert_content", {"path": "Makefile", "line": 1, "content": "x"}), 2),
    ("symlink into harness", write("service/sneaky/x.py"), 2),
    ("dot-dot into golden", write("service/../golden/x.csv"), 2),
    ("generated report json", write("reports/certificate.json"), 2),
    ("triage note allowed", write("reports/notes/triage_1.md"), 0),
    ("test file allowed", write("tests/test_u2.py"), 0),
    ("BOB_API_KEY", write("service/sheetshift_ho3/api.py", "BOB_API_KEY=abc"), 2),
    ("api key literal", write("service/sheetshift_ho3/api.py", 'api_key = "abcdefghijklmnop1234"'), 2),  # gitleaks:allow
    ("redirect into harness", cmd("echo x > harness/y.py"), 2),
    ("append into decisions", cmd("echo '{}' >> decisions/decisions.jsonl"), 2),
    ("cp into tools", cmd("cp service/a.py tools/a.py"), 2),
    ("cp from build allowed", cmd("cp build/rate_tables.json service/sheetshift_ho3/data/rate_tables.json"), 0),
    ("mv protected away", cmd("mv harness/run.py /tmp/run.py"), 2),
    ("rm -rf .bob", cmd("rm -rf .bob"), 2),
    ("sed -i on workbook dir", cmd("sed -i 's/a/b/' workbook/notes.txt"), 2),
    ("tee AGENTS.md", cmd("echo hi | tee AGENTS.md"), 2),
    ("cd then write", cmd("cd harness && echo x > y.py"), 2),
    ("python -c on golden", cmd("python3 -c \"open('golden/x','w').write('1')\""), 2),
    ("git push via -C", cmd("git -C . push"), 2),
    ("pytest allowed", cmd("pytest -q 2>&1 | tail -5"), 0),
    ("dump_workbook allowed", cmd("python3 tools/dump_workbook.py workbook/example_mutual_ho3_rater.xlsx"), 0),
    ("map module allowed", cmd("python3 -m tools.dump_workbook --expect-lints 3"), 0),
    ("smoke allowed", cmd("python3 -m harness.smoke --unit U2 --n 200"), 0),
    ("dev null allowed", cmd("ls service 2>/dev/null"), 0),
    ("quoted > is not a redirect", cmd("python3 -c \"print(1 > 0)\""), 0),
    ("git status allowed", cmd("git status --short"), 0),
    # Windows shells (PowerShell / cmd): backslash separators and Windows write verbs
    ("win redirect backslash", cmd("echo x > harness\\common.py"), 2),
    ("Copy-Item into harness", cmd("Copy-Item service\\x.py harness\\common.py"), 2),
    ("Set-Content -Path", cmd("Set-Content -Path harness/common.py -Value x"), 2),
    ("Remove-Item", cmd("Remove-Item harness/common.py"), 2),
    ("cmd copy", cmd("copy x.py harness\\common.py"), 2),
    ("cmd del", cmd("del tools\\x.py"), 2),
    ("Copy-Item -Destination first", cmd("Copy-Item -Destination harness/x.py -Path service/y.py"), 2),
    ("Out-File via pipe", cmd("echo x | Out-File harness\\x.py"), 2),
    ("Get-Content allowed", cmd("Get-Content harness\\common.py"), 0),
    ("Copy-Item into service allowed", cmd("Copy-Item build\\rate_tables.json service\\sheetshift_ho3\\data\\rate_tables.json"), 0),
    # case-insensitive file systems
    ("Harness/ upper case", write("Harness/common.py"), 2),
    ("AGENTS.MD upper case", write("AGENTS.MD"), 2),
    # more POSIX write forms
    ("bash -c string", cmd("bash -c 'echo x > harness/y.py'"), 2),
    ("python heredoc shutil", cmd("python3 - <<EOF\nimport shutil; shutil.copy('a', 'harness/b.py')\nEOF"), 2),
    ("find -delete", cmd("find harness -name '*.pyc' -delete"), 2),
    ("xargs rm", cmd("ls harness | xargs rm"), 2),
    ("pushd then write", cmd("pushd tools && touch x.py"), 2),
    ("git -C restore", cmd("git -C harness restore common.py"), 2),
    ("python -m tools.decide", cmd("python3 -m tools.decide D-001 --option adopt-manual"), 2),
    # read-only commands that must stay allowed
    ("cat decisions allowed", cmd("cat decisions/decisions.jsonl"), 0),
    ("grep open( allowed", cmd("grep -n 'open(' harness/common.py"), 0),
    ("python -c then pytest allowed", cmd("python3 -c 'import sys' && python3 -m pytest -q tools/tests/"), 0),
    ("heredoc with apostrophe into tests", cmd("cat > tests/test_x.py <<'EOF'\n# don't read build/ here\nEOF"), 0),
    ("git commit mentioning decisions/", cmd("git commit -m 'read decisions/ only'"), 0),
    # read-only tools pass even on protected paths; unknown edit tools are checked
    ("read_file on harness allowed", ("read_file", {"path": "harness/common.py"}), 0),
    ("unknown edit tool on harness", ("edit_file", {"path": "harness/common.py", "content": "x"}), 2),
    ("unknown edit tool on service", ("edit_file", {"path": "service/sheetshift_ho3/x.py"}), 0),
    ("xml args path", ("apply_diff", {"args": "<file><path>harness/common.py</path><diff>x</diff></file>"}), 2),
    # Bob 2.0 tools, with the parameters the installed Bob IDE declares
    ("office_read on the workbook allowed", ("office_read", {"path": "workbook/probe/stale_cache.xlsx", "mode": "text", "query": ""}), 0),
    ("office_read on the manual allowed", ("office_read", {"path": "manual/example_mutual_ho3_rating_manual.pdf", "mode": "text"}), 0),
    ("grep in harness allowed", ("grep", {"pattern": "def compare", "path": "harness"}), 0),
    ("glob in build allowed", ("glob", {"pattern": "**/*.md", "path": "build"}), 0),
    ("list_files on golden allowed", ("list_files", {"path": "golden", "recursive": False}), 0),
    ("office_edit on the workbook", ("office_edit", {"path": "workbook/example_mutual_ho3_rater.xlsx", "operation": "set", "query": "/Calc/A2", "props": "{}"}), 2),
    ("office_edit on any xlsx", ("office_edit", {"path": "service/sheetshift_ho3/data/x.xlsx", "operation": "set"}), 2),
    ("html artifact quoting reports allowed", ("create_html_artifact", {"id": "run", "title": "Run", "description": "summary", "html": "<p>write reports/certificate.json values; harness/ untouched</p>"}), 0),
    ("chart artifact allowed", ("create_chart", {"type": "bar", "title": "cells", "props": "{}"}), 0),
    ("subagent spawn naming protected dirs allowed", ("spawn_subagent", {"description": "Translate U2. Do not edit harness/, golden/ or .bob/.", "name": "U2"}), 0),
    ("use_skill allowed", ("use_skill", {"skill_name": "translate-sheet"}), 0),
    ("execute_command with cwd into harness", ("execute_command", {"command": "echo x > common.py", "cwd": "harness"}), 2),
]


@pytest.mark.parametrize("shape", ["bob", "alt"])
@pytest.mark.parametrize("name,call,expected", CASES, ids=[c[0] for c in CASES])
def test_guard_table(fake_repo, shape, name, call, expected):
    if call is None:  # absolute path case needs the temp root
        call = write(str(fake_repo / "harness" / "x.py"))
    tool, tool_input = call
    assert run_guard(fake_repo, tool, tool_input, shape) == expected


@pytest.mark.parametrize("raw,expected", [
    ('{"tool": "write_file", "input": {"path": "harness/x.py"', 2),   # truncated JSON
    ("not json at all, service/ok.py", 0),
    ('{"tool": "write_file", "input": {"content": "no path"}}', 0),     # no path, nothing dangerous
    ('{"tool": "write_file", "input": {"content": "see harness/x"}}', 2),
])
def test_fail_closed(fake_repo, raw, expected):
    assert run_guard(fake_repo, None, None, raw=raw) == expected


def test_unbalanced_quotes_fail_closed(fake_repo):
    assert run_guard(fake_repo, *cmd("echo 'oops > harness/x.py")) == 2
    assert run_guard(fake_repo, *cmd("echo 'oops > service/x.py")) == 0


def test_audit_log_is_repo_relative(fake_repo):
    run_guard(fake_repo, *write(str(fake_repo / "service" / "sheetshift_ho3" / "u.py")))
    run_guard(fake_repo, *write("harness/x.py"))
    logs = glob.glob(str(fake_repo / "audit" / "*" / "hook_events.jsonl"))
    assert len(logs) == 1
    text = open(logs[0], encoding="utf-8").read()
    assert str(fake_repo) not in text
    records = [json.loads(l) for l in text.splitlines()]
    keys = {"ts", "handle", "event", "tool", "rel_path", "decision", "reason"}
    assert all(set(r) == keys for r in records)
    assert any(r["rel_path"] == "service/sheetshift_ho3/u.py" and r["decision"] == "allow"
               for r in records)
    assert any(r["rel_path"] == "harness/x.py" and r["decision"] == "block" for r in records)
    assert '"content"' not in text and "MIIEow" not in text


def test_logging_failure_keeps_the_decision(tmp_path):
    """If audit/ cannot be written, a correctly blocked call stays blocked (and an allowed one allowed)."""
    root = tmp_path / "repo"
    shutil.copytree(HOOKS, str(root / ".bob" / "hooks"), ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tests").mkdir()
    (root / "audit").write_text("a file where the audit folder should be")
    assert run_guard(root, *write("tests/test_harness_selfcheck.py")) == 2
    assert run_guard(root, *write("tests/test_u1.py", "reads build/rate_tables.json")) == 0


def test_payload_sample_holds_keys_only(fake_repo):
    run_guard(fake_repo, *write("service/sheetshift_ho3/v.py", "SECRET_VALUE_NOT_LOGGED"))
    sample = glob.glob(str(fake_repo / "audit" / "*" / "hook_payload_sample.json"))
    assert sample
    text = open(sample[0], encoding="utf-8").read()
    assert "SECRET_VALUE_NOT_LOGGED" not in text and "input_keys" in text
    assert "PreToolUse:write_file" in text  # keyed by event and tool
