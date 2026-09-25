"""Full golden run: service vs the recorded oracle(s), then triage.

usage: python -m harness.run --golden [--seed 2026] [--service MODULE]

Reads golden/inputs_<seed>.json.gz and golden/oracle_<seed>_Calc.csv.gz (plus the patched
oracle when decisions have been applied), runs quote() on every policy, compares every cell,
and writes:
  reports/last_run.json        summary (gitignored; quoted by /shift-verify)
  reports/mismatches.json      every group with class, signature and examples
  reports/decision_queue.json  one entry per lint with its allowed options
LibreOffice is not needed. Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import json
import os
import sys
import time

from harness import common as C
from harness import compare as K
from harness import triage as T


def run_id_for(hashes):
    parts = [hashes.get(k) or "-" for k in ("service_tree", "inputs", "oracle", "oracle_patched", "decisions")]
    return C.sha256_bytes("|".join(parts).encode("utf-8"))[:12]


def input_hashes(seed, service):
    gp = C.golden_paths(seed)
    root = C.service_root(service)
    return {"service_tree": C.tree_sha256(root) if root else None,
            "inputs": C.sha256_file(gp["inputs"]), "oracle": C.sha256_file(gp["oracle"]),
            "oracle_patched": C.sha256_file(gp["oracle_patched"]),
            "decisions": C.sha256_file(C.DECISIONS)}


def section(policies, oracle, service_rows, mode, decisions, fixed_rows):
    mism = K.compare(oracle, service_rows)
    groups, acct = T.triage(policies, oracle, service_rows, mism, mode, decisions, fixed_rows)
    s = K.summarize(mism, len(policies))
    s.update(acct)
    by_class = {}
    for g in groups:
        by_class[g["class"]] = by_class.get(g["class"], 0) + 1
    s["groups_by_class"] = dict(sorted(by_class.items()))
    return s, groups


def evaluate(seed, service):
    """Run the whole comparison; returns a result dict (raises ServiceMissing if not written)."""
    t = {}
    t0 = time.time()
    meta, policies = C.load_inputs(seed)
    oracle = C.load_oracle(seed)
    if oracle is None:
        raise SystemExit("golden oracle missing: run `make oracle` (Claude Code sandbox / CI)")
    patched = C.load_oracle(seed, patched=True)
    t["load_golden"] = time.time() - t0
    t0 = time.time()
    mod = C.import_service(service)
    rows = K.run_service(mod.quote, policies)
    t["service"] = time.time() - t0
    decisions = C.load_decisions()
    fixed = meta.get("fixed_rows", 0)
    t0 = time.time()
    orig, g_orig = section(policies, oracle, rows, "original", decisions, fixed)
    t["compare_triage"] = time.time() - t0
    pat, g_pat = (None, None)
    if patched is not None:
        t0 = time.time()
        pat, g_pat = section(policies, patched, rows, "patched", decisions, fixed)
        t["compare_triage_patched"] = time.time() - t0
    hashes = input_hashes(seed, service)
    rid = run_id_for(hashes)
    joined = {g["lint"] for g in g_orig if g.get("lint")}
    static_only = [{"lint": l["id"], "type": l["type"], "cell": l.get("cells") or l["cell"],
                    "decision": C.decision_id_for_lint(l["id"])}
                   for l in C.lints() if l["id"] not in joined]
    return {"run_id": rid, "seed": seed, "service": service, "meta": meta, "policies": policies,
            "oracle": oracle, "patched_oracle": patched, "service_rows": rows,
            "original": orig, "groups": g_orig, "patched": pat, "groups_patched": g_pat,
            "static_only": static_only, "hashes": hashes, "decisions": decisions,
            "seconds": {k: round(v, 2) for k, v in t.items()}}


def status_of(res):
    ok = res["original"]["unexplained_cells"] == 0 and (
        res["patched"] is None or res["patched"]["unexplained_cells"] == 0)
    return "all-explained" if ok else "open"


def write_reports(res, last_run=True):
    queue = T.decision_queue(res["groups"], res["run_id"], res["decisions"], res["oracle"], res["service_rows"])
    mism = {"_about": "Mismatch groups from harness.run (classes fixed by harness/triage.py).",
            "run_id": res["run_id"], "seed": res["seed"], "service": res["service"],
            "tolerance": K.TOLERANCE,
            "original": {"summary": res["original"], "groups": res["groups"]},
            "patched": ({"summary": res["patched"], "groups": res["groups_patched"]}
                        if res["patched"] is not None else None),
            "static_only_anomalies": res["static_only"]}
    C.write_json(os.path.join(C.REPORTS, "mismatches.json"), mism)
    C.write_json(os.path.join(C.REPORTS, "decision_queue.json"), queue)
    summary = last_run_summary(res, queue)
    if last_run:
        C.write_json(os.path.join(C.REPORTS, "last_run.json"), summary)
    return summary


def _brief(groups):
    return [{"id": g["id"], "class": g["class"], "cell": g["cell"] or g["output_name"], "kind": g["kind"],
             "lint": g["lint"], "decision": g["decision"], "rows": g["rows"], "cells": g["cells"],
             "signature": g["signature"]["text"]} for g in groups]


def last_run_summary(res, queue):
    keep = ("cells_compared", "cells_equal", "decided_cells", "unexplained_cells",
            "root_cells_explaining_all_diffs", "rows_fully_equal", "groups_by_class")
    out = {"run_id": res["run_id"], "seed": res["seed"], "service": res["service"],
           "policies": len(res["policies"]), "status": status_of(res),
           "original": {k: res["original"][k] for k in keep},
           "patched": ({k: res["patched"][k] for k in keep if k != "decided_cells"}
                       if res["patched"] is not None else None),
           "groups": _brief(res["groups"]),
           "groups_patched": _brief(res["groups_patched"]) if res["groups_patched"] is not None else None,
           "decisions_pending": [i["id"] for i in queue["items"] if i["status"] == "PENDING"],
           "static_only_anomalies": res["static_only"], "seconds": res["seconds"]}
    return out


def print_summary(s):
    o = s["original"]
    print("SheetShift run %s: %d policies, %d/%d cells equal; unexplained %d; decided %d; groups %s" % (
        s["run_id"], s["policies"], o["cells_equal"], o["cells_compared"], o["unexplained_cells"],
        o["decided_cells"]["total"], json.dumps(o["groups_by_class"])))
    for g in s["groups"]:
        print("  %s %-24s %-10s rows=%-5d cells=%-6d lint=%s  %s" % (
            g["id"], g["class"], g["cell"], g["rows"], g["cells"], g["lint"] or "-", g["signature"][:110]))
    if s["patched"] is not None:
        p = s["patched"]
        print("patched oracle: %d/%d cells equal; unexplained %d" % (
            p["cells_equal"], p["cells_compared"], p["unexplained_cells"]))
    if s["static_only_anomalies"]:
        print("static-only anomalies: %s" % ", ".join(x["lint"] for x in s["static_only_anomalies"]))
    if s["decisions_pending"]:
        print("decisions pending: %s" % ", ".join(s["decisions_pending"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Golden run: service vs recorded oracle, then triage")
    ap.add_argument("--golden", action="store_true", help="use the recorded oracle (the only mode)")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    ap.add_argument("--no-last-run", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    a = ap.parse_args(argv)
    try:
        res = evaluate(a.seed, a.service)
    except C.ServiceMissing as e:
        s = {"status": "pending", "service": a.service, "missing": str(e)}
        if not a.no_last_run:
            C.write_json(os.path.join(C.REPORTS, "last_run.json"), s)
        print("SheetShift run: pending (%s)" % e)
        return 0
    s = write_reports(res, last_run=not a.no_last_run)
    if a.json:
        print(json.dumps(s, indent=1, default=str))
    else:
        print_summary(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
