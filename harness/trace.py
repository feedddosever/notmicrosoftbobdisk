"""Cell-to-code traceability: join the 48 workbook rules with the service's @covers STEPS.

usage: python -m harness.trace [--service MODULE] [--out reports/traceability.json]

For every rule in build/graph.json rule_order (43 Calc columns + Summary B2..B6):
  {cell, output_name, template, functions: [{file, line, name}], tests, status}
status is covered, out_of_scope or uncovered. Out-of-scope declarations are generated from
graph.json (the Summary cells are whole-book totals, not part of rating one quote) plus any
entries in the service's OUT_OF_SCOPE.json (for example an escalated decision).
Gate: every rule is covered or declared out of scope, no column is tagged twice, no @covers
name disagrees with graph.json, and every out-of-scope cell exists in the graph; exit 1 otherwise.
Also writes a reverse index "file:function" -> cells.

Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import glob
import os
import re
import sys

from harness import common as C

SUMMARY_REASON = "whole-book aggregate over all policy rows; not part of rating a single quote"


def out_of_scope_declarations(service):
    """{cell: {reason, source}} from graph.json and the service's OUT_OF_SCOPE.json."""
    out = {}
    for c in C.graph().get("cells", []):
        out[c["cell"]] = {"reason": SUMMARY_REASON, "source": "build/graph.json"}
    root = C.service_root(service)
    path = os.path.join(root, "OUT_OF_SCOPE.json") if root else None
    if path and os.path.exists(path):
        doc = C.read_json(path)
        items = doc.get("items", doc) if isinstance(doc, dict) else doc
        if isinstance(items, dict):
            items = [dict(v, cell=k) if isinstance(v, dict) else {"cell": k, "reason": v} for k, v in items.items()]
        for it in items or []:
            if isinstance(it, dict) and it.get("cell"):
                out[it["cell"]] = {"reason": it.get("reason") or it.get("why"),
                                   "decision": it.get("decision"), "source": C.rel(path)}
    return out


def test_refs(names):
    """{function name: ['tests/test_x.py:LINE', ...]} (at most 5 each)."""
    refs = {n: [] for n in names}
    pats = {n: re.compile(r"\b%s\b" % re.escape(n)) for n in names if n}
    for path in sorted(glob.glob(os.path.join(C.ROOT, "tests", "test_*.py"))):
        if os.path.basename(path) == "test_harness_selfcheck.py":
            continue
        with open(path, encoding="utf-8") as f:
            for k, line in enumerate(f, 1):
                for n, p in pats.items():
                    if len(refs[n]) < 5 and p.search(line):
                        refs[n].append("%s:%d" % (C.rel(path), k))
    return refs


def trace(service):
    mod = C.import_service(service)
    steps = C.service_steps(mod, service)
    g = C.graph()
    rules = {c["cell"]: {"output_name": c["output_name"], "template": c.get("template_a1")} for c in g["columns"]}
    for c in g.get("cells", []):
        rules[c["cell"]] = {"output_name": None, "template": c.get("formula")}
    by_cell = {}
    for s in steps:
        fn = s.get("fn")
        by_cell.setdefault(s["cell"], []).append({
            "file": C.rel(s["file"]) if s.get("file") else None, "line": s.get("line"),
            "name": s.get("name_fn") or getattr(fn, "__name__", None), "output_name": s.get("name")})
    tests = test_refs(sorted({f["name"] for fs in by_cell.values() for f in fs if f["name"]}))
    oos = out_of_scope_declarations(service)
    out, reverse = [], {}
    for cell in g["rule_order"]:
        fns = by_cell.get(cell, [])
        status = "covered" if fns else ("out_of_scope" if cell in oos else "uncovered")
        entry = {"cell": cell, "output_name": rules[cell]["output_name"], "template": rules[cell]["template"],
                 "functions": [{"file": f["file"], "line": f["line"], "name": f["name"]} for f in fns],
                 "tests": sorted({t for f in fns for t in tests.get(f["name"], [])}), "status": status}
        if status == "out_of_scope":
            entry["out_of_scope"] = oos[cell]
        wrong = [f["output_name"] for f in fns if f["output_name"] and f["output_name"] != rules[cell]["output_name"]]
        if wrong and rules[cell]["output_name"]:
            entry["name_mismatch"] = wrong
        out.append(entry)
        for f in fns:
            reverse.setdefault("%s:%s" % (f["file"], f["name"]), []).append(cell)
    unknown = sorted(c for c in by_cell if c not in rules)
    doubly = sorted(c for c in by_cell if c in rules and len(by_cell[c]) > 1)
    oos_unknown = sorted(c for c in oos if c not in rules)
    counts = {k: sum(1 for e in out if e["status"] == k) for k in ("covered", "out_of_scope", "uncovered")}
    gate = (counts["uncovered"] == 0 and not any("name_mismatch" in e for e in out)
            and not doubly and not oos_unknown)
    return {"_about": "Workbook rule -> service code traceability (harness/trace.py).",
            "service": service, "total_rules": len(out), "counts": counts, "gate": "pass" if gate else "fail",
            "uncovered": [e["cell"] for e in out if e["status"] == "uncovered"],
            "unknown_cells_in_steps": unknown, "doubly_tagged": doubly,
            "out_of_scope_not_in_graph": oos_unknown, "rules": out,
            "reverse_index": dict(sorted(reverse.items()))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Workbook rule -> code traceability")
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED, help="accepted for uniformity; unused")
    ap.add_argument("--out", default=os.path.join(C.REPORTS, "traceability.json"))
    a = ap.parse_args(argv)
    try:
        doc = trace(a.service)
    except C.ServiceMissing as e:
        print("trace: pending (%s)" % e)
        return 0
    C.write_json(a.out, doc)
    c = doc["counts"]
    print("trace: %d covered, %d out of scope, %d uncovered of %d rules; gate %s" % (
        c["covered"], c["out_of_scope"], c["uncovered"], doc["total_rules"], doc["gate"].upper()))
    return 0 if doc["gate"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
