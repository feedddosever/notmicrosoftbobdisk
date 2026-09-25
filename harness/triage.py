"""Root cells, groups, signatures and the fixed classification rules (plan section 6.4).

usage: python -m harness.triage [--seed 2026] [--service MODULE]
       (same pipeline as harness.run; writes reports/mismatches.json and decision_queue.json)

* Root of a mismatch: a mismatched cell whose Calc precedents all match in that row.
* Group: root column + kind of difference (+ the lint the root cell joins, if any).
* Signature: the best single-condition predicate over the root column's raw inputs and its
  immediate precedents (oracle values), with its precision = group rows / rows matching.
* Classes (first rule that applies wins):
    decided                   a signed adopt-manual decision covers the group's lint
    escalated                 the decision is "escalate": counts as unexplained until resolved
    spreadsheet-anomaly       the group joins a lint on the same column or cell, no decision yet
    translation-bug           the group joins a decided lint but the service does not follow
                              the decision (keep-workbook broken, or adopt-manual missing
                              against the patched oracle)
    translation-bug-rounding  no lint; every delta is exactly one unit in the last place of
                              the column's outermost ROUND/ROUNDUP step (+-0.01 at ROUND(..,2),
                              +-1 at ROUNDUP(..,0))
    translation-bug           no lint; signature precision >= 0.95
    needs-human               everything else
  A column lint of type range_short_of_table joins only the rows whose lookup key reaches the
  keys the short range misses, so a real translation bug in that column is not masked.

Standard library only; Python 3.8+. Bob never edits these rules; Bob fixes the code.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import datetime as dt
import re
import sys
from collections import Counter, defaultdict

from harness import common as C
from harness.compare import EXCEPTION, MISSING

PRECISION_BUG = 0.95
CLASS_ORDER = ["translation-bug", "translation-bug-rounding", "needs-human", "spreadsheet-anomaly",
               "escalated", "decided"]
_ROUND = re.compile(r"^=(ROUND|ROUNDUP|ROUNDDOWN)\((.*),\s*(-?\d+)\)$", re.S)


# ---------------------------------------------------------------- graph helpers
def column_info():
    """{output_name: graph column dict}."""
    return {c["output_name"]: c for c in C.graph()["columns"]}


def transitive_inputs(cols, name, memo=None):
    memo = {} if memo is None else memo
    if name in memo:
        return memo[name]
    out = set(cols[name].get("inputs", []))
    for p in cols[name].get("precedents", []):
        out |= transitive_inputs(cols, p, memo)
    memo[name] = out
    return out


def rounding_step(template):
    """('ROUND', digits) if the column's outermost step is ROUND/ROUNDUP/ROUNDDOWN, else None."""
    m = _ROUND.match(template or "")
    if not m:
        return None
    depth = 0                       # the matched ',digits)' must close the outer call
    for ch in m.group(2):
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return None
    return (m.group(1), int(m.group(3))) if depth == 0 else None


# ---------------------------------------------------------------- lint joining
def lint_index():
    cell_lints, col_lints = {}, defaultdict(list)
    for l in C.lints():
        if l.get("row"):
            cell_lints[(l["output_name"], l["row"])] = l
        else:
            col_lints[l["output_name"]].append(l)
    return cell_lints, col_lints


def _num(v):
    if v is None:
        return 0
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def lint_for_root(name, row_idx, policy, cols, cell_lints, col_lints):
    """The lint a root cell (output `name`, 0-based row) joins, or None."""
    l = cell_lints.get((name, row_idx + 2))
    if l:
        return l
    for l in col_lints.get(name, []):
        if l["type"] == "range_short_of_table" and l.get("missing_keys"):
            ins = cols[name].get("inputs", [])
            keys = [k for k in l["missing_keys"] if isinstance(k, (int, float))]
            if len(ins) == 1 and keys:
                v = _num(policy.get(ins[0]))
                if v is None or v < min(keys):
                    continue            # the short range cannot explain this row
        return l
    return None


# ---------------------------------------------------------------- roots
def roots_of_row(mm, cols, order):
    """For one row's mismatches {name: kind}: (roots set, {name: set of root names})."""
    roots, attr = set(), {}
    for n in order:
        if n not in mm:
            continue
        bad_precs = [p for p in cols[n].get("precedents", []) if p in mm]
        if not bad_precs:
            roots.add(n)
            attr[n] = {n}
        else:
            s = set()
            for p in bad_precs:
                s |= attr[p]
            attr[n] = s
    return roots, attr


# ---------------------------------------------------------------- signature
def _ordinal(v):
    if isinstance(v, dt.date):
        return v.toordinal()
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    return None


def _fmt(v, is_date):
    if is_date:
        return dt.date.fromordinal(int(v)).isoformat()
    return ("%g" % v) if isinstance(v, float) else str(v)


def delta_profile(rows, name, oracle, service):
    d = Counter()
    for i in rows:
        o, s = oracle[i].get(name), service[i].get(name, MISSING)
        if isinstance(o, float) and isinstance(s, (int, float)) and not isinstance(s, bool):
            d["%+.6g" % (float(s) - o)] += 1
        else:
            d["%s -> %s" % (C.show(o)[:14], "missing" if s is MISSING else C.show(s)[:14])] += 1
    top = ", ".join("%s x%d" % kv for kv in d.most_common(3))
    return top + (" ..." if len(d) > 3 else ""), d


def signature(rows, name, policies, oracle, cols, memo=None):
    """Best single-condition predicate: dict {predicate, precision, support, population}."""
    getters = {}
    for v in sorted(transitive_inputs(cols, name, memo)):
        if v != C.config()["id_column"]:
            getters["p." + v] = (lambda i, v=v: policies[i].get(v))
    for p in cols[name].get("precedents", []):
        getters["c." + p] = (lambda i, p=p: oracle[i].get(p))
    n_all = len(policies)
    best = None
    support = len(rows)
    for vname, get in sorted(getters.items()):
        vals = [get(i) for i in rows]
        ords = [_ordinal(v) for v in vals]
        is_date = isinstance(vals[0], dt.date)
        cands = []
        if all(o is not None for o in ords):
            lo, hi = min(ords), max(ords)      # a range first: it wins ties (reads better)
            cands.append((lambda x, lo=lo, hi=hi: _ordinal(x) is not None and lo <= _ordinal(x) <= hi,
                          "%s in [%s..%s]" % (vname, _fmt(lo, is_date), _fmt(hi, is_date))))
            if len(set(ords)) <= 8 and not is_date:
                vs = set(ords)
                cands.append((lambda x, vs=vs: _ordinal(x) in vs,
                              "%s in {%s}" % (vname, ", ".join(_fmt(x, False) for x in sorted(vs)))))
        else:
            vs = set(map(repr, vals))
            if len(vs) <= 6:
                cands.append((lambda x, vs=vs: repr(x) in vs,
                              "%s in {%s}" % (vname, ", ".join(sorted(vs)))))
        for pred, text in cands:
            pop = sum(1 for i in range(n_all) if pred(get(i)))
            cand = (support / float(max(pop, 1)), -pop, text)
            if best is None or cand[:2] > best[:2]:
                best = cand
    if best is None:
        return {"predicate": None, "precision": 0.0, "support": support, "population": None}
    return {"predicate": best[2], "precision": round(best[0], 4), "support": support,
            "population": -best[1]}


def is_rounding_delta(dcounter, step):
    if not step or not dcounter:
        return False
    unit = 10.0 ** (-step[1])
    for k in dcounter:
        try:
            d = abs(float(k))
        except ValueError:
            return False
        if abs(d - unit) > max(1e-9, unit * 1e-6):
            return False
    return True


# ---------------------------------------------------------------- triage
def triage(policies, oracle, service, mism, mode="original", decisions=None, fixed_rows=0):
    """Group and classify mismatches. Returns (groups, cell_accounting)."""
    cols = column_info()
    order = C.graph()["topo_order"]
    cell_lints, col_lints = lint_index()
    decisions = C.load_decisions() if decisions is None else decisions
    memo = {}
    groups = defaultdict(list)          # key -> [row indexes of root cells]
    cell_roots = []                     # (row, name, frozenset of group keys)
    for i in sorted(mism):
        mm = mism[i]
        if EXCEPTION in service[i]:
            key = ("*", "exception", service[i][EXCEPTION].split(":")[0][:60], None)
            groups[key].append(i)
            cell_roots.extend((i, n, frozenset([key])) for n in mm)
            continue
        roots, attr = roots_of_row(mm, cols, order)
        keys = {}
        for r in roots:
            l = lint_for_root(r, i, policies[i], cols, cell_lints, col_lints)
            keys[r] = (r, mm[r], None, l["id"] if l else None)
            groups[keys[r]].append(i)
        for n in mm:
            cell_roots.append((i, n, frozenset(keys[r] for r in attr[n])))
    cells_per_group = Counter()
    for _, _, ks in cell_roots:
        for k in ks:
            cells_per_group[k] += 1
    out = {}
    lints_by_id = {l["id"]: l for l in C.lints()}
    for key, rows in groups.items():
        name, kind, crash, lint_id = key
        g = {"root_column": None, "cell": None, "output_name": name, "kind": kind,
             "lint": lint_id, "decision": None, "decision_option": None}
        if crash:
            g.update(output_name="quote()", crash=crash)
            sig = signature_for_crash(rows, policies)
            prof, dc = "service raised " + crash, Counter()
            step = None
        else:
            col = cols[name]
            g.update(root_column=col["col"], cell=col["cell"])
            prof, dc = delta_profile(rows, name, oracle, service)
            sig = signature(rows, name, policies, oracle, cols, memo)
            step = rounding_step(col.get("template_a1"))
        cls, reason = classify(g, lint_id, lints_by_id, decisions, mode, dc, step, sig, crash)
        rows_sorted = sorted(set(rows))
        g.update({
            "class": cls, "reason": reason, "root_cells": len(rows), "rows": len(rows_sorted),
            "cells": cells_per_group[key],
            "boundary_rows": sum(1 for i in rows_sorted if i < fixed_rows),
            "random_rows": sum(1 for i in rows_sorted if i >= fixed_rows),
            "rounding_step": ("%s(..,%d)" % step) if step else None,
            "signature": dict(sig, delta_profile=prof, text="delta %s | %s%s" % (
                prof, ("single row %d (%s); " % (rows_sorted[0] + 2, policies[rows_sorted[0]].get(
                    C.config()["id_column"]))) if len(rows_sorted) == 1 else "", _sig_text(sig))),
            "examples": [example(i, name, policies, oracle, service, cols) for i in rows_sorted[:3]],
            "sheet_rows": [i + 2 for i in rows_sorted],
        })
        out[key] = g
    ranked = sorted(out.items(), key=lambda kv: (CLASS_ORDER.index(kv[1]["class"]), -kv[1]["cells"],
                                                 order.index(kv[0][0]) if kv[0][0] in order else -1,
                                                 kv[0][1]))
    for k, (key, g) in enumerate(ranked, 1):
        g["id"] = "G%02d" % k
    gid = {key: g["id"] for key, g in ranked}
    acct = account(cell_roots, dict(ranked), gid)
    return [dict([("id", g["id"])] + [(k, v) for k, v in g.items() if k != "id"]) for _, g in ranked], acct


def _sig_text(sig):
    if not sig.get("predicate"):
        return "no single-condition predicate"
    return "%s (precision %.2f: %d of %s such rows)" % (sig["predicate"], sig["precision"],
                                                       sig["support"], sig["population"])


def signature_for_crash(rows, policies):
    cols = {"_all": {"inputs": [n for n in C.inputs()], "precedents": []}}
    return signature(rows, "_all", policies, [{}] * len(policies), cols)


def classify(g, lint_id, lints_by_id, decisions, mode, dc, step, sig, crash):
    """The fixed rules; returns (class, reason)."""
    if crash:
        return "translation-bug", "quote() raised an exception"
    if lint_id:
        did = C.decision_id_for_lint(lint_id)
        dec = decisions.get(did)
        g["decision"] = did
        if dec is None:
            return "spreadsheet-anomaly", "joins lint %s (%s); awaiting a person's decision %s" % (
                lint_id, lints_by_id[lint_id]["type"], did)
        opt = dec.get("option")
        g["decision_option"] = opt
        if opt == "escalate":
            return "escalated", "%s escalated; unexplained until resolved" % did
        if opt == "adopt-manual" and mode == "original":
            return "decided", "%s adopt-manual (%s) signed by %s" % (did, dec.get("rule"), dec.get("by"))
        if opt == "adopt-manual":
            return "translation-bug", "%s adopt-manual: service differs from the patched oracle" % did
        return "translation-bug", "%s %s: service does not keep the workbook behaviour" % (did, opt)
    if is_rounding_delta(dc, step):
        return "translation-bug-rounding", "every delta is one unit of the %s(..,%d) step" % step
    if sig.get("precision", 0) >= PRECISION_BUG:
        return "translation-bug", "signature precision %.2f >= %.2f" % (sig["precision"], PRECISION_BUG)
    return "needs-human", "no lint and signature precision %.2f < %.2f" % (sig.get("precision", 0), PRECISION_BUG)


def example(i, name, policies, oracle, service, cols):
    ex = {"row": i + 2, "policy_id": policies[i].get(C.config()["id_column"])}
    if name in cols:
        ex["workbook"] = C.show(oracle[i].get(name))
        s = service[i].get(name, MISSING)
        ex["service"] = "missing" if s is MISSING else C.show(s)
        ins = sorted(transitive_inputs(cols, name))
        ex["inputs"] = {k: C.encode(policies[i].get(k)) for k in ins}
    else:
        ex["service"] = service[i].get(EXCEPTION)
    return ex


def account(cell_roots, groups_by_key, gid):
    """Cell accounting: decided / unexplained cells and per-class totals."""
    decided_by = Counter()
    decided_total = unexplained = 0
    by_class = Counter()
    for _, _, ks in cell_roots:
        classes = {groups_by_key[k]["class"] for k in ks}
        if classes == {"decided"}:
            decided_total += 1
            for k in ks:
                decided_by[groups_by_key[k]["decision"]] += 1
        else:
            unexplained += 1
        for c in classes:
            by_class[c] += 1
    return {"decided_cells": {"total": decided_total, "by_decision": dict(sorted(decided_by.items()))},
            "unexplained_cells": unexplained,
            "root_cells_explaining_all_diffs": sum(g["root_cells"] for g in groups_by_key.values()),
            "cells_by_class": dict(sorted(by_class.items()))}


def decision_queue(groups, run_id, decisions=None):
    """One entry per lint with its allowed options, status and runtime evidence."""
    decisions = C.load_decisions() if decisions is None else decisions
    items = []
    for l in C.lints():
        did = C.decision_id_for_lint(l["id"])
        joined = [g for g in groups if g.get("lint") == l["id"]]
        dec = decisions.get(did)
        status = "PENDING" if dec is None else ("ESCALATED" if dec.get("option") == "escalate" else "DECIDED")
        runtime = None
        if joined:
            g0 = joined[0]
            runtime = {"groups": [g["id"] for g in joined], "rows": sum(g["rows"] for g in joined),
                       "cells": sum(g["cells"] for g in joined),
                       "signature": g0["signature"]["text"], "example": g0["examples"][0]}
        items.append({
            "id": did, "lint": l["id"], "type": l["type"], "cell": l.get("cells") or l["cell"],
            "output_name": l["output_name"], "formula": l.get("formula"),
            "column_rule": l.get("column_rule"), "manual_rule": l.get("manual_rule"),
            "options": list(l.get("options", [])), "status": status,
            "decision": dec, "runtime": runtime, "static_only": runtime is None,
        })
    return {"_about": "Anomalies awaiting (or holding) a person's decision. Decide with "
                      "tools/decide.py <id> --option <allowed option> (people only).",
            "run_id": run_id, "items": items}


def main(argv=None):
    from harness import run
    return run.main(list(argv if argv is not None else sys.argv[1:]) + ["--no-last-run"])


if __name__ == "__main__":
    sys.exit(main())
