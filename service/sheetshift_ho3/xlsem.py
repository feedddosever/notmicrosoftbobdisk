"""Excel semantics helpers for SheetShift HO-3.

Helper name mapping (user-facing names → plan §10 xl_* names):
  xround          = xl_round          (ROUND via 15-sig-fig Decimal + ROUND_HALF_UP)
  xroundup        = xl_roundup        (ROUNDUP via 15-sig-fig Decimal + ROUND_UP)
  band            = xl_vlookup_approx (approximate VLOOKUP: bisect_right(keys,v)-1)
  exact           = xl_vlookup_exact  (exact VLOOKUP / MATCH: case-insensitive linear search)
  text_eq         = (Excel = semantics: case-insensitive str; blank(None) equals "" and 0)
  n0              = (blank-to-zero coercion: None → 0)
  edate           = xl_edate          (EDATE: same day m months later, clamped to EOM)
  yearfrac_basis3 = xl_yearfrac_3     (YEARFRAC basis 3: (b-a).days / 365)
  datedif_y       = xl_datedif_y      (DATEDIF "y": complete years; XLError("#NUM!") if a > b)
  iferror         = xl_iferror        (IFERROR: return alt when x is XLError)
  xmin            = MIN: ignores None args; propagates first XLError
  xmax            = MAX: ignores None args; propagates first XLError
"""

import calendar
import pathlib
from bisect import bisect_right
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

# ---------------------------------------------------------------------------
# Repo-root path (two directories above this file: service/sheetshift_ho3/xlsem.py)
# Used by covers() to build repo-relative file paths.
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# XLError
# ---------------------------------------------------------------------------

class XLError(Exception):
    """Represents an Excel error value (e.g. "#N/A", "#NUM!", "#DIV/0!")."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, XLError):
            return self.code == other.code
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.code)

    def __repr__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Traceability registry
# ---------------------------------------------------------------------------

STEPS: list = []


def covers(cell: str, output_name: str):
    """Decorator: tag a column function with its Calc cell and output name.

    Appends {"cell", "name", "fn", "file", "line"} to STEPS and returns
    the function unchanged.  ``file`` is repo-relative with forward slashes;
    ``line`` is f.__code__.co_firstlineno (the @covers line).
    """
    def decorator(f):
        abs_path = pathlib.Path(f.__code__.co_filename).resolve()
        try:
            rel = abs_path.relative_to(_REPO_ROOT)
        except ValueError:
            rel = abs_path
        STEPS.append({
            "cell": cell,
            "name": output_name,
            "fn": f.__name__,
            "file": str(rel).replace("\\", "/"),
            "line": f.__code__.co_firstlineno,
        })
        return f
    return decorator


# ---------------------------------------------------------------------------
# Internal: propagate XLError through any helper
# ---------------------------------------------------------------------------

def _propagate(*args):
    """Return the first XLError found in args, or None."""
    for a in args:
        if isinstance(a, XLError):
            return a
    return None


# ---------------------------------------------------------------------------
# Rounding helpers
# ---------------------------------------------------------------------------

def xround(x, d: int):
    """ROUND(x, d) — halves away from zero, 15-sig-fig pre-conversion."""
    err = _propagate(x)
    if err is not None:
        return err
    d_str = Decimal(10) ** (-d)
    return float(Decimal(format(float(x), ".15g")).quantize(d_str, rounding=ROUND_HALF_UP))


def xroundup(x, d: int):
    """ROUNDUP(x, d) — away from zero, 15-sig-fig pre-conversion."""
    err = _propagate(x)
    if err is not None:
        return err
    d_str = Decimal(10) ** (-d)
    return float(Decimal(format(float(x), ".15g")).quantize(d_str, rounding=ROUND_UP))


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def band(v, keys: list, vals: list):
    """Approximate VLOOKUP: largest key <= v.  Returns XLError('#N/A') if none."""
    err = _propagate(v)
    if err is not None:
        return err
    i = bisect_right(keys, v) - 1
    if i < 0:
        return XLError("#N/A")
    return vals[i]


def exact(v, keys: list, vals: list):
    """Exact VLOOKUP / MATCH lookup: case-insensitive.  Returns XLError('#N/A') on miss."""
    err = _propagate(v)
    if err is not None:
        return err
    v_lo = v.lower() if isinstance(v, str) else v
    for k, val in zip(keys, vals):
        k_cmp = k.lower() if isinstance(k, str) else k
        if k_cmp == v_lo:
            return val
    return XLError("#N/A")


def text_eq(a, b) -> bool:
    """Excel = semantics.

    - XLError argument: return the error unchanged (not a bool).
    - Both str: case-insensitive comparison.
    - blank (None) equals "" and equals 0; blank does NOT equal "Y".
    - Otherwise: standard Python equality.
    """
    err = _propagate(a, b)
    if err is not None:
        return err
    # blank (None) equals "" and equals 0 (§20 Blanks)
    # Normalise: treat None as equivalent to both 0 and "".
    if a is None and (b == "" or b == 0):
        return True
    if b is None and (a == "" or a == 0):
        return True
    if a is None or b is None:
        return False
    if isinstance(a, str) and isinstance(b, str):
        return a.lower() == b.lower()
    return a == b


# ---------------------------------------------------------------------------
# Blank coercion
# ---------------------------------------------------------------------------

def n0(x):
    """Blank (None) → 0; any other value unchanged.  Propagates XLError."""
    if isinstance(x, XLError):
        return x
    return 0 if x is None else x


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def edate(d, m: int):
    """EDATE(d, m): same calendar day m months later, clamped to end-of-month.
    Returns an XLError argument unchanged."""
    import datetime
    if isinstance(d, XLError):
        return d
    month = d.month + m
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def yearfrac_basis3(a, b):
    """YEARFRAC(a, b, 3) = (b - a).days / 365."""
    err = _propagate(a, b)
    if err is not None:
        return err
    return (b - a).days / 365


def datedif_y(a, b):
    """DATEDIF(a, b, "y"): complete years from a to b.  XLError('#NUM!') if a > b."""
    err = _propagate(a, b)
    if err is not None:
        return err
    if a > b:
        return XLError("#NUM!")
    years = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        years -= 1
    return years


# ---------------------------------------------------------------------------
# MIN / MAX
# ---------------------------------------------------------------------------

def xmin(*args):
    """MIN(*args): ignore None arguments; return first XLError unchanged."""
    err = _propagate(*args)
    if err is not None:
        return err
    filtered = [a for a in args if a is not None]
    return min(filtered)


def xmax(*args):
    """MAX(*args): ignore None arguments; return first XLError unchanged."""
    err = _propagate(*args)
    if err is not None:
        return err
    filtered = [a for a in args if a is not None]
    return max(filtered)


# ---------------------------------------------------------------------------
# Error trap
# ---------------------------------------------------------------------------

def iferror(x, alt):
    """IFERROR(x, alt): return alt when x is XLError, else x."""
    if isinstance(x, XLError):
        return alt
    return x
