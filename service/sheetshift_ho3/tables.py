"""Rate table accessor for SheetShift HO-3.

Loads service/sheetshift_ho3/data/rate_tables.json once at import time.
API (docs/CONTRACT.md section 4):
  table(key)   -> {"ref", "header", "rows"}
  rows(ref)    -> list of row lists for any rectangular sub-range inside one table
  column(ref)  -> list of values for a one-column range
  scalar(name) -> scalar value (CreditCap, MinPremium, AssessRate, HurrCapPct)
"""

import json
import pathlib
import re

_DATA_FILE = pathlib.Path(__file__).parent / "data" / "rate_tables.json"

with _DATA_FILE.open(encoding="utf-8") as _fh:
    _DB = json.load(_fh)

_TABLES: dict = _DB["tables"]
_SCALARS: dict = _DB["scalars"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def table(key: str) -> dict:
    """Return {"ref", "header", "rows"} for the given table key.

    key is either a defined name (e.g. "BaseRates") or a literal ref
    (e.g. "RateTables!$A$13:$C$16"), exactly as it appears in the JSON
    "tables" object.
    """
    return _TABLES[key]


def rows(ref: str) -> list:
    """Return row lists for any rectangular range inside one table.

    ref must be a RateTables absolute ref such as 'RateTables!$A$31:$B$35'.
    The range is resolved by intersecting it with each table's ref.
    """
    sheet_r, r_start, c_start, r_end, c_end = _parse_ref(ref)
    for tbl in _TABLES.values():
        sheet_t, t_r1, t_c1, t_r2, t_c2 = _parse_ref(tbl["ref"])
        if sheet_r != sheet_t:
            continue
        # Check that the requested range is contained within this table
        if t_r1 <= r_start and r_end <= t_r2 and t_c1 <= c_start and c_end <= t_c2:
            # Row offset inside the table
            row_off = r_start - t_r1
            row_cnt = r_end - r_start + 1
            col_off = c_start - t_c1
            col_cnt = c_end - c_start + 1
            result = []
            for row in tbl["rows"][row_off: row_off + row_cnt]:
                result.append(row[col_off: col_off + col_cnt])
            return result
    raise KeyError(f"Ref {ref!r} is not contained in any known table")


def column(ref: str) -> list:
    """Return a flat list of values for a one-column range.

    ref must be a single-column RateTables absolute ref such as
    'RateTables!$B$13:$B$16'.
    """
    return [row[0] for row in rows(ref)]


def scalar(name: str):
    """Return the scalar value for a defined name such as 'MinPremium'."""
    return _SCALARS[name]


# ---------------------------------------------------------------------------
# Internal: parse an absolute RateTables ref into (sheet, r1, c1, r2, c2)
# All row/col indices are 1-based integers.
# ---------------------------------------------------------------------------

_REF_RE = re.compile(
    r"^(.+?)!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)$",
    re.IGNORECASE,
)


def _col_num(letters: str) -> int:
    """Convert column letters (A, B, ..., Z, AA, ...) to a 1-based integer."""
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _parse_ref(ref: str):
    """Return (sheet, r1, c1, r2, c2) from an absolute ref like 'RateTables!$A$3:$D$10'."""
    m = _REF_RE.match(ref)
    if not m:
        raise ValueError(f"Cannot parse ref: {ref!r}")
    sheet, c1_str, r1_str, c2_str, r2_str = m.groups()
    return (
        sheet.upper(),
        int(r1_str),
        _col_num(c1_str),
        int(r2_str),
        _col_num(c2_str),
    )
