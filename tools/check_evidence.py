"""Check the Bob evidence folder, commit trailers, audit logs and attribution (hackathon rules: Bob task evidence, attribution).

usage: python3 tools/check_evidence.py [--final] [--json] [--no-blame]

Always errors (exit 1):
- bob_sessions/ is not flat, or holds a file that is not README.md, INDEX.md, roster.json,
  a task screenshot   <team>_taskNN_<desc>_<handle>_summary.png
  a task export       <team>_taskNN_<desc>_<handle>_history.json (Bob IDE's Export, imported
                      with tools/import_bob_export.py) or _history.md
  or a misc screenshot <team>_misc_<desc>_<handle>.png (e.g. the Bobalytics view)
- a file name uses another team slug than roster.json, or a handle not in the roster;
- an INDEX.md row names a missing or badly named screenshot/export, or two rows share one;
- a screenshot is not named by any INDEX row (exactly one PNG per row);
- an export still contains a home path or a non-noreply email address, or a .json export does
  not parse;
- a commit has a malformed `Bob-Task:` trailer, or an INDEX row's commit does not carry the
  matching `Bob-Task: TNN (mN)` trailer.
With --final (the Sun 09:00 gate) these become errors too (otherwise warnings):
- a roster handle without a screenshot; INDEX empty;
- exports_available is true in roster.json but a row has no export; exports_available unset;
- a Bob-Task commit whose task is missing from INDEX.md; a handle with Bob-Task commits but no
  audit/<handle>/bob_edits.jsonl;
- a tracked service/ file that no Bob-Task commit touched, or that ATTRIBUTION.md does not list.

Also reports "Bob-authored lines: Lb of Lt non-generated lines" from git blame (lines whose
commit carries a Bob-Task trailer), which the README quotes.

Standard library only; Python 3.8+. The INDEX.md parser is reused by tools/build_site_data.py.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS = os.path.join(ROOT, "bob_sessions")

SCREENSHOT_RE = re.compile(r"^[a-z0-9]+_task\d{2}_[a-z0-9_]+_m[1-4]_summary\.png$")
EXPORT_RE = re.compile(r"^[a-z0-9]+_task\d{2}_[a-z0-9_]+_m[1-4]_history\.(md|json)$")
MISC_RE = re.compile(r"^[a-z0-9]+_misc_[a-z0-9_]+_m[1-4]\.png$")
NAME_PARTS = re.compile(r"^(?P<team>[a-z0-9]+)_task(?P<nn>\d{2})_(?P<desc>[a-z0-9_]+)_(?P<handle>m[1-4])_(summary\.png|history\.md|history\.json)$")
FIXED_FILES = {"README.md", "INDEX.md", "roster.json", ".gitkeep"}

TRAILER_RE = re.compile(r"^Bob-Task:\s*(.*)$", re.M)
TRAILER_OK = re.compile(r"^T(\d{2}) \((m[1-4])\)$")
# /Users/x, /home/x and Windows drive paths (any letter, either case, single or JSON-escaped
# backslashes or forward slashes), unless already scrubbed to <home>.
HOME_RE = re.compile(r"(?i)(/Users/|/home/|\b[a-z]:(\\{1,2}|/)Users(\\{1,2}|/))(?!<home>)[^\\/\s]+")
NAMING_HELP = ("expected <team>_taskNN_<desc>_<mN>_summary.png (or _history.json / _history.md), e.g. "
               "teamalpha_task01_login_flow_m1_summary.png: lowercase, two-digit task, handle before _summary")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"(@users\.noreply\.github\.com|^noreply@anthropic\.com|^noreply@github\.com)$", re.I)

# Not counted in the Bob-authored line ratio: generated data, binaries, logs and evidence.
GENERATED_PREFIXES = ("build/", "golden/", "reports/", "public/data/", "workbook/", "audit/",
                      "bob_sessions/", "decisions/", "service/sheetshift_ho3/data/")
BINARY_EXT = (".png", ".jpg", ".pdf", ".xlsx", ".gz", ".mp4", ".ico", ".xcu")

INDEX_COLUMNS = ["Task", "Member", "Mode", "Subagents", "Files changed", "Commit", "Gauge before",
                 "Gauge after", "Screenshot", "Export", "Status"]


# ---------------------------------------------------------------- INDEX.md
def _key(name):
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _cell(text):
    """Markdown cell -> plain text: link target or text, backticks and spaces stripped."""
    t = text.strip()
    m = re.match(r"^\[([^\]]*)\]\(([^)]*)\)$", t)
    if m:
        t = m.group(2) or m.group(1)
    t = t.strip("` ")
    return "" if t in ("-", "–", "—") else t


def parse_index(path=None):
    """Rows of bob_sessions/INDEX.md as dicts keyed by snake_case header names."""
    path = path or os.path.join(SESSIONS, "INDEX.md")
    if not os.path.exists(path):
        return []
    header, rows = None, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c for c in line.strip("|").split("|")]
            if header is None:
                header = [_key(c) for c in cells]
                continue
            if all(re.match(r"^\s*:?-{2,}:?\s*$", c) for c in cells):
                continue
            vals = [_cell(c) for c in cells] + [""] * len(header)
            row = dict(zip(header, vals))
            if any(row.values()):
                rows.append(row)
    return rows


def roster():
    path = os.path.join(SESSIONS, "roster.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- git
def git(*args):
    """stdout of a git command in the repo, or None when git or the history is unavailable."""
    try:
        out = subprocess.run(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def bob_commits():
    """{sha: {"task": "T03", "handle": "m1", "raw": trailer}} plus a list of malformed trailers."""
    log = git("log", "--all", "--format=%H%x00%B%x1e")
    good, bad = {}, []
    for rec in (log or "").split("\x1e"):
        if "\x00" not in rec:
            continue
        sha, body = rec.strip("\n").split("\x00", 1)
        for raw in TRAILER_RE.findall(body):
            m = TRAILER_OK.match(raw.strip())
            if m:
                good[sha] = {"task": "T" + m.group(1), "handle": m.group(2), "raw": raw.strip()}
            else:
                bad.append((sha[:10], raw.strip()))
    return good, bad


def tracked_files():
    out = git("ls-files")
    return [p for p in (out or "").splitlines() if p]


def files_touched(sha):
    out = git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha)
    return [p for p in (out or "").splitlines() if p]


def bob_line_ratio(bob_shas):
    """(bob_lines, total_lines) over tracked, non-generated text files, via git blame."""
    bob, total = 0, 0
    sha_line = re.compile(r"^([0-9a-f]{40}) \d+ \d+")
    for path in tracked_files():
        if path.startswith(GENERATED_PREFIXES) or path.lower().endswith(BINARY_EXT):
            continue
        out = git("blame", "--line-porcelain", "--", path)
        if out is None:
            continue
        for line in out.splitlines():
            m = sha_line.match(line)
            if m:
                total += 1
                bob += m.group(1) in bob_shas
    return bob, total


# ---------------------------------------------------------------- checks
class Report(object):
    def __init__(self, final):
        self.final, self.errors, self.warnings, self.info = final, [], [], {}

    def error(self, msg):
        self.errors.append(msg)

    def gate(self, msg):
        """Incomplete evidence: an error with --final, a warning otherwise."""
        (self.errors if self.final else self.warnings).append(msg)


def check_folder(rep, team, handles):
    if not os.path.isdir(SESSIONS):
        rep.error("bob_sessions/ is missing")
        return [], []
    shots, exports = [], []
    for name in sorted(os.listdir(SESSIONS)):
        path = os.path.join(SESSIONS, name)
        if os.path.isdir(path):
            rep.error("bob_sessions/ must be flat; found folder %s/" % name)
            continue
        if name in FIXED_FILES:
            continue
        if SCREENSHOT_RE.match(name):
            shots.append(name)
        elif EXPORT_RE.match(name):
            exports.append(name)
        elif MISC_RE.match(name):
            pass
        else:
            rep.error("bob_sessions/%s does not match the naming rule; %s%s" % (name, NAMING_HELP, naming_hint(name)))
            continue
        prefix = name.split("_", 1)[0]
        handle = re.search(r"_(m[1-4])(?:_summary\.png|_history\.md|_history\.json|\.png)$", name).group(1)
        if team and prefix != team:
            rep.error("bob_sessions/%s uses team slug %r, roster says %r" % (name, prefix, team))
        if handles and handle not in handles:
            rep.error("bob_sessions/%s names handle %s, which is not in roster.json" % (name, handle))
    return shots, exports


def naming_hint(name):
    """A suggested fix for a name that almost matches the rule, or ''."""
    low = name.lower()
    if low != name and (SCREENSHOT_RE.match(low) or EXPORT_RE.match(low) or MISC_RE.match(low)):
        return " (hint: use lower case: %s)" % low
    m = re.match(r"^([a-z0-9]+_task\d{2}_[a-z0-9_]+?)_(summary\.png|history\.md|history\.json)$", low)
    if m and not re.search(r"_m[1-4]$", m.group(1)):
        return " (hint: add your handle: %s_m1_%s)" % (m.group(1), m.group(2))
    return ""


def check_exports(rep, exports):
    for name in exports:
        with open(os.path.join(SESSIONS, name), encoding="utf-8", errors="replace") as f:
            text = f.read()
        if name.endswith(".json"):
            try:
                json.loads(text)
            except ValueError:
                rep.error("bob_sessions/%s is not valid JSON; re-import it with tools/import_bob_export.py" % name)
        if HOME_RE.search(text):
            rep.error("bob_sessions/%s contains a home path; scrub it (see bob_sessions/README.md)" % name)
        bad = sorted({e for e in EMAIL_RE.findall(text) if not EMAIL_OK.search(e)})
        if bad:
            rep.error("bob_sessions/%s contains %d email address(es); scrub them" % (name, len(bad)))


def check_index(rep, rows, shots, exports, exports_available, commits):
    seen_shots, seen_exports = {}, {}
    for i, r in enumerate(rows, 1):
        where = "INDEX.md row %d (%s)" % (i, r.get("task") or "?")
        task = (r.get("task") or "").upper()
        member = r.get("member") or ""
        if not re.match(r"^T\d{2}$", task):
            rep.error("%s: Task must look like T03" % where)
        if not re.match(r"^m[1-4]$", member):
            rep.error("%s: Member must be a handle m1..m4" % where)
        shot = os.path.basename(r.get("screenshot") or "")
        if not shot:
            rep.error("%s: no screenshot" % where)
        elif shot not in shots:
            rep.error("%s: screenshot %s is missing or badly named" % (where, shot))
        else:
            m = NAME_PARTS.match(shot)
            if m and ("T" + m.group("nn") != task or m.group("handle") != member):
                rep.error("%s: screenshot %s does not match task %s / member %s" % (where, shot, task, member))
            if shot in seen_shots:
                rep.error("%s: screenshot %s is also used by row %d" % (where, shot, seen_shots[shot]))
            seen_shots[shot] = i
        exp = os.path.basename(r.get("export") or "")
        if exp:
            if exp not in exports:
                rep.error("%s: export %s is missing or badly named" % (where, exp))
            elif exp in seen_exports:
                rep.error("%s: export %s is also used by row %d" % (where, exp, seen_exports[exp]))
            seen_exports[exp] = i
        elif exports_available:
            rep.gate("%s: exports are available but this row has no export" % where)
        sha = (r.get("commit") or "").strip()
        if sha and commits is not None:
            full = [s for s in commits if s.startswith(sha)]
            if not full:
                rep.error("%s: commit %s has no Bob-Task trailer (or is not in the history)" % (where, sha))
            elif commits[full[0]]["task"] != task or commits[full[0]]["handle"] != member:
                rep.error("%s: commit %s is trailed %r" % (where, sha, commits[full[0]]["raw"]))
    for s in shots:
        if s not in seen_shots:
            rep.error("bob_sessions/%s is not named by any INDEX.md row (one PNG per row)" % s)
    for e in exports:
        if e not in seen_exports:
            rep.gate("bob_sessions/%s is not named by any INDEX.md row" % e)


def check_history(rep, rows, commits, attribution_text):
    tasks_in_index = {(r.get("task") or "").upper() for r in rows}
    handles = {}
    for sha, c in sorted(commits.items()):
        handles.setdefault(c["handle"], 0)
        handles[c["handle"]] += 1
        if c["task"] not in tasks_in_index:
            rep.gate("commit %s (Bob-Task %s) has no INDEX.md row" % (sha[:10], c["raw"]))
    for h in sorted(handles):
        if not os.path.exists(os.path.join(ROOT, "audit", h, "bob_edits.jsonl")):
            rep.gate("%s has %d Bob-Task commit(s) but no audit/%s/bob_edits.jsonl" % (h, handles[h], h))
    touched = set()
    for sha in commits:
        touched.update(files_touched(sha))
    for path in tracked_files():
        if not path.startswith("service/") or path.endswith(".gitkeep"):
            continue
        generated = path.startswith("service/sheetshift_ho3/data/verify_sample_")
        if not generated and path not in touched:
            rep.gate("%s is not touched by any Bob-Task commit" % path)
        if path not in attribution_text:
            rep.gate("%s is not listed in ATTRIBUTION.md" % path)


def run(final=False, blame=True):
    rep = Report(final)
    ros = roster()
    team = ros.get("team_slug") or None
    handles = [m.get("handle") for m in ros.get("members", []) if isinstance(m, dict) and m.get("handle")]
    exports_available = ros.get("exports_available")
    if not ros:
        rep.error("bob_sessions/roster.json is missing")
    if not team:
        rep.gate("roster.json team_slug is not set (the registered team name as a lowercase slug)")
    if exports_available is None:
        rep.gate("roster.json exports_available is not set (record the T00 finding)")

    shots, exports = check_folder(rep, team, handles)
    check_exports(rep, exports)
    rows = parse_index()
    if not rows:
        rep.gate("bob_sessions/INDEX.md has no task rows yet")
    has_history = git("rev-parse", "--verify", "-q", "HEAD") is not None
    commits, bad = bob_commits() if has_history else ({}, [])
    for sha, raw in bad:
        rep.error("commit %s has a malformed trailer 'Bob-Task: %s' (want 'Bob-Task: T03 (m1)')" % (sha, raw))
    check_index(rep, rows, shots, exports, exports_available, commits if has_history else None)
    for h in handles:
        if not any(re.search(r"_%s_summary\.png$" % h, s) for s in shots):
            rep.gate("roster handle %s has no task screenshot yet" % h)
    attribution = ""
    if os.path.exists(os.path.join(ROOT, "ATTRIBUTION.md")):
        with open(os.path.join(ROOT, "ATTRIBUTION.md"), encoding="utf-8") as f:
            attribution = f.read()
    if has_history:
        check_history(rep, rows, commits, attribution)

    rep.info = {"index_rows": len(rows), "screenshots": len(shots), "exports": len(exports),
                "bob_task_commits": len(commits), "handles": handles, "team_slug": team}
    if blame and has_history:
        lb, lt = bob_line_ratio(set(commits))
        rep.info["bob_authored_lines"] = lb
        rep.info["non_generated_lines"] = lt
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check Bob evidence, trailers and attribution")
    ap.add_argument("--final", action="store_true", help="treat incomplete evidence as errors")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--no-blame", action="store_true", help="skip the git blame line count")
    a = ap.parse_args(argv)
    rep = run(final=a.final, blame=not a.no_blame)
    if a.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, "info": rep.info},
                         indent=1, sort_keys=True))
    else:
        for w in rep.warnings:
            print("warning: " + w)
        for e in rep.errors:
            print("ERROR: " + e)
        i = rep.info
        print("evidence: %d INDEX rows, %d screenshots, %d exports, %d Bob-Task commits" % (
            i["index_rows"], i["screenshots"], i["exports"], i["bob_task_commits"]))
        if "bob_authored_lines" in i:
            print("Bob-authored lines: %d of %d non-generated lines" % (i["bob_authored_lines"], i["non_generated_lines"]))
        print("check_evidence: %s" % ("FAIL" if rep.errors else "ok"))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
