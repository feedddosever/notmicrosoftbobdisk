"""Optional Excel cross-check (README > Limits): does real Excel agree with the LibreOffice oracle?

Until a person with Excel runs it, golden/excel_crosscheck.json does not exist, the
certificate keeps "excel_crosscheck": null and every page says Excel parity is unverified.

How a person runs it (about 10 minutes, needs desktop Excel):
  1. Open golden/expanded_200.xlsx in Excel (click Enable Editing if Excel shows Protected View).
     The book asks for a full recalculation on load; to be sure, press Ctrl+Alt+Shift+F9 on
     Windows, or choose Formulas > Calculate Now on a Mac. Do not edit any cell.
  2. File > Save As > "Excel Workbook (.xlsx)" as golden/excel_cached_200.xlsx.
  3. Note the Excel version (File > Account > About Excel).
  4. python3 tools/excel_crosscheck.py golden/excel_cached_200.xlsx --excel-version "Excel 365 16.0.x"
     It writes golden/excel_crosscheck.json, which harness.certify quotes in the certificate.
An Excel "CSV UTF-8" export of sheet Calc is also accepted, but the .xlsx route keeps full
precision without reformatting any cells.

The comparison uses the harness tolerance (numbers within 1e-6, dates and text exact, errors by
code). Numeric differences under 1e-4 are also counted separately as "display precision
suspects", since they usually mean a cell kept a number format in step 3.

Standard library plus the harness package; Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import csv
import datetime as dt
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


EXCEL_EPOCH = dt.date(1899, 12, 30)


def excel_cell(v, is_date):
    """A cached value read by openpyxl (data_only) -> harness value, matching parse_oracle_cell."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, str):
        return C.parse_oracle_cell(v.strip(), is_date)
    if isinstance(v, dt.datetime):
        return v.date() if is_date else v
    if isinstance(v, dt.date):
        return v
    if is_date and isinstance(v, (int, float)):
        return EXCEL_EPOCH + dt.timedelta(days=int(v))
    return float(v)


def read_excel_xlsx(path):
    """Sheet Calc of a workbook saved by Excel -> list of {output_name: cached value}."""
    try:
        import openpyxl  # dev dependency (requirements-dev.txt)
    except ImportError:
        raise SystemExit("openpyxl is needed: python -m pip install -r requirements-dev.txt")
    dates = set(C.date_outputs())
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if "Calc" not in wb.sheetnames:
        raise SystemExit("%s has no sheet Calc" % path)
    it = wb["Calc"].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it)]
    missing = [n for n in C.outputs() if n not in header]
    if missing:
        raise SystemExit("sheet Calc header lacks output names %s" % missing[:5])
    rows, blank_formula_cells = [], 0
    for rec in it:
        if rec is None or not any(x not in (None, "") for x in rec):
            continue
        row = {h: excel_cell(v, h in dates) for h, v in zip(header, rec) if h}
        rows.append(row)
    wb.close()
    if rows and all(v is None for r in rows for k, v in r.items() if k != "policy_id"):
        raise SystemExit("%s has no cached values: open it in Excel, recalculate and save it again" % path)
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
    ap.add_argument("excel_file", help="golden/expanded_200.xlsx recalculated and saved by Excel (.xlsx), or its sheet Calc as CSV")
    ap.add_argument("--excel-version", required=True, help='e.g. "Excel 365 16.0.18025"')
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--out", default=os.path.join(C.GOLDEN, "excel_crosscheck.json"))
    a = ap.parse_args(argv)
    oracle = C.load_oracle(a.seed)
    if oracle is None:
        raise SystemExit("golden oracle missing: run make oracle first")
    reader = read_excel_xlsx if a.excel_file.lower().endswith(".xlsx") else read_excel_csv
    excel = reader(a.excel_file)
    if len(excel) < 200:
        raise SystemExit("expected 200 policy rows in sheet Calc, found %d" % len(excel))
    res = crosscheck(excel, oracle)
    gmeta = C.read_json(C.golden_paths(a.seed)["meta"])
    doc = dict({"_about": "Excel vs the LibreOffice oracle on the first 200 golden policies (tools/excel_crosscheck.py). Written once by a person with Excel; certify quotes it.",
                "excel_version": a.excel_version, "seed": a.seed,
                "libreoffice": (gmeta.get("original") or {}).get("label"),
                "excel_file": C.rel(a.excel_file), "excel_file_sha256": C.sha256_file(a.excel_file)}, **res)
    C.write_json(a.out, doc)
    print("excel_crosscheck: %d of %d cells equal over %d rows (%d display-precision suspects) -> %s" % (
        res["cells_equal"], res["cells_compared"], res["rows"], res["display_precision_suspects"], C.rel(a.out)))
    return 0 if res["cells_equal"] == res["cells_compared"] else 1


if __name__ == "__main__":
    sys.exit(main())
