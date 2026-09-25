"""Optional Excel cross-check (plan decision D5): does real Excel agree with the LibreOffice oracle?

STATUS: stub. The comparison below runs, but it has not yet been run on a CSV exported
by real Excel. Until a person with Excel runs it, the certificate keeps
"excel_crosscheck": null and every page says Excel parity is unverified.

How a person runs it (about 30 minutes, needs desktop Excel):
  1. Produce the small book (CC sandbox or CI, needs LibreOffice only for the oracle):
       python -m harness.expand --seed 2026 --n 200 --out golden/expanded_200.xlsx
  2. Open golden/expanded_200.xlsx in Excel. Press Ctrl+Alt+Shift+F9 (full rebuild and recalc).
  3. On sheet Calc: select all, set number format "General"; set column AF to "yyyy-mm-dd".
     (CSV export writes the displayed text, so formatted cells would lose digits.)
  4. File > Save As > "CSV UTF-8 (Comma delimited)" for sheet Calc only, e.g. calc_excel.csv.
     Record the Excel version (File > Account > About Excel).
  5. python3 tools/excel_crosscheck.py calc_excel.csv --excel-version "Excel 365 16.0.x"
     It writes reports/excel_crosscheck.json; harness.certify can then quote it.

The comparison uses the harness tolerance (numbers within 1e-6, dates and text exact, errors by
code). Numeric differences under 1e-4 are also counted separately as "display precision
suspects", since they usually mean a cell kept a number format in step 3.

Standard library plus the harness package; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from harness import common as C  # noqa: E402
from harness import compare as CMP  # noqa: E402


def read_excel_csv(path):
    """Excel's Calc CSV -> list of {output_name: value}; header row must be the output names."""
    dates = set(C.date_outputs())
    with open(path, encoding="utf-8-sig", newline="") as f:
        rdr = csv.reader(f)
        header = [h.strip() for h in next(rdr)]
        missing = [n for n in C.outputs() if n not in header]
        if missing:
            raise SystemExit("CSV header lacks output names %s; export sheet Calc with its header row" % missing[:5])
        rows = []
        for rec in rdr:
            if not any(x.strip() for x in rec):
                continue
            rows.append({h: C.parse_oracle_cell(v.strip(), h in dates) for h, v in zip(header, rec)})
    return rows


def crosscheck(excel_rows, oracle_rows):
    names = C.outputs()
    n = min(len(excel_rows), len(oracle_rows))
    mism, suspects, by_output = [], 0, {}
    for i in range(n):
        diff = CMP.compare_row(excel_rows[i], oracle_rows[i], names)
        for name, kind in diff.items():
            by_output[name] = by_output.get(name, 0) + 1
            e, o = excel_rows[i].get(name), oracle_rows[i].get(name)
            if kind == "numeric" and abs(float(e) - float(o)) < 1e-4:
                suspects += 1
            if len(mism) < 100:
                mism.append({"row": i + 2, "output_name": name, "kind": kind,
                             "excel": C.show(e), "libreoffice": C.show(o)})
    cells = n * len(names)
    bad = sum(by_output.values())
    return {"rows": n, "cells_compared": cells, "cells_equal": cells - bad,
            "display_precision_suspects": suspects, "mismatches_by_output": dict(sorted(by_output.items())),
            "mismatches": mism}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare an Excel-recalculated Calc CSV with the LibreOffice oracle",
                                 epilog="See the module docstring for the steps in Excel.")
    ap.add_argument("excel_csv", help="sheet Calc of golden/expanded_200.xlsx, recalculated and saved by Excel")
    ap.add_argument("--excel-version", required=True, help='e.g. "Excel 365 16.0.18025"')
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--out", default=os.path.join(C.REPORTS, "excel_crosscheck.json"))
    a = ap.parse_args(argv)
    oracle = C.load_oracle(a.seed)
    if oracle is None:
        raise SystemExit("golden oracle missing: run make oracle first")
    excel = read_excel_csv(a.excel_csv)
    res = crosscheck(excel, oracle)
    gmeta = C.read_json(C.golden_paths(a.seed)["meta"])
    doc = dict({"_about": "Excel vs LibreOffice oracle on the first rows of the golden inputs (tools/excel_crosscheck.py).",
                "excel_version": a.excel_version, "seed": a.seed,
                "libreoffice": (gmeta.get("original") or {}).get("label"),
                "excel_csv_sha256": C.sha256_file(a.excel_csv)}, **res)
    C.write_json(a.out, doc)
    print("excel_crosscheck: %d of %d cells equal over %d rows (%d display-precision suspects) -> %s" % (
        res["cells_equal"], res["cells_compared"], res["rows"], res["display_precision_suspects"], C.rel(a.out)))
    return 0 if res["cells_equal"] == res["cells_compared"] else 1


if __name__ == "__main__":
    sys.exit(main())
