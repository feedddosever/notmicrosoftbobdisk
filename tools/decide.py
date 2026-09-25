"""Record a person's decision on a spreadsheet anomaly (people only; never Bob, never CI).

usage: python3 tools/decide.py D-001 --option adopt-manual --by m1 --rule R-205 \\
           --why "Manual includes $10,000 band; workbook range truncated"

Appends one record to decisions/decisions.jsonl:
  {"id","cell","lint","option","rule","by","at","why","evidence_run","workbook_sha256","service_commit"}
Guard rails:
  * refuses to run unless stdin is an interactive terminal (a tool or agent cannot pipe a yes);
  * the person types the decision id back to confirm;
  * the option must be one the lint allows (keep-workbook is refused for A2 and A3: a quote()
    service has no row identity, so it cannot reproduce a single-row quirk);
  * adopt-manual must cite the lint's manual rule (the rule harness.patch_workbook implements);
  * --by is a handle such as m1 (never an email); an id that is already decided is refused.
The pending items and their allowed options are in reports/decision_queue.json (harness.run).

Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS = os.path.join(ROOT, "decisions", "decisions.jsonl")
LINTS = os.path.join(ROOT, "build", "lints.json")
QUEUE = os.path.join(ROOT, "reports", "decision_queue.json")
LAST_RUN = os.path.join(ROOT, "reports", "last_run.json")
HANDLE = re.compile(r"^[a-z][a-z0-9_-]{0,19}$")
OPTIONS = ("keep-workbook", "adopt-manual", "escalate")


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def lint_for(decision_id):
    """D-00k is the k-th lint of build/lints.json (same mapping as harness/common.py)."""
    m = re.match(r"^D-(\d{3})$", decision_id)
    lints = (_load(LINTS) or {}).get("lints", [])
    if not m or not 1 <= int(m.group(1)) <= len(lints):
        return None
    return lints[int(m.group(1)) - 1]


def existing(decision_id):
    if not os.path.exists(DECISIONS):
        return None
    with open(DECISIONS, encoding="utf-8") as f:
        for line in f:
            if line.strip() and json.loads(line).get("id") == decision_id:
                return json.loads(line)
    return None


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def git_head():
    try:
        out = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def validate(a, lint):
    """Returns an error message, or None when the request is acceptable."""
    if lint is None:
        return "unknown decision id %s (expected D-001..D-%03d)" % (
            a.id, len((_load(LINTS) or {}).get("lints", [])))
    if a.option not in lint.get("options", []):
        return "%s (%s, %s) allows only: %s" % (a.id, lint["id"], lint["type"], ", ".join(lint.get("options", [])))
    if not HANDLE.match(a.by or "") or "@" in (a.by or ""):
        return "--by must be a handle such as m1 (lowercase, no email)"
    if a.option == "adopt-manual" and a.rule != lint.get("manual_rule"):
        return "adopt-manual on %s must cite %s (got %s)" % (lint["id"], lint.get("manual_rule"), a.rule)
    if not a.why or len(a.why.strip()) < 10:
        return "--why needs a reason of at least 10 characters"
    if existing(a.id):
        return "%s is already decided; decisions are append-only (ask the team before superseding)" % a.id
    return None


def record(a, lint):
    last = _load(LAST_RUN) or {}
    cfg = _load(os.path.join(ROOT, "sheetshift.json")) or {}
    wb = os.path.join(ROOT, cfg.get("workbook", "workbook/example_mutual_ho3_rater.xlsx"))
    return {"id": a.id, "cell": lint.get("cells") or lint["cell"], "lint": lint["id"], "option": a.option,
            "rule": a.rule, "by": a.by,
            "at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "why": a.why.strip(), "evidence_run": last.get("run_id"),
            "workbook_sha256": sha256(wb) if os.path.exists(wb) else None,
            "service_commit": git_head()}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Record an anomaly decision (people only)")
    ap.add_argument("id", help="decision id, e.g. D-001 (see reports/decision_queue.json)")
    ap.add_argument("--option", required=True, choices=OPTIONS)
    ap.add_argument("--by", required=True, help="your handle, e.g. m1")
    ap.add_argument("--rule", help="manual rule, e.g. R-205 (required for adopt-manual)")
    ap.add_argument("--why", required=True)
    a = ap.parse_args(argv)
    if not sys.stdin.isatty():
        sys.exit("decide.py: refusing to run without an interactive terminal (people only)")
    lint = lint_for(a.id)
    err = validate(a, lint)
    if err:
        sys.exit("decide.py: " + err)
    rec = record(a, lint)
    print(json.dumps(rec, indent=1))
    typed = input("Type the decision id (%s) to sign this decision: " % a.id).strip()
    if typed != a.id:
        sys.exit("decide.py: confirmation did not match; nothing written")
    os.makedirs(os.path.dirname(DECISIONS), exist_ok=True)
    with open(DECISIONS, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("recorded %s in %s; next: make patch (Claude Code / CI) then make verify" % (
        a.id, os.path.relpath(DECISIONS, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
