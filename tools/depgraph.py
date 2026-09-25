"""Formula dependency graph and spreadsheet-anomaly lints for row-based workbooks.

Works at column level so it scales to large row-based books:
  1. every formula is normalised to an R1C1 template (string literals skipped);
  2. a column with >= 10 formula cells where >= 90% share one template is "row-based":
     the majority template is the column rule; minority templates become
     `inconsistent_formula` lints and stray constants inside the formula rows become
     `hardcoded_value_in_formula_column` lints. Other formula cells are one node each;
  3. one representative per (node, template) is tokenised with openpyxl's Tokenizer
     for functions, precedents and defined names;
  4. absolute multi-row ranges are checked against the contiguous table block they
     start in -> `range_short_of_table` lint when the range stops short of the block;
  5. a node-level DAG and a deterministic topological order (sheet, column, row priority).
Also scans for constructs outside the supported subset (volatile functions, macros,
external links, array/data-table formulas, iterative calculation).

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import heapq
import re
import zipfile
from collections import Counter, defaultdict

import openpyxl
from openpyxl.formula import Tokenizer
from openpyxl.utils import column_index_from_string, get_column_letter, range_boundaries

MIN_ROW_BASED_CELLS = 10       # a column needs this many formula cells to be row-based ...
MIN_TEMPLATE_SHARE = 0.90      # ... and this share of them on one template
MAX_CONST_SHARE = 0.10         # constants in a formula column above this share are data, not lints
VOLATILE = {"NOW", "TODAY", "RAND", "RANDBETWEEN", "RANDARRAY", "OFFSET", "INDIRECT", "CELL", "INFO"}

REF = re.compile(r"(?<![A-Za-z_.$])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![\w(])")
R1C1_REF = re.compile(r"R(\[-?\d+\]|\d+)C(\[-?\d+\]|\d+)")
SHEET_REF = re.compile(r"^(?:'?([^'!]+)'?!)?(.+)$")


def _outside_strings(formula, fn):
    """Apply fn to the parts of `formula` that are outside double-quoted string literals."""
    parts = formula.split('"')
    for k in range(0, len(parts), 2):
        parts[k] = fn(parts[k])
    return '"'.join(parts)


def r1c1(formula, row, col):
    """A1 formula at (row, col) -> R1C1 template; equal templates mean the same rule."""
    def sub(m):
        ca, cl, ra, rw = m.groups()
        c, r = column_index_from_string(cl), int(rw)
        return (f"R{r}" if ra else f"R[{r - row}]") + (f"C{c}" if ca else f"C[{c - col}]")
    return _outside_strings(formula, lambda s: REF.sub(sub, s))


def a1(template, row, col):
    """Inverse of r1c1: render an R1C1 template as an A1 formula at (row, col)."""
    def sub(m):
        rs, cs = m.groups()
        r = row + int(rs[1:-1]) if rs.startswith("[") else int(rs)
        c = col + int(cs[1:-1]) if cs.startswith("[") else int(cs)
        return (f"{get_column_letter(c)}" if cs.startswith("[") else f"${get_column_letter(c)}") + \
               (f"{r}" if rs.startswith("[") else f"${r}")
    return _outside_strings(template, lambda s: R1C1_REF.sub(sub, s))


def tokens(formula):
    """-> (function names in order, range/reference operands) via openpyxl's Tokenizer."""
    funcs, operands = [], []
    for t in Tokenizer(formula).items:
        if t.type == "FUNC" and t.subtype == "OPEN":
            funcs.append(t.value[:-1].upper())
        elif t.type == "OPERAND" and t.subtype == "RANGE":
            operands.append(t.value)
    return funcs, operands


def resolve(operand, host_sheet, names):
    """-> (kind 'name'|'abs'|'rel', sheet, (min_col, min_row, max_col, max_row), name_or_None)."""
    if operand in names:
        m = SHEET_REF.match(names[operand])
        return "name", m.group(1) or host_sheet, range_boundaries(m.group(2).replace("$", "")), operand
    m = SHEET_REF.match(operand)
    sheet, ref = m.group(1) or host_sheet, m.group(2)
    return ("abs" if "$" in ref else "rel"), sheet, range_boundaries(ref.replace("$", "")), None


def table_block_end(ws, col, row):
    """Last row of the contiguous non-empty block going down from (col, row)."""
    r = row
    while ws.cell(r + 1, col).value not in (None, ""):
        r += 1
    return r


def _ref(sheet, c1, r1, c2, r2):
    if (c1, r1) == (c2, r2):
        return f"{sheet}!{get_column_letter(c1)}{r1}"
    return f"{sheet}!{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}"


def _scan_unsupported(path, wb):
    """Constructs outside the supported subset (reported, never silently translated)."""
    found = []
    with zipfile.ZipFile(path) as z:
        members = z.namelist()
    if any(m.lower().endswith("vbaproject.bin") for m in members):
        found.append({"kind": "macros", "detail": "VBA project present; macros are not supported"})
    if any(m.startswith("xl/externalLinks/") for m in members):
        found.append({"kind": "external_links", "detail": "external workbook links are out of scope"})
    calc = getattr(wb, "calculation", None)
    if calc is not None and getattr(calc, "iterate", False):
        found.append({"kind": "iterative_calculation", "detail": "iterative calculation is enabled"})
    return found


def analyze(path):
    """Build the node graph, lints and unsupported-construct scan for the workbook at `path`."""
    wb = openpyxl.load_workbook(path)            # formulas, not values
    names = {n: d.attr_text for n, d in wb.defined_names.items()}
    nodes, lints = [], []
    unsupported = _scan_unsupported(path, wb)
    sheet_index = {ws.title: i for i, ws in enumerate(wb.worksheets)}
    for ws in wb.worksheets:
        by_col = defaultdict(lambda: defaultdict(list))   # col letter -> template -> [rows]
        consts = defaultdict(list)                        # col letter -> [(row, value)]
        for row in ws.iter_rows(min_row=2):
            for c in row:
                v = c.value
                if isinstance(v, str) and v.startswith("="):
                    by_col[c.column_letter][r1c1(v, c.row, c.column)].append(c.row)
                elif v is not None and not isinstance(v, (str, int, float, bool)) and \
                        not hasattr(v, "year"):
                    unsupported.append({"kind": "array_or_data_table_formula",
                                        "detail": f"{ws.title}!{c.coordinate}: {type(v).__name__}"})
                elif v is not None:
                    consts[c.column_letter].append((c.row, v))
        for col in sorted(by_col, key=column_index_from_string):
            groups = by_col[col]
            total = sum(len(v) for v in groups.values())
            major_t, major_rows = max(groups.items(), key=lambda kv: (len(kv[1]), -min(kv[1])))
            if total >= MIN_ROW_BASED_CELLS and len(major_rows) / total >= MIN_TEMPLATE_SHARE:
                node_groups = [(f"{ws.title}!{col}", "column", groups)]
            else:
                node_groups = [(f"{ws.title}!{col}{r}", "cell", {t: [r]})
                               for t, rows in groups.items() for r in rows]
            for key, kind, g in node_groups:
                nodes.append(_node(wb, ws, col, key, kind, g, names, lints, unsupported))
            if node_groups[0][1] == "column":
                _column_lints(ws, col, groups, major_t, consts.get(col, []), total, lints, nodes[-1])
    _add_topo(nodes, sheet_index)
    return {"names": names, "nodes": nodes, "lints": lints, "unsupported": unsupported,
            "sheets": [ws.title for ws in wb.worksheets]}


def _node(wb, ws, col, key, kind, groups, names, lints, unsupported):
    """Describe one node (a row-based column or a single cell) from its majority template."""
    total = sum(len(v) for v in groups.values())
    major_t, major_rows = max(groups.items(), key=lambda kv: (len(kv[1]), -min(kv[1])))
    rep_row = min(major_rows)
    rep = ws[f"{col}{rep_row}"].value
    funcs, ops = tokens(rep)
    for t in groups:                               # volatile functions in any template
        for f in tokens(a1(t, rep_row, column_index_from_string(col)))[0]:
            if f in VOLATILE:
                unsupported.append({"kind": "volatile_function", "detail": f"{key}: {f}"})
    prec_cols, prec_cells, tables, used_names = set(), set(), [], set()
    for op in ops:
        kind_, sh, (c1, r1, c2, r2), nm = resolve(op, ws.title, names)
        if nm:
            used_names.add(nm)
        if kind_ == "rel":                         # row-relative -> column dependency
            for ci in range(c1, c2 + 1):
                prec_cols.add((sh, get_column_letter(ci)))
            if kind == "cell" and r1 == r2:
                prec_cells.add(f"{sh}!{get_column_letter(c1)}{r1}")
            continue
        ref = _ref(sh, c1, r1, c2, r2)
        entry = {"operand": op, "ref": ref, "name": nm}
        if entry not in tables:
            tables.append(entry)
        if kind_ == "abs" and r2 > r1:             # literal range vs the table block it starts in
            end = table_block_end(wb[sh], c1, r1)
            if end > r2:
                covering = sorted(n for n in names
                                  if resolve(n, sh, names)[2][:2] == (c1, r1))
                missing_keys = [wb[sh].cell(r, c1).value for r in range(r2 + 1, end + 1)]
                lints.append({"type": "range_short_of_table", "node": key, "rows": major_rows,
                              "range": op, "table_block": _ref(sh, c1, r1, c2, end),
                              "rows_missing": end - r2, "missing_keys": missing_keys,
                              "named_ranges_covering_block": covering})
    return {"key": key, "sheet": ws.title, "col": col, "kind": kind,
            "template_r1c1": major_t, "formula_a1": rep, "example_row": rep_row,
            "rows": [min(major_rows), max(major_rows)], "n_cells": total,
            "functions": sorted(set(funcs)), "function_calls": funcs,
            "precedent_columns": sorted(prec_cols, key=lambda sc: (sc[0], column_index_from_string(sc[1]))),
            "tables": tables, "names": sorted(used_names),
            "exceptions": []}


def _column_lints(ws, col, groups, major_t, consts, total, lints, node):
    """Inconsistent formulas and typed-over constants inside a row-based column."""
    lo, hi = node["rows"][0], node["rows"][1]
    for t, rows in groups.items():
        if t == major_t:
            continue
        for r in rows:
            lo, hi = min(lo, r), max(hi, r)
            lints.append({"type": "inconsistent_formula", "node": node["key"], "row": r,
                          "formula": ws[f"{col}{r}"].value, "template_r1c1": t})
            node["exceptions"].append(f"{node['key']}{r}")
    inside = [(r, v) for r, v in consts if lo <= r <= hi]
    if inside and len(inside) <= MAX_CONST_SHARE * total:
        for r, v in inside:
            lints.append({"type": "hardcoded_value_in_formula_column", "node": node["key"],
                          "row": r, "value": v})
            node["exceptions"].append(f"{node['key']}{r}")
    node["exceptions"].sort(key=lambda k: int(re.search(r"(\d+)$", k).group(1)))


def _add_topo(nodes, sheet_index):
    """Deterministic Kahn topological order; ties broken by (sheet, column, row)."""
    by_key = {n["key"]: n for n in nodes}
    col_nodes = {(n["sheet"], n["col"]): n["key"] for n in nodes if n["kind"] == "column"}
    deps = {}
    for n in nodes:
        deps[n["key"]] = sorted({col_nodes[sc] for sc in n["precedent_columns"]
                                 if sc in col_nodes and col_nodes[sc] != n["key"]},
                                key=lambda k: (sheet_index[by_key[k]["sheet"]],
                                               column_index_from_string(by_key[k]["col"])))
        n["precedent_nodes"] = deps[n["key"]]

    def prio(k):
        n = by_key[k]
        row = int(re.search(r"(\d+)$", k).group(1)) if n["kind"] == "cell" else 0
        return (sheet_index[n["sheet"]], column_index_from_string(n["col"]), row)

    indeg = {k: len(v) for k, v in deps.items()}
    rev = defaultdict(list)
    for k, v in deps.items():
        for p in v:
            rev[p].append(k)
    heap = [(prio(k), k) for k, d in indeg.items() if d == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        _, k = heapq.heappop(heap)
        order.append(k)
        for nxt in rev[k]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(heap, (prio(nxt), nxt))
    if len(order) != len(nodes):
        raise ValueError("circular references between formula columns are not supported")
    for i, k in enumerate(order):
        by_key[k]["topo_index"] = i


def function_inventory(nodes):
    """Call counts per function across distinct rules (one count per call in the rule)."""
    return dict(sorted(Counter(f for n in nodes for f in n["function_calls"]).items(),
                       key=lambda kv: (-kv[1], kv[0])))
