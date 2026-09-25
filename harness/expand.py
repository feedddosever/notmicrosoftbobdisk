"""Expand the customer workbook to N policy rows for the oracle.

usage: python -m harness.expand [--seed 2026] [--n N] [--workbook PATH] [--out PATH]

Writes the golden inputs into a copy of the workbook *as received*:
  * Policies rows 2..N+1 get the generated inputs (blank = empty cell).
  * Calc rows 2..41 keep their own formulas cell by cell (so the typed-over AM17 and the odd
    X31 stay exactly as the customer has them).
  * Calc rows 42..N+1 get each column's majority formula, computed from the source workbook
    itself (so a decision-patched workbook expands with its repaired template).
Default output: build/cache/harness/expanded_<seed>.xlsx (gitignored). `--n 200 --out
golden/expanded_200.xlsx` produces the small book for the Excel cross-check.

Needs openpyxl (dev/tool dependency): Claude Code sandbox / CI only.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import json
import os
import re
import time
from collections import Counter

from harness import common as C

_NUM = re.compile(r"(\d+)")
PROBE_A, PROBE_B = 100000, 200000


def row_formula_factory(template, col):
    """Compile a row-2 A1 formula into f(r) -> the formula for row r (relative rows shift)."""
    from openpyxl.formula.translate import Translator
    a = Translator(template, origin="%s2" % col).translate_formula("%s%d" % (col, PROBE_A))
    b = Translator(template, origin="%s2" % col).translate_formula("%s%d" % (col, PROBE_B))
    pa, pb = _NUM.split(a), _NUM.split(b)
    if len(pa) != len(pb):
        raise ValueError("cannot compile template %s for column %s" % (template, col))
    parts = []
    for x, y in zip(pa, pb):
        if x == y:
            parts.append(x)
        elif x.isdigit() and y.isdigit() and int(y) - int(x) == PROBE_B - PROBE_A:
            parts.append(int(x) - PROBE_A)          # relative row: offset from the current row
        else:
            raise ValueError("unexpected token difference in %s" % template)

    def at(r):
        return "".join(str(r + p) if isinstance(p, int) else p for p in parts)
    if at(2) != template:
        raise ValueError("template round-trip failed for %s: %s" % (col, at(2)))
    return at


def majority_templates(ws, cols, first, last):
    """{col: row-2 formula} = the most common formula of each column, normalised to row 2."""
    from openpyxl.formula.translate import Translator
    out = {}
    for col in cols:
        seen = Counter()
        for r in range(first, last + 1):
            v = ws["%s%d" % (col, r)].value
            if isinstance(v, str) and v.startswith("="):
                seen[Translator(v, origin="%s%d" % (col, r)).translate_formula("%s2" % col)] += 1
        if not seen:
            raise ValueError("column %s has no formulas" % col)
        out[col] = seen.most_common(1)[0][0]
    return out


def expand(workbook, policies, out):
    """Write `policies` into a copy of `workbook`; returns info (templates, seconds)."""
    import openpyxl
    from tools.gen_workbook import normalize_xlsx
    cfg = C.config()
    t0 = time.time()
    wb = openpyxl.load_workbook(workbook)
    wp, wc = wb[cfg["sheets"]["inputs"]], wb[cfg["sheets"]["calc"]]
    first, last = cfg["first_data_row"], cfg["last_data_row"]
    in_cols, out_cols = cfg["input_columns"], cfg["output_columns"]
    templates = majority_templates(wc, out_cols, first, last)
    makers = {col: row_formula_factory(f, col) for col, f in templates.items()}
    in_fmt = {c: wp["%s%d" % (c, first)].number_format for c in in_cols}
    out_fmt = {c: wc["%s%d" % (c, first)].number_format for c in out_cols}
    names = cfg["inputs"]
    n = len(policies)
    for i, p in enumerate(policies):
        r = first + i
        for c, name in zip(in_cols, names):
            cell = wp["%s%d" % (c, r)]
            cell.value = p.get(name)
            cell.number_format = in_fmt[c]
        if r > last:
            for c in out_cols:
                cell = wc["%s%d" % (c, r)]
                cell.value = makers[c](r)
                cell.number_format = out_fmt[c]
    for r in range(first + n, last + 1):            # fewer policies than the customer book
        for c in in_cols:
            wp["%s%d" % (c, r)].value = None
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    normalize_xlsx(out)
    return {"templates": templates, "rows": n, "seconds": round(time.time() - t0, 2)}


def main(argv=None):
    cfg = C.config()
    ap = argparse.ArgumentParser(description="Expand the workbook to the golden inputs")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--n", type=int, help="use only the first n golden policies")
    ap.add_argument("--workbook", default=os.path.join(C.ROOT, cfg["workbook"]))
    ap.add_argument("--out")
    ap.add_argument("--service", default=C.DEFAULT_SERVICE, help="accepted for uniformity; unused")
    a = ap.parse_args(argv)
    _, policies = C.load_inputs(a.seed)
    if a.n:
        policies = policies[:a.n]
    out = a.out or C.cache_paths(a.seed)["expanded"]
    info = expand(a.workbook, policies, out)
    print(json.dumps({"out": C.rel(out), "rows": info["rows"], "seconds": info["seconds"],
                      "sha256": C.sha256_file(out)}))


if __name__ == "__main__":
    main()
