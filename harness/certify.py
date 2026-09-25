"""Certificate: one JSON + one self-contained HTML page summarising the equivalence evidence.

usage: python -m harness.certify [--seed 2026] [--service MODULE]

Runs the golden comparison and traceability afresh, reads the mutation report (make mutate)
and recomputes the spot-check, then writes reports/certificate.json, reports/certificate.html,
reports/traceability.json, reports/spotcheck.json, reports/mismatches.json and
reports/decision_queue.json. Only this command writes the certificate (never a hook, never Bob).

status is GREEN only when every check below passes; each failing check is listed in
status_reasons. RED always when the harness/ tree hash differs from harness/EXPECTED_TREE_SHA256.
  harness tree hash matches        original.unexplained_cells == 0
  no decision pending              patched.unexplained_cells == 0 (when a patched oracle exists)
  traceability gate passes         mutation report present for this exact service tree
Unlabelled mutation survivors are listed under warnings (a person labels them).

Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import html
import os
import sys
import time

from harness import _hash_tree
from harness import common as C
from harness import run as R
from harness import spotcheck as SP
from harness import trace as TR


def hashes(seed, service):
    gp = C.golden_paths(seed)
    root = C.service_root(service)
    return {
        "workbook": C.sha256_file(os.path.join(C.ROOT, C.config()["workbook"])),
        "rate_tables_build": C.sha256_file(os.path.join(C.BUILD, "rate_tables.json")),
        "rate_tables_service": C.sha256_file(os.path.join(root, "data", "rate_tables.json")) if root else None,
        "service_tree": C.tree_sha256(root) if root else None,
        "harness_tree": _hash_tree.tree_sha256(C.HARNESS),
        "harness_tree_expected": _hash_tree.expected(),
        "golden_inputs": C.sha256_file(gp["inputs"]),
        "oracle_original_csv_gz": C.sha256_file(gp["oracle"]),
        "oracle_patched_csv_gz": C.sha256_file(gp["oracle_patched"]),
        "decisions_jsonl": C.sha256_file(C.DECISIONS),
    }


def _groups_by_class(groups):
    out = {}
    for g in groups:
        out.setdefault(g["class"], []).append({
            "id": g["id"], "cell": g["cell"] or g["output_name"], "kind": g["kind"], "rows": g["rows"],
            "cells": g["cells"], "lint": g["lint"], "decision": g["decision"],
            "signature": g["signature"]["text"]})
    return dict(sorted(out.items()))


def _mutation(service_tree):
    p = os.path.join(C.REPORTS, "mutation_report.json")
    if not os.path.exists(p):
        return None, None
    m = C.read_json(p)
    keep = ("total", "killed", "killed_by_crash", "catch_rate", "caught_using_boundary_rows",
            "caught_using_random_rows", "caught_only_by_boundary_rows", "caught_only_by_random_rows",
            "survivors", "sites_found", "seed", "sample_seed", "seconds")
    out = {k: m.get(k) for k in keep}
    out["stale"] = m.get("service_tree_sha256") != service_tree
    return out, m


def certify(seed, service):
    t = {}
    t0 = time.time()
    res = R.evaluate(seed, service)
    R.write_reports(res)
    t["run"] = time.time() - t0
    t0 = time.time()
    tr = TR.trace(service)
    C.write_json(os.path.join(C.REPORTS, "traceability.json"), tr)
    t["trace"] = time.time() - t0
    h = hashes(seed, service)
    mutation, mfull = _mutation(h["service_tree"])
    spot = SP.spotcheck(C.read_json(os.path.join(C.REPORTS, "mismatches.json")), mfull)
    C.write_json(os.path.join(C.REPORTS, "spotcheck.json"), spot)
    gmeta = C.read_json(C.golden_paths(seed)["meta"])
    orig, pat = res["original"], res["patched"]
    queue = C.read_json(os.path.join(C.REPORTS, "decision_queue.json"))
    pending = [i["id"] for i in queue["items"] if i["status"] == "PENDING"]
    reasons, warnings = [], []
    if h["harness_tree"] != h["harness_tree_expected"]:
        reasons.append("harness tree hash differs from harness/EXPECTED_TREE_SHA256")
    if orig["unexplained_cells"]:
        reasons.append("original: %d unexplained cells" % orig["unexplained_cells"])
    if pending:
        reasons.append("decisions pending: %s" % ", ".join(pending))
    adopt = [d for d in res["decisions"].values() if d.get("option") == "adopt-manual"]
    if adopt and pat is None:
        reasons.append("adopt-manual decisions exist but the patched oracle is missing (make patch)")
    pmeta = gmeta.get("patched") or {}
    if pat is not None and pmeta.get("decisions_sha256") != h["decisions_jsonl"]:
        reasons.append("patched oracle was built from different decisions (make patch)")
    if pat is not None and pat["unexplained_cells"]:
        reasons.append("patched: %d unexplained cells" % pat["unexplained_cells"])
    if tr["gate"] != "pass":
        reasons.append("traceability gate failed: uncovered [%s], doubly tagged [%s], unknown out-of-scope [%s]" % (
            ", ".join(tr["uncovered"]), ", ".join(tr.get("doubly_tagged", [])),
            ", ".join(tr.get("out_of_scope_not_in_graph", []))))
    if mutation is None:
        reasons.append("mutation report missing (make mutate)")
    elif mutation["stale"]:
        reasons.append("mutation report is for a different service tree (re-run make mutate)")
    elif any(s["label"] == "unlabeled" for s in mutation["survivors"]):
        warnings.append("unlabelled mutation survivors: %s" % ", ".join(
            s["id"] for s in mutation["survivors"] if s["label"] == "unlabeled"))
    meta = res["meta"]
    o = gmeta.get("original", {})
    cert = {
        "_about": "SheetShift equivalence certificate (harness/certify.py). Synthetic data; "
                  "Example Mutual Insurance Co. is FICTIONAL; the anomalies were seeded.",
        "status": "GREEN" if not reasons else "RED", "status_reasons": reasons, "warnings": warnings,
        "run_id": res["run_id"], "seed": seed, "service": service, "policies": len(res["policies"]),
        "boundary_policies": meta.get("boundary_policies"), "lint_guided_rows": meta.get("lint_guided_rows"),
        "original": {k: orig[k] for k in ("cells_compared", "cells_equal", "decided_cells",
                                            "unexplained_cells", "root_cells_explaining_all_diffs")},
        "patched": ({k: pat[k] for k in ("cells_compared", "cells_equal", "unexplained_cells")}
                    if pat is not None else None),
        "groups_by_class": _groups_by_class(res["groups"]),
        "groups_by_class_patched": _groups_by_class(res["groups_patched"]) if pat is not None else None,
        "static_only_anomalies": res["static_only"],
        "decisions": [{"id": i["id"], "lint": i["lint"], "status": i["status"],
                       "option": (i["decision"] or {}).get("option"), "rule": (i["decision"] or {}).get("rule"),
                       "by": (i["decision"] or {}).get("by")} for i in queue["items"]],
        "mutation": mutation,
        "naive_baseline": (mfull or {}).get("naive_baseline"),
        "spotcheck": {"groups": spot["groups"], "naive_baseline": spot["naive_baseline"]},
        "traceability": {"total_rules": tr["total_rules"], "counts": tr["counts"], "gate": tr["gate"]},
        "oracle": {"engine": o.get("engine"), "version": o.get("version"), "label": o.get("label"),
                   "recalc": o.get("recalc"), "profile_sha256": o.get("profile_sha256")},
        "excel_crosscheck": None,
        "hashes": h, "git_commit": C.git_commit(),
        "seconds": dict({k: round(v, 2) for k, v in t.items()}, **{"run_" + k: v for k, v in res["seconds"].items()},
                        oracle_recalc=o.get("seconds_recalc"),
                        mutation=(mutation or {}).get("seconds")),
        "limits": C.graph().get("limits", []),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    return cert


# ---------------------------------------------------------------- HTML
CSS = """
:root{--bg:#fbfbf9;--fg:#1d1f21;--muted:#5d6166;--card:#fff;--line:#dcdcd6;--ok:#1d7a46;--bad:#b3261e;--accent:#2f5d9e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15171a;--fg:#e6e6e3;--muted:#a3a7ad;--card:#1d2024;--line:#33373d;--ok:#5cc78a;--bad:#ff8a80;--accent:#8fb4ee}}
:root[data-theme="dark"]{--bg:#15171a;--fg:#e6e6e3;--muted:#a3a7ad;--card:#1d2024;--line:#33373d;--ok:#5cc78a;--bad:#ff8a80;--accent:#8fb4ee}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 48px}h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:28px 0 8px}
.muted{color:var(--muted)}.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:700;color:#fff}
.GREEN{background:var(--ok)}.RED{background:var(--bad)}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:14px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:1.35rem;font-variant-numeric:tabular-nums}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;background:var(--card);font-size:.9rem}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}td.n{text-align:right;font-variant-numeric:tabular-nums}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em;word-break:break-all}ul{padding-left:20px}
"""


def _e(x):
    return html.escape("" if x is None else str(x))


def _table(head, rows):
    h = "".join("<th>%s</th>" % _e(x) for x in head)
    body = "".join("<tr>%s</tr>" % "".join(
        '<td class="n">%s</td>' % _e(c) if isinstance(c, (int, float)) else "<td>%s</td>" % _e(c) for c in r)
        for r in rows)
    return '<div class="wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (h, body)


def render_html(c):
    o = c["original"]
    kp = [("Policies", "{:,}".format(c["policies"])), ("Cells compared", "{:,}".format(o["cells_compared"])),
          ("Cells equal", "{:,}".format(o["cells_equal"])), ("Decided cells", "{:,}".format(o["decided_cells"]["total"])),
          ("Unexplained cells", "{:,}".format(o["unexplained_cells"])),
          ("Traceability", "%d/%d rules" % (c["traceability"]["counts"]["covered"] + c["traceability"]["counts"]["out_of_scope"],
                                            c["traceability"]["total_rules"]))]
    if c["mutation"]:
        kp.append(("Mutants killed", "%d/%d" % (c["mutation"]["killed"], c["mutation"]["total"])))
    if c["patched"]:
        kp.append(("Patched unexplained", "{:,}".format(c["patched"]["unexplained_cells"])))
    groups = [(g["id"], cls, g["cell"], g["rows"], g["cells"], g["lint"] or "", g["signature"])
              for cls, gs in c["groups_by_class"].items() for g in gs]
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>SheetShift certificate</title><style>%s</style></head><body><main>" % CSS,
        "<h1>SheetShift equivalence certificate <span class='badge %s'>%s</span></h1>" % (_e(c["status"]), _e(c["status"])),
        "<p class='muted'>Example Mutual Insurance Co. (FICTIONAL) HO-3 workbook vs the translated service "
        "<code>%s</code>. Run <code>%s</code>, seed %s, generated %s. All data synthetic; anomalies seeded.</p>" % (
            _e(c["service"]), _e(c["run_id"]), _e(c["seed"]), _e(c["generated_at"])),
        "<div class='kpis'>%s</div>" % "".join("<div class='kpi'><span class='muted'>%s</span><b>%s</b></div>" % (_e(k), _e(v)) for k, v in kp),
    ]
    if c["status_reasons"] or c["warnings"]:
        parts.append("<h2>Status reasons</h2><ul>%s</ul>" % "".join(
            "<li>%s</li>" % _e(r) for r in c["status_reasons"] + ["warning: " + w for w in c["warnings"]]))
    parts.append("<h2>Mismatch groups (original oracle)</h2>")
    parts.append(_table(["Group", "Class", "Root", "Rows", "Cells", "Lint", "Signature"], groups) if groups
                 else "<p>No mismatches.</p>")
    parts.append("<h2>Decisions</h2>" + _table(["Id", "Lint", "Status", "Option", "Rule", "By"],
                 [(d["id"], d["lint"], d["status"], d["option"] or "", d["rule"] or "", d["by"] or "") for d in c["decisions"]]))
    if c["static_only_anomalies"]:
        parts.append("<p>Static-only anomalies (lint, no runtime difference): %s</p>" % _e(
            ", ".join(x["lint"] for x in c["static_only_anomalies"])))
    if c["naive_baseline"]:
        nb = c["naive_baseline"]
        parts.append("<h2>Naive translation baseline</h2>" + _table(
            ["Operator", "Rows affected", "p_detect_20"],
            [(k, v if k == "any_rows" else v.get("rows_affected"),
              c["spotcheck"]["naive_baseline"].get(k, {}).get("p_detect_20")) for k, v in nb.items()]))
    if c["mutation"]:
        m = c["mutation"]
        parts.append("<h2>Mutation self-test</h2><p>%d of %d mutants killed (%d by crash); caught using boundary rows %d, "
                     "random rows %d; only by boundary rows: %s.</p>" % (
                         m["killed"], m["total"], m["killed_by_crash"], m["caught_using_boundary_rows"],
                         m["caught_using_random_rows"], _e(", ".join(m["caught_only_by_boundary_rows"]) or "none")))
        if m["survivors"]:
            parts.append(_table(["Survivor", "Operator", "File:line", "Change", "Label"],
                                [(s["id"], s["op"], "%s:%s" % (s["file"], s["line"]), s["change"], s["label"])
                                 for s in m["survivors"]]))
    parts.append("<h2>Oracle and hashes</h2>" + _table(["Item", "Value"], [
        ("Oracle", c["oracle"].get("label")), ("Recalculation", c["oracle"].get("recalc")),
        ("Excel cross-check", "not run (Excel parity UNVERIFIED)" if c["excel_crosscheck"] is None else "run"),
        ("git commit", c["git_commit"])] + [(k, v) for k, v in c["hashes"].items()]))
    parts.append("<h2>Limits</h2><ul>%s</ul>" % "".join("<li>%s</li>" % _e(x) for x in c["limits"]))
    parts.append("<p class='muted'>Written by harness/certify.py (Claude Code harness). Numbers are copied from "
                 "reports/certificate.json.</p></main></body></html>\n")
    return "".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the equivalence certificate")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    a = ap.parse_args(argv)
    try:
        cert = certify(a.seed, a.service)
    except C.ServiceMissing as e:
        print("certify: pending (%s); no certificate written" % e)
        return 1
    C.write_json(os.path.join(C.REPORTS, "certificate.json"), cert)
    C.write_text(os.path.join(C.REPORTS, "certificate.html"), render_html(cert))
    print("certificate %s: %s" % (cert["status"], "; ".join(cert["status_reasons"]) or "all checks pass"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
