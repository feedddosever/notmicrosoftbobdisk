"""PostToolUse hook: log each Bob edit and run the smoke test for the edited unit.

Appends {ts, tool, rel_path} to audit/<handle>/bob_edits.jsonl. For an edit under
service/, infers the unit from the file name (u1_*.py -> U1; otherwise all units) and runs
`python3 -m harness.smoke [--unit U] --n 200`, which writes reports/smoke_last.json.
If smoke cannot run, this hook writes an error record there instead (atomically).
Never blocks (PostToolUse cannot block) and always exits 0.

Standard library only; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

SMOKE_TIMEOUT = 17  # seconds; the hook itself has 20
UNIT_FILE = re.compile(r"(?:^|/)(?:test_)?u([1-4])(?:_[^/]*)?\.py$")


def unit_for(rels):
    """'U2' if every edited service file belongs to unit 2; None means run all units."""
    units = set()
    for rel in rels:
        m = UNIT_FILE.search(rel)
        if not m:
            return None
        units.add("U" + m.group(1))
    return units.pop() if len(units) == 1 else None


def stamp():
    """(mtime, size) of reports/smoke_last.json, to see whether smoke rewrote it."""
    try:
        st = os.stat(C.SMOKE_LAST)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def run_smoke(unit):
    """Run the harness smoke test; record an error if it left no fresh report."""
    cmd = [sys.executable, "-m", "harness.smoke", "--n", "200"] + (["--unit", unit] if unit else [])
    before = stamp()
    reason = None
    try:
        proc = subprocess.run(cmd, cwd=C.ROOT, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=SMOKE_TIMEOUT)
        if stamp() == before:
            reason = "harness.smoke exited %d without writing a report" % proc.returncode
    except subprocess.TimeoutExpired:
        reason = "harness.smoke timed out after %ds" % SMOKE_TIMEOUT
    if reason:
        C.write_json_atomic(C.SMOKE_LAST, {"status": "error", "unit": unit or "all",
                                           "reason": reason})


def main():
    try:
        payload = C.Payload(C.read_stdin(sys.stdin))
        who = C.handle()
        rels = [C.loggable(C.rel_path(p)) for p in C.find_paths(payload.input)]
        for rel in rels:
            C.append_jsonl(C.audit_path("bob_edits.jsonl", who),
                           {"ts": C.now(), "tool": payload.tool, "rel_path": rel})
        C.log_payload_keys(payload, who)
        service = [r for r in rels if r and r.startswith("service/") and r.endswith((".py", ".json"))]
        if service:
            run_smoke(unit_for(service))
    except Exception as e:
        sys.stderr.write("post_edit: %s\n" % type(e).__name__)
    sys.exit(0)


if __name__ == "__main__":
    main()
