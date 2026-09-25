"""Fast smoke test (< 3 s): 200 golden rows, one unit or the whole quote().

usage: python -m harness.smoke [--unit U1..U4] [--n 200] [--seed 2026] [--service MODULE]

* With --unit, the unit's @covers functions run in isolation: upstream outputs come from the
  oracle, so a unit can be checked before rater.py or the other units exist. Functions are
  called as fn(p, c) in column order (docs/CONTRACT.md section 4); an upstream error value
  is passed as the service's XLError (or an object with .code).
* Without --unit, quote(policy) runs end to end on all 43 outputs.
* Rows: the boundary and lint-guided rows first, then a seeded sample of random rows.
* Mismatches whose root cell joins a lint (build/lints.json) are reported as lint-explained,
  not as failures; everything else is unexplained.
* If a needed unit module (service/<pkg>/units/uN_*.py) or the service module is missing,
  the status is "pending" and the exit code is 0.
Writes reports/smoke_last.json atomically (gitignored) and prints one line of <= 120 chars.

Standard library only; Python 3.8+ (runs from Bob's PostToolUse hook).

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import glob
import importlib
import importlib.util
import os
import random
import sys
import time

from harness import common as C
from harness import compare as K
from harness import triage as T

UNITS = ("U1", "U2", "U3", "U4")


def pick_rows(meta, n, seed):
    fixed = min(meta.get("fixed_rows", 0), n)
    rest = list(range(fixed, meta["n"]))
    rng = random.Random(seed * 7919 + 200)
    return list(range(fixed)) + sorted(rng.sample(rest, min(n - fixed, len(rest))))


def unit_files(service):
    """{unit: path or None} for the package's units/ dir; None if the service has no units dir."""
    pkg = C.service_package(service)
    if not pkg:
        return None
    try:
        spec = importlib.util.find_spec(pkg)
    except ModuleNotFoundError:
        return {u: None for u in UNITS}
    if spec is None or not spec.submodule_search_locations:
        return {u: None for u in UNITS}
    udir = os.path.join(list(spec.submodule_search_locations)[0], "units")
    out = {}
    for u in UNITS:
        k = u[1:]
        hits = sorted(glob.glob(os.path.join(udir, "u%s_*.py" % k)) + glob.glob(os.path.join(udir, "u%s.py" % k)))
        out[u] = hits[0] if hits else None
    return out


def import_unit(service, path):
    pkg = C.service_package(service)
    return importlib.import_module("%s.units.%s" % (pkg, os.path.splitext(os.path.basename(path))[0]))


def _err(errcls, code):
    if errcls is not None:
        try:
            return errcls(code)
        except Exception:
            pass
    return C.ErrorValue(code)


def run_unit(unit, service, policies, oracle, rows):
    """Isolated unit run: returns (service_rows, uncovered cells)."""
    spec = C.read_json(os.path.join(C.BUILD, "units.json"))[unit]
    mod = C.import_service(service) if unit_files(service) is None else None
    if mod is None:
        import_unit(service, unit_files(service)[unit])
        pkg = C.service_package(service)
        steps = C.service_steps(importlib.import_module(pkg + ".xlsem"), pkg + ".xlsem")
    else:
        steps = C.service_steps(mod, service)
    by_cell = {}
    for s in steps:
        by_cell.setdefault(s["cell"], s["fn"])
    cols = T.column_info()
    errcls = C.xlerror_class(service)
    uncovered = [c for c in spec["cells"] if c not in by_cell]
    out = [None] * len(policies)
    for i in rows:
        p = dict(policies[i])
        c = {}
        for name in spec["upstream"]:
            v = oracle[i].get(name)
            c[name] = _err(errcls, v.code) if isinstance(v, C.ErrorValue) else v
        res = {}
        for cell, name in zip(spec["cells"], spec["outputs"]):
            fn = by_cell.get(cell)
            if fn is None:
                res[name] = K.MISSING
                continue
            try:
                v = fn(p, c)
            except Exception as e:  # an error value raised, or a crash
                code = C.service_error_code(e)
                if code is None:
                    up = [c.get(q) for q in cols[name].get("precedents", [])]
                    up = [C.service_error_code(x) for x in up if C.service_error_code(x)]
                    code = up[0] if up else None     # lenient: treat as error propagation
                v = _err(errcls, code) if code else "#EXCEPTION %s" % type(e).__name__
            c[name] = v
            res[name] = v
        out[i] = {k: v for k, v in res.items() if v is not K.MISSING}
    return out, uncovered, spec["outputs"]


def smoke(unit, n, seed, service):
    t0 = time.time()
    files = unit_files(service)
    wanted = [unit] if unit else list(UNITS)
    missing = [u for u in wanted if files is not None and files.get(u) is None]
    if not unit:
        try:
            if not missing:
                C.import_service(service)
        except C.ServiceMissing:
            missing.append("rater")
    if missing:
        return {"status": "pending", "unit": unit or "all", "missing": missing,
                "line": "smoke: pending (%s not yet written)" % ", ".join(missing)}
    meta, policies = C.load_inputs(seed)
    rows = pick_rows(meta, n, seed)
    oracle = C.load_oracle(seed, wanted_rows=set(rows))
    if oracle is None:
        return {"status": "no_oracle", "unit": unit or "all", "line": "smoke: golden oracle missing"}
    if unit:
        srows, uncovered, names = run_unit(unit, service, policies, oracle, rows)
    else:
        quote = C.import_service(service).quote
        srows = [None] * len(policies)
        for i in rows:
            srows[i] = C.call_quote(quote, policies[i])
        uncovered, names = [], C.outputs()
    mism = K.compare(oracle, srows, names, rows)
    cols = T.column_info()
    cell_lints, col_lints = T.lint_index()
    lint_cells, failures = {}, []
    unexplained = 0
    for i in sorted(mism):
        mm = mism[i]
        if K.EXCEPTION in srows[i]:
            unexplained += len(mm)
            failures.append({"row": i + 2, "cell": "quote()", "error": srows[i][K.EXCEPTION]})
            continue
        sub = {k: v for k, v in mm.items()}
        roots, attr = T.roots_of_row(sub, cols, [x for x in C.graph()["topo_order"] if x in names])
        for name in sorted(sub, key=lambda x: names.index(x)):
            ls = [T.lint_for_root(r, i, policies[i], cols, cell_lints, col_lints) for r in attr[name]]
            if ls and None not in ls:
                for lid in sorted({l["id"] for l in ls}):
                    lint_cells[lid] = lint_cells.get(lid, 0) + 1
                continue
            unexplained += 1
            if name in roots and len(failures) < 5:
                s = srows[i].get(name, K.MISSING)
                failures.append({"row": i + 2, "cell": cols[name]["cell"], "output": name,
                                 "kind": mm[name], "workbook": C.show(oracle[i].get(name)),
                                 "service": "missing" if s is K.MISSING else C.show(s)})
    bad_rows = len(mism)
    label = unit or "all"
    status = "ok" if unexplained == 0 and not uncovered else "fail"
    line = "smoke %s %s: %d/%d rows equal" % (label, status.upper(), len(rows) - bad_rows, len(rows))
    if unexplained:
        f = failures[0] if failures else {}
        line += "; %d unexplained cells, first %s row %s" % (unexplained, f.get("cell"), f.get("row"))
    if lint_cells:
        line += "; lint-explained cells %s" % ",".join("%s:%d" % kv for kv in sorted(lint_cells.items()))
    if uncovered:
        line += "; uncovered %s" % ",".join(uncovered)
    return {"status": status, "unit": label, "service": service, "seed": seed, "rows": len(rows),
            "rows_equal": len(rows) - bad_rows, "cells_compared": len(rows) * len(names),
            "unexplained_cells": unexplained, "lint_explained_cells": dict(sorted(lint_cells.items())),
            "uncovered": uncovered, "first_failures": failures,
            "seconds": round(time.time() - t0, 2), "line": line[:120]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fast smoke test on golden rows")
    ap.add_argument("--unit", choices=UNITS)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    ap.add_argument("--out", default=os.path.join(C.REPORTS, "smoke_last.json"))
    a = ap.parse_args(argv)
    try:
        res = smoke(a.unit, a.n, a.seed, a.service)
    except Exception as e:  # a broken service module must not break the hook
        res = {"status": "error", "unit": a.unit or "all", "error": "%s: %s" % (type(e).__name__, str(e)[:300]),
               "line": ("smoke %s ERROR: %s: %s" % (a.unit or "all", type(e).__name__, e))[:120]}
    res["at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    C.write_json(a.out, res)
    print(res["line"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
