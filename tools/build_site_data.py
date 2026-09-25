"""Build public/data/*.json, the only data the static pages read.

usage: python -m tools.build_site_data [--out public/data] [--reports reports] [--static]
                                       [--service MODULE] [--sample PATH] [--repo-url URL]
       python -m tools.build_site_data --readme   # also rewrite the README headline block

Copies or derives, never invents:
  certificate.json         reports/certificate.json (byte copy)
  certificate_report.html  reports/certificate.html (byte copy, written by harness.certify)
  traceability.json        reports/traceability.json (byte copy)
  mutation.json            reports/mutation_report.json (byte copy)
  spotcheck.json           reports/spotcheck.json (byte copy)
  graph.json, lints.json   build/graph.json, build/lints.json (byte copies)
  baseline.json            reports/baseline.json, if a person recorded the hand-translation timing
  decisions.json           {queue: reports/decision_queue.json items, log: decisions/decisions.jsonl}
  replay.json              timeline from audit/<handle>/*.jsonl, reports/run_log.jsonl,
                           bob_sessions/INDEX.md, decisions and Bob-Task commits
  quote_examples.json      a few golden policies with their recorded workbook values
  verify_sample_results.json  the service run over the whole verification sample (static
                           fallback for /verify); only when the service imports
  site.json                commit, repo URL, mode, recorded dates, exports_available (from
                           bob_sessions/roster.json), source hashes, missing files
A missing source is listed in site.json "missing" and the page says "not generated yet".
--readme rewrites the block between the headline markers in README.md from the certificate;
it refuses a certificate produced by a stand-in service (only Bob's service goes in the README).
Output is deterministic (sorted keys, no build timestamp), so rebuilding changes nothing.

Standard library only (plus the harness package for golden data); Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import check_evidence as EV  # noqa: E402

DEFAULT_SERVICE = "service.sheetshift_ho3.rater"
CARRIER = "Example Mutual Insurance Co. (FICTIONAL)"
MAX_MISMATCHES = 200
MAX_EVENTS = 2000

COPIES = [  # (output name, source relative to repo or reports dir, from_reports)
    ("certificate.json", "certificate.json", True),
    ("certificate_report.html", "certificate.html", True),
    ("traceability.json", "traceability.json", True),
    ("mutation.json", "mutation_report.json", True),
    ("spotcheck.json", "spotcheck.json", True),
    ("baseline.json", "baseline.json", True),
    ("graph.json", "build/graph.json", False),
    ("lints.json", "build/lints.json", False),
]
OPTIONAL = {"baseline.json"}


# ---------------------------------------------------------------- small helpers
def rel(path):
    """Repo-relative path; paths outside the repo are reduced to their name (no absolute paths)."""
    r = os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")
    return "<outside-repo>/" + os.path.basename(path) if r.startswith("..") else r


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dumps(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(obj))


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                out.append(rec)
    return out


def git(*args):
    try:
        out = subprocess.run(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.decode("utf-8", "replace").strip() if out.returncode == 0 else None


def repo_url(explicit=None):
    """https://github.com/<owner>/<repo> from --repo-url or the origin remote; credentials never kept."""
    raw = explicit or git("remote", "get-url", "origin") or ""
    m = re.match(r"^(?:https?://(?:[^@/]+@)?github\.com/|git@github\.com:)([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", raw.strip())
    return "https://github.com/%s/%s" % (m.group(1), m.group(2)) if m else None


def utc(ts):
    """Normalise an ISO timestamp to YYYY-MM-DDTHH:MM:SSZ (UTC); None if unreadable."""
    import datetime as dt
    if not ts or not isinstance(ts, str):
        return None
    t = ts.strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(t)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- replay timeline
def bob_commit_events():
    """Events for commits carrying a Bob-Task trailer, with their UTC commit time."""
    log = git("log", "--all", "--format=%H%x00%cI%x00%s%x00%B%x1e")
    events = []
    for rec in (log or "").split("\x1e"):
        parts = rec.strip("\n").split("\x00")
        if len(parts) < 4:
            continue
        sha, when, subject, body = parts[0], parts[1], parts[2], parts[3]
        m = re.search(r"^Bob-Task:\s*T(\d{2}) \((m[1-4])\)\s*$", body, re.M)
        if m:
            events.append({"ts": utc(when), "kind": "commit", "task": "T" + m.group(1),
                           "handle": m.group(2), "commit": sha, "title": subject[:200]})
    return events


def audit_events():
    """Edits and guard blocks from audit/<handle>/*.jsonl (repo-relative paths only)."""
    events, counts = [], {"edits": 0, "guard_allow": 0, "guard_block": 0}
    top = os.path.join(ROOT, "audit")
    if not os.path.isdir(top):
        return events, counts
    for handle in sorted(os.listdir(top)):
        if not re.match(r"^[A-Za-z0-9_-]{1,32}$", handle):
            continue
        last = None
        for r in read_jsonl(os.path.join(top, handle, "bob_edits.jsonl")):
            counts["edits"] += 1
            path, ts = r.get("rel_path"), utc(r.get("ts"))
            key = (path, (ts or "")[:16])
            if key == last:  # collapse repeated edits of one file within a minute
                continue
            last = key
            events.append({"ts": ts, "kind": "edit", "handle": handle, "path": path if path and not str(path).startswith("<") else None,
                           "title": "Bob edited %s" % (path or "a file"), "detail": r.get("tool")})
        for r in read_jsonl(os.path.join(top, handle, "hook_events.jsonl")):
            if r.get("decision") == "block":
                counts["guard_block"] += 1
                events.append({"ts": utc(r.get("ts")), "kind": "guard_block", "handle": handle,
                               "title": "Guard blocked %s on %s" % (r.get("tool") or "a tool call", r.get("rel_path") or "a protected path"),
                               "detail": r.get("reason")})
            else:
                counts["guard_allow"] += 1
    return events, counts


def run_log_events():
    events = []
    for r in read_jsonl(os.path.join(ROOT, "reports", "run_log.jsonl")):
        events.append({"ts": utc(r.get("ts")), "kind": "smoke", "handle": r.get("handle"),
                       "title": "Task turn ended", "detail": str(r.get("smoke") or "")[:200]})
    return events


def decision_events(log):
    return [{"ts": utc(d.get("at")), "kind": "decision", "handle": d.get("by"),
             "title": "%s: %s (%s) on %s" % (d.get("id"), d.get("option"), d.get("rule"), d.get("cell")),
             "detail": (d.get("why") or "")[:300]} for d in log]


def task_rows():
    rows = []
    for r in EV.parse_index():
        shot, exp = r.get("screenshot"), r.get("export")
        rows.append({
            "task": (r.get("task") or "").upper(), "member": r.get("member"), "mode": r.get("mode"),
            "subagents": r.get("subagents"), "files_changed": r.get("files_changed"),
            "commit": r.get("commit") or None, "gauge_before": r.get("gauge_before"),
            "gauge_after": r.get("gauge_after"), "status": r.get("status"),
            "screenshot": ("bob_sessions/" + os.path.basename(shot)) if shot else None,
            "export": ("bob_sessions/" + os.path.basename(exp)) if exp else None})
    return rows


def build_replay(log):
    tasks = task_rows()
    commits = bob_commit_events()
    by_sha = {e["commit"]: e for e in commits}
    for t in tasks:  # attach the INDEX row's evidence to its commit event
        full = [s for s in by_sha if t["commit"] and s.startswith(t["commit"])]
        if full:
            ev = by_sha[full[0]]
            ev.update({"kind": "task", "screenshot": t["screenshot"], "export": t["export"],
                       "detail": "mode %s; subagents %s; gauge %s -> %s; %s" % (
                           t["mode"] or "?", t["subagents"] or "0", t["gauge_before"] or "?",
                           t["gauge_after"] or "?", t["status"] or "done")})
    edits, counts = audit_events()
    runs = run_log_events()
    events = commits + edits + runs + decision_events(log)
    events = [e for e in events if e.get("ts")]
    events.sort(key=lambda e: (e["ts"], e["kind"], e.get("handle") or "", e.get("title") or ""))
    truncated = max(0, len(events) - MAX_EVENTS)
    events = events[:MAX_EVENTS]
    for e in events:
        for k in [k for k, v in e.items() if v in (None, "")]:
            del e[k]
    bob_days = sorted({e["ts"][:10] for e in events if e["kind"] in ("commit", "task", "edit", "smoke", "guard_block")})
    return {
        "_about": "Replay of a recorded run, built by tools/build_site_data.py from audit logs, the run log, "
                  "bob_sessions/INDEX.md, decisions and Bob-Task commits. Nothing here runs Bob.",
        "events": events, "tasks": tasks, "truncated_events": truncated,
        "sources": {"audit edits": counts["edits"], "guard blocks": counts["guard_block"],
                    "guard allows": counts["guard_allow"], "run log records": len(runs),
                    "Bob-Task commits": len(commits), "INDEX rows": len(tasks), "decisions": len(log)},
    }, ({"first": bob_days[0], "last": bob_days[-1]} if bob_days else None)


# ---------------------------------------------------------------- golden examples and static verify
def quote_examples(seed):
    """A handful of golden policies (inputs + recorded workbook values) for the quote form."""
    try:
        from harness import common as C
        meta, policies = C.load_inputs(seed)
        oracle = C.load_oracle(seed)
    except Exception:
        return None
    if not policies or oracle is None:
        return None
    picks = [
        ("first golden policy", lambda p: True),
        ("ineligible zone (T09 -> #N/A)", lambda p: str(p.get("zone") or "").upper() == "T09"),
        ("deductible of 10,000 or more (anomaly A1)", lambda p: (p.get("deductible") or 0) >= 10000),
        ("blank roof age", lambda p: p.get("roof_age") is None),
        ("six-month term", lambda p: p.get("term_months") == 6),
    ]
    out, used = [], set()
    for label, pred in picks:
        for i, p in enumerate(policies):
            if i not in used and pred(p):
                used.add(i)
                out.append({"label": label, "row": i + 2,
                            "policy": {k: C.encode(p.get(k)) for k in C.inputs()},
                            "expected": {k: C.encode(oracle[i].get(k)) for k in C.outputs()}})
                break
    gmeta = read_json(C.golden_paths(seed)["meta"]) or {}
    return {"_about": "Golden policies with the values the original workbook produced (recorded oracle). "
                      "Synthetic data for %s." % CARRIER,
            "oracle": (gmeta.get("original") or {}).get("label"), "seed": seed,
            "encoding": {"date": {"date": "YYYY-MM-DD"}, "error": {"error": "#N/A"}, "blank": None},
            "examples": out}


def verify_results(service, sample_path, commit):
    """Run the service over the whole verification sample; None if either is unavailable."""
    if not sample_path or not os.path.exists(sample_path):
        return None, "verification sample not exported yet (make sample)"
    try:
        from harness import common as C
        from harness import compare as CMP
        mod = C.import_service(service)
    except Exception as e:  # ServiceMissing or an import error in the service
        return None, "service %s does not import (%s)" % (service, type(e).__name__)
    with gzip.open(sample_path, "rt", encoding="utf-8") as f:
        sample = json.load(f)
    names = sample.get("outputs") or C.outputs()
    mismatches, per_output, rows_equal = [], {}, 0
    for r in sample["rows"]:
        policy = {k: C.decode(v) for k, v in r["policy"].items()}
        expected = {k: C.decode(v) for k, v in r["expected"].items()}
        got = C.call_quote(mod.quote, policy)
        diff = CMP.compare_row(expected, got, names)
        if not diff:
            rows_equal += 1
        for name, kind in sorted(diff.items(), key=lambda kv: names.index(kv[0]) if kv[0] in names else 99):
            per_output[name] = per_output.get(name, 0) + 1
            if len(mismatches) < MAX_MISMATCHES:
                mismatches.append({"row": r["row"], "policy_id": r["policy"].get("policy_id"), "output_name": name,
                                   "kind": kind, "expected": C.show(expected.get(name)),
                                   "service": C.show(got.get(name)) if CMP.EXCEPTION not in got else got[CMP.EXCEPTION]})
    n = len(sample["rows"])
    return {
        "_about": "Precomputed static fallback for /verify: the service at this commit run over the whole "
                  "verification sample. The live page calls /api/verify instead.",
        "precomputed": True, "commit": commit, "service": service,
        "oracle": sample.get("oracle"), "oracle_variant": sample.get("oracle_variant"),
        "tolerance": sample.get("tolerance"), "rows": n, "rows_equal": rows_equal,
        "cells_compared": n * len(names), "cells_equal": n * len(names) - sum(per_output.values()),
        "mismatches_by_output": dict(sorted(per_output.items())), "mismatches": mismatches,
        "mismatches_truncated": max(0, sum(per_output.values()) - len(mismatches)),
    }, None


# ---------------------------------------------------------------- README headline
README_START = "<!-- headline:start"
README_END = "<!-- headline:end -->"


def _n(x):
    return "{:,}".format(x) if isinstance(x, (int, float)) else "[?]"


def headline_markdown(cert, n_signed):
    """The README headline block, quoting certificate.json numbers exactly."""
    o = cert.get("original") or {}
    dec = o.get("decided_cells")
    decided = dec.get("total", 0) if isinstance(dec, dict) else (dec or 0)
    p = cert.get("patched")
    mut = cert.get("mutation") or {}
    nr = ((cert.get("spotcheck") or {}).get("naive_baseline") or {}).get("naive_round") or {}
    miss = "%.1f%%" % (100 * (1 - nr["p_detect_20"])) if "p_detect_20" in nr else "[P20]"
    lines = [
        "**%s cells compared: %s identical to the workbook, %s differing only in rows traced to %s human-signed "
        "decision%s, %s unexplained.**" % (_n(o.get("cells_compared")), _n(o.get("cells_equal")), _n(decided),
                                            n_signed, "" if n_signed == 1 else "s", _n(o.get("unexplained_cells"))),
        "",
        "- Decision-patched workbook: " + ("%s of %s cells identical, %s unexplained." % (
            _n(p.get("cells_equal")), _n(p.get("cells_compared")), _n(p.get("unexplained_cells"))) if p else "not run (no signed decisions)."),
        "- Harness sensitivity: %s of %s mutants of Bob's code caught." % (_n(mut.get("killed")), _n(mut.get("total"))),
        "- A 20-quote spot check misses naive rounding %s of the time." % miss,
        "- Certificate status: %s · seed %s · %s policies · oracle: %s." % (
            cert.get("status"), cert.get("seed"), _n(cert.get("policies")), (cert.get("oracle") or {}).get("label")),
    ]
    return "\n".join(lines)


def update_readme(cert, n_signed, path=None):
    path = path or os.path.join(ROOT, "README.md")
    if not cert:
        raise SystemExit("--readme: reports/certificate.json is missing")
    if cert.get("service") != DEFAULT_SERVICE:
        raise SystemExit("--readme: the certificate is for %r, not Bob's service; README left unchanged" % cert.get("service"))
    with open(path, encoding="utf-8") as f:
        text = f.read()
    a, b = text.find(README_START), text.find(README_END)
    if a < 0 or b < a:
        raise SystemExit("--readme: headline markers not found in README.md")
    head_end = text.index("\n", a) + 1
    new = text[:head_end] + headline_markdown(cert, n_signed) + "\n" + text[b:]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)


# ---------------------------------------------------------------- main
def build(out_dir, reports_dir, service, sample_path, static, explicit_repo_url, seed=2026):
    os.makedirs(out_dir, exist_ok=True)
    files, missing = {}, []

    def record(name, source):
        files[name] = {"source": source, "sha256": sha256_file(os.path.join(out_dir, name))}

    for name, src, from_reports in COPIES:
        path = os.path.join(reports_dir, src) if from_reports else os.path.join(ROOT, src)
        dest = os.path.join(out_dir, name)
        if os.path.exists(path):
            shutil.copyfile(path, dest)
            record(name, rel(path))
        else:
            if os.path.exists(dest):
                os.remove(dest)
            if name not in OPTIONAL:
                missing.append(name)

    queue_doc = read_json(os.path.join(reports_dir, "decision_queue.json")) or {}
    log = read_jsonl(os.path.join(ROOT, "decisions", "decisions.jsonl"))
    write_json(os.path.join(out_dir, "decisions.json"), {
        "_about": "Decision queue (harness) and signed decision log (people, via tools/decide.py).",
        "queue": queue_doc.get("items", []), "log": log})
    record("decisions.json", "reports/decision_queue.json + decisions/decisions.jsonl")

    replay, recorded = build_replay(log)
    write_json(os.path.join(out_dir, "replay.json"), replay)
    record("replay.json", "audit/, reports/run_log.jsonl, bob_sessions/INDEX.md, git log")

    ex = quote_examples(seed)
    if ex:
        write_json(os.path.join(out_dir, "quote_examples.json"), ex)
        record("quote_examples.json", "golden/")
    else:
        missing.append("quote_examples.json")

    commit = git("rev-parse", "--verify", "-q", "HEAD")
    sample_path = sample_path or os.path.join(ROOT, "service", "sheetshift_ho3", "data", "verify_sample_%d.json.gz" % seed)
    vr, why = verify_results(service, sample_path, commit)
    dest = os.path.join(out_dir, "verify_sample_results.json")
    if vr:
        write_json(dest, vr)
        record("verify_sample_results.json", rel(sample_path) + " + " + service)
    else:
        if os.path.exists(dest):
            os.remove(dest)
        missing.append("verify_sample_results.json")

    cert = read_json(os.path.join(out_dir, "certificate.json")) or {}
    site_service = cert.get("service") or service
    roster = read_json(os.path.join(ROOT, "bob_sessions", "roster.json")) or {}
    site = {
        "_about": "Site metadata written by tools/build_site_data.py. Synthetic data; %s." % CARRIER,
        "schema": 1, "carrier": CARRIER, "mode": "static" if static else "live",
        "commit": commit, "commit_short": commit[:7] if commit else None,
        "repo_url": repo_url(explicit_repo_url), "recorded": recorded,
        "exports_available": roster.get("exports_available") if isinstance(roster, dict) else None,
        "service": {"module": site_service, "standin": site_service != DEFAULT_SERVICE},
        "files": dict(sorted(files.items())), "missing": sorted(missing),
        "notes": ([why] if why else []),
    }
    write_json(os.path.join(out_dir, "site.json"), site)
    return site


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build public/data/*.json for the SheetShift pages")
    ap.add_argument("--out", default=os.path.join(ROOT, "public", "data"))
    ap.add_argument("--reports", default=os.path.join(ROOT, "reports"))
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    ap.add_argument("--sample", help="verification sample (default: the service's data/verify_sample_2026.json.gz)")
    ap.add_argument("--static", action="store_true", help="GitHub Pages mirror: pages show the API-offline banner")
    ap.add_argument("--repo-url", help="https://github.com/<owner>/<repo> (default: from the origin remote)")
    ap.add_argument("--readme", action="store_true", help="rewrite the README headline block from the certificate")
    a = ap.parse_args(argv)
    site = build(os.path.abspath(a.out), os.path.abspath(a.reports), a.service, a.sample, a.static, a.repo_url)
    if a.readme:
        signed = len({d.get("id") for d in read_jsonl(os.path.join(ROOT, "decisions", "decisions.jsonl")) if d.get("by")})
        update_readme(read_json(os.path.join(os.path.abspath(a.reports), "certificate.json")), signed)
        print("README.md headline updated from the certificate")
    print("site data: %d files written to %s; missing: %s" % (
        len(site["files"]) + 1, rel(os.path.abspath(a.out)), ", ".join(site["missing"]) or "none"))
    for n in site["notes"]:
        print("note: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
