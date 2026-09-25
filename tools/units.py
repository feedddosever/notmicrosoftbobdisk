"""Translation units: split the Calc columns into contiguous topological units and render
one self-contained brief per unit (build/units/U<k>.md) with sample rows from the oracle.

A unit is a contiguous run of columns in topological order, so every column reads only
policy inputs (`p`), columns earlier in its own unit, or outputs of earlier units (`c`).

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import datetime as dt

ERROR_CODES = {"#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!"}
UNIT_MD_LIMIT = 5000
N_SAMPLES = 5


def is_error(v):
    return isinstance(v, str) and (v in ERROR_CODES or v.startswith("Err:"))


def split(order, n_units, target_starts=None, slack=3):
    """Split the topological column order into n_units contiguous runs.

    Uses target_starts (first column of each unit) when it is valid for this order and
    each unit is within `slack` columns of an even share; otherwise balances by count.
    """
    n = len(order)
    if target_starts and len(target_starts) == n_units and target_starts[0] == order[0] \
            and all(s in order for s in target_starts):
        idx = [order.index(s) for s in target_starts] + [n]
        if idx == sorted(idx) and len(set(idx)) == len(idx):
            sizes = [b - a for a, b in zip(idx, idx[1:])]
            if all(abs(s - n / n_units) <= slack for s in sizes):
                return [order[a:b] for a, b in zip(idx, idx[1:])]
    base, extra = divmod(n, n_units)
    out, i = [], 0
    for k in range(n_units):
        size = base + (1 if k < extra else 0)
        out.append(order[i:i + size])
        i += size
    return out


def describe(parts, columns, input_order):
    """-> {U1: {columns, outputs, inputs, upstream, cells}} from the split and column info."""
    units, owner = {}, {}
    for k, cols in enumerate(parts, 1):
        for col in cols:
            owner[col] = f"U{k}"
    by_col = {c["col"]: c for c in columns}
    for k, cols in enumerate(parts, 1):
        uid = f"U{k}"
        reads_in, reads_up = set(), []
        for col in cols:
            reads_in.update(by_col[col]["inputs"])
            for pc in by_col[col]["precedent_cols"]:
                if owner[pc] != uid:
                    assert int(owner[pc][1:]) < k, f"{col} reads a later unit"
                    if by_col[pc]["output_name"] not in reads_up:
                        reads_up.append(by_col[pc]["output_name"])
        up_order = [c["output_name"] for c in columns if c["output_name"] in reads_up]
        units[uid] = {
            "columns": list(cols),
            "outputs": [by_col[c]["output_name"] for c in cols],
            "inputs": [i for i in input_order if i in reads_in],
            "upstream": up_order,
            "cells": [by_col[c]["cell"] for c in cols],
            "range": f"Calc!{cols[0]}:{cols[-1]}",
        }
    return units


def fmt(v):
    """Render a cell value for the unit briefs (errors bare, text quoted, dates ISO)."""
    if v is None:
        return "blank"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (dt.date, dt.datetime)):
        return (v.date() if isinstance(v, dt.datetime) else v).isoformat()
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, int):
        return str(v)
    if is_error(v):
        return v
    return f'"{v}"'


def choose_samples(unit, rows, excluded, n=N_SAMPLES):
    """Pick n sheet rows that together show the most distinct behaviour for this unit.

    rows: {sheet_row: {"p": inputs, "c": oracle outputs}}. Rows touched by a lint are
    excluded. One error row is included when the unit has one (errors propagate).
    Greedy on features (blank inputs, case variants, low-cardinality values); ties -> lower row.
    """
    cand = [r for r in sorted(rows) if r not in excluded]
    fields = [("p", f) for f in unit["inputs"]] + [("c", f) for f in unit["outputs"]]
    distinct = {fld: len({fmt(rows[r][fld[0]].get(fld[1])) for r in cand}) for fld in fields}

    def feats(r):
        out = set()
        for src, f in fields:
            v = rows[r][src].get(f)
            if v is None or is_error(v):
                out.add((f, fmt(v)))
            elif isinstance(v, str) and src == "p" and v[:1].islower():
                out.add((f, "case"))      # lower-case variant (text compare is case-insensitive)
            if distinct[(src, f)] <= 12:
                out.add((f, fmt(v)))
        return out

    chosen, seen = [], set()
    err = [r for r in cand if any(is_error(rows[r]["c"].get(o)) for o in unit["outputs"])]
    if err:
        chosen.append(err[0])
        seen |= feats(err[0])
    while len(chosen) < min(n, len(cand)):
        best = max((r for r in cand if r not in chosen), key=lambda r: (len(feats(r) - seen), -r))
        chosen.append(best)
        seen |= feats(best)
    return sorted(chosen)


def render_md(uid, unit, columns, layout, names, lints, rows, samples, engine):
    """The self-contained brief a translator (person or agent) needs for one unit."""
    by_col = {c["col"]: c for c in columns}
    in_col = dict(zip(layout["inputs"], layout["input_columns"]))
    first, last = layout["first_data_row"], layout["last_data_row"]
    L = [f"# {uid}: Calc!{unit['columns'][0]}..{unit['columns'][-1]} ({len(unit['columns'])} columns)",
         "",
         f"{layout['carrier']}: synthetic workbook. Generated by tools/dump_workbook.py; do not edit.",
         "",
         f"One function per column, `c_<col>_<output_name>(p, c)`, tagged "
         f"`@covers(\"Calc!<col>\", \"<output_name>\")`. `p` = policy inputs; `c` = outputs so far. "
         f"Rows {first}..{last} all use the rule shown for row {first} (formula refs are row {first}).",
         "",
         "Reads p: " + (", ".join(f"{i} ({in_col[i]})" for i in unit["inputs"]) or "none"),
         "Reads c from earlier units: " + (", ".join(unit["upstream"]) or "none"),
         ""]
    used = sorted({nm for c in unit["columns"] for nm in by_col[c]["named_ranges"]})
    literal = sorted({t["operand"] for c in unit["columns"] for t in by_col[c]["tables"] if not t["name"]})
    if used or literal:
        L.append("Tables (values in build/rate_tables.json): " +
                 "; ".join([f"{nm} = {names[nm]}" for nm in used] + literal))
        L.append("")
    L += ["| Col | output_name | Rule (row %d) | Rule ref |" % first, "|---|---|---|---|"]
    for col in unit["columns"]:
        c = by_col[col]
        L.append(f"| {col} | {c['output_name']} | `{c['template_a1']}` | {c['manual_rule'] or '-'} |")
    mine = [l for l in lints if l["column"] in unit["columns"]]
    if mine:
        L += ["", "Open lints (awaiting a signed human decision; details in build/sheets/Calc_exceptions.md):"]
        for l in mine:
            what = f"`{l['formula']}` vs rule `{l['column_rule']}`" if l["type"] != "range_short_of_table" \
                else f"range {l['range']} stops {l['rows_missing']} row(s) short of {l['table_block']}"
            L.append(f"- {l['id']} {l['type']} at {l['cell']}: {what} ({l['manual_rule']})")
    L += ["", f"Sample rows: expected values from {engine}, forced recalculation of the workbook. "
          "Rows touched by a lint are left out. Errors are shown bare (#N/A); text is quoted.", ""]
    L.append("| src | field | " + " | ".join(f"row {r}" for r in samples) + " |")
    L.append("|---|---|" + "---|" * len(samples))
    L.append("| p | policy_id | " + " | ".join(fmt(rows[r]["p"]["policy_id"]) for r in samples) + " |")
    for src, fields in (("p", [f for f in unit["inputs"] if f != "policy_id"]),
                        ("c", unit["upstream"]), ("out", unit["outputs"])):
        key = "p" if src == "p" else "c"
        for f in fields:
            L.append(f"| {src} | {f} | " + " | ".join(fmt(rows[r][key].get(f)) for r in samples) + " |")
    return "\n".join(L) + "\n"


def check_size(text, limit=UNIT_MD_LIMIT):
    """True when a brief fits the size budget (CI asserts the same limit)."""
    return len(text) < limit
