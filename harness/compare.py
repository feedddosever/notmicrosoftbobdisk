"""Cell-by-cell comparison of service outputs with the oracle, under a fixed tolerance.

usage: python -m harness.compare [--seed 2026] [--service MODULE] [--patched]
       (prints a JSON summary; harness.run writes the reports)

TOLERANCE is a constant in a protected file (plan section 6.3). Changing it takes a human
commit with the reason recorded in PROVENANCE.md.

Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import json
import numbers
import sys

from harness import common as C

NUMBER_ABS_TOL = 1e-6
TOLERANCE = {
    "numbers": "absolute difference <= 1e-6",
    "dates": "exact",
    "text": "exact and case-sensitive",
    "errors": "same error code",
    "blank_zero_empty": "blank, 0 and \"\" are different",
}
MISSING = object()          # the service dict lacks this output name
EXCEPTION = "__exception__"  # key call_quote() uses for a crashed quote


def diff_kind(o, s):
    """None if oracle value `o` and service value `s` are equal under TOLERANCE, else a kind.

    Kinds: missing, error_code, error_vs_value (oracle error, service value),
    value_vs_error, blank, date, numeric, text, text_case, type.
    """
    if s is MISSING:
        return "missing"
    ocode = o.code if isinstance(o, C.ErrorValue) else None
    scode = C.service_error_code(s)
    if ocode or scode:
        if ocode and scode:
            return None if ocode == scode else "error_code"
        return "error_vs_value" if ocode else "value_vs_error"
    if o is None or s is None:
        return None if (o is None and s is None) else "blank"
    if isinstance(o, dt.date):
        if isinstance(s, dt.datetime):
            s = s.date()
        if not isinstance(s, dt.date):
            return "type"
        return None if s == o else "date"
    if isinstance(o, float):
        if isinstance(s, bool) or not isinstance(s, numbers.Number):
            return "type"
        try:
            d = abs(float(s) - o)
        except (TypeError, ValueError, OverflowError):
            return "type"
        return None if d <= NUMBER_ABS_TOL else "numeric"
    if isinstance(o, str):
        if not isinstance(s, str):
            return "type"
        if s == o:
            return None
        return "text_case" if s.casefold() == o.casefold() else "text"
    return "type"


def same(o, s):
    return diff_kind(o, s) is None


def compare_row(orow, srow, names):
    """{output_name: kind} for the mismatching cells of one row."""
    if EXCEPTION in srow:
        return {n: "exception" for n in names}
    out = {}
    for n in names:
        k = diff_kind(orow.get(n), srow.get(n, MISSING))
        if k:
            out[n] = k
    return out


def compare(oracle_rows, service_rows, names=None, rows=None):
    """Returns {row_index: {output_name: kind}} over `rows` (default: all rows)."""
    names = names or C.outputs()
    idx = range(len(oracle_rows)) if rows is None else rows
    mism = {}
    for i in idx:
        m = compare_row(oracle_rows[i], service_rows[i], names)
        if m:
            mism[i] = m
    return mism


def summarize(mism, n_rows, names=None):
    names = names or C.outputs()
    cells = n_rows * len(names)
    bad = sum(len(v) for v in mism.values())
    return {"rows": n_rows, "cells_compared": cells, "cells_equal": cells - bad,
            "mismatched_cells": bad, "rows_fully_equal": n_rows - len(mism)}


def run_service(quote, policies):
    return [C.call_quote(quote, p) for p in policies]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare the service with the golden oracle")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    ap.add_argument("--patched", action="store_true")
    a = ap.parse_args(argv)
    _, policies = C.load_inputs(a.seed)
    oracle = C.load_oracle(a.seed, patched=a.patched)
    if oracle is None:
        print(json.dumps({"status": "no_oracle", "patched": a.patched}))
        return 1
    try:
        mod = C.import_service(a.service)
    except C.ServiceMissing as e:
        print(json.dumps({"status": "pending", "missing": str(e)}))
        return 0
    mism = compare(oracle, run_service(mod.quote, policies))
    out = summarize(mism, len(policies))
    out["tolerance"] = TOLERANCE
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
