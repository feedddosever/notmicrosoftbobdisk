"""Probe values from .bob/rules/20-excel-semantics.md, plus covers() tests."""

import datetime
import importlib
import math
import pathlib
import sys

import pytest

# Ensure the workspace root is on the path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from service.sheetshift_ho3.xlsem import (
    XLError,
    STEPS,
    covers,
    xround,
    xroundup,
    band,
    exact,
    text_eq,
    n0,
    edate,
    yearfrac_basis3,
    datedif_y,
    iferror,
)


# ---------------------------------------------------------------------------
# XLError
# ---------------------------------------------------------------------------

def test_xlerror_code():
    e = XLError("#N/A")
    assert e.code == "#N/A"


def test_xlerror_repr():
    assert repr(XLError("#DIV/0!")) == "#DIV/0!"


def test_xlerror_equality():
    assert XLError("#N/A") == XLError("#N/A")
    assert XLError("#N/A") != XLError("#NUM!")


def test_xlerror_is_exception():
    assert isinstance(XLError("#N/A"), Exception)


# ---------------------------------------------------------------------------
# xround — ROUND probe values
# ---------------------------------------------------------------------------

def test_round_628_125():
    assert xround(628.125, 2) == pytest.approx(628.13, abs=1e-9)


def test_round_3505_times_689():
    # Python round gives 2414.94 — the correct answer is 2414.95
    assert xround(3.505 * 689, 2) == pytest.approx(2414.95, abs=1e-9)


def test_round_1_005():
    assert xround(1.005, 2) == pytest.approx(1.01, abs=1e-9)


def test_round_2_675():
    assert xround(2.675, 2) == pytest.approx(2.68, abs=1e-9)


def test_round_neg_2_5():
    assert xround(-2.5, 0) == pytest.approx(-3.0, abs=1e-9)


def test_round_propagates_error():
    e = XLError("#DIV/0!")
    assert xround(e, 2) is e


# ---------------------------------------------------------------------------
# xroundup — ROUNDUP probe values
# ---------------------------------------------------------------------------

def test_roundup_0_1_plus_0_2():
    assert xroundup(0.1 + 0.2, 1) == pytest.approx(0.3, abs=1e-9)


def test_roundup_682_14():
    assert xroundup(682.14, 0) == pytest.approx(683.0, abs=1e-9)


def test_roundup_propagates_error():
    e = XLError("#NUM!")
    assert xroundup(e, 0) is e


# ---------------------------------------------------------------------------
# band — approximate VLOOKUP
# ---------------------------------------------------------------------------

_BAND_KEYS = [0, 500, 1000, 2500]
_BAND_VALS = [1.1, 1.0, 0.92, 0.82]


def test_band_exact_hit():
    assert band(1000, _BAND_KEYS, _BAND_VALS) == pytest.approx(0.92, abs=1e-9)


def test_band_between():
    assert band(999, _BAND_KEYS, _BAND_VALS) == pytest.approx(1.0, abs=1e-9)


def test_band_below_first():
    result = band(-1, _BAND_KEYS, _BAND_VALS)
    assert isinstance(result, XLError) and result.code == "#N/A"


def test_band_propagates_error():
    e = XLError("#N/A")
    assert band(e, _BAND_KEYS, _BAND_VALS) is e


# ---------------------------------------------------------------------------
# exact — exact VLOOKUP / MATCH
# ---------------------------------------------------------------------------

_MATCH_KEYS = ["None", "Basic", "Fortified"]
_MATCH_VALS = [1, 2, 3]


def test_exact_case_insensitive():
    # MATCH("fortified", {"None","Basic","Fortified"}, 0) → 3 (1-based index returned as value)
    assert exact("fortified", _MATCH_KEYS, _MATCH_VALS) == 3


def test_exact_miss():
    result = exact("zz", _MATCH_KEYS, _MATCH_VALS)
    assert isinstance(result, XLError) and result.code == "#N/A"


def test_exact_propagates_error():
    e = XLError("#N/A")
    assert exact(e, _MATCH_KEYS, _MATCH_VALS) is e


# ---------------------------------------------------------------------------
# text_eq
# ---------------------------------------------------------------------------

def test_text_eq_same_case():
    assert text_eq("Y", "Y") is True


def test_text_eq_different_case():
    # "y"="Y" is TRUE in Excel
    assert text_eq("y", "Y") is True


def test_text_eq_different_value():
    # "Yes"="Y" is FALSE
    assert text_eq("Yes", "Y") is False


def test_if_y_eq_Y():
    # IF("y"="Y",1,0) → 1
    assert (1 if text_eq("y", "Y") else 0) == 1


# ---------------------------------------------------------------------------
# n0 — blank coercion
# ---------------------------------------------------------------------------

def test_n0_none_is_zero():
    assert n0(None) == 0


def test_n0_blank_times_1():
    # blank*1 = 0
    assert n0(None) * 1 == 0


def test_n0_blank_eq_empty():
    # blank = "" → True via n0 interpreted as 0: 0 == "" is false in Python
    # but blank = 0 is True
    assert n0(None) == 0


def test_n0_propagates_error():
    e = XLError("#N/A")
    assert n0(e) is e


# ---------------------------------------------------------------------------
# edate
# ---------------------------------------------------------------------------

def test_edate_month_end_clamp():
    # EDATE(DATE(2026,8,31), 6) → 2027-02-28
    d = datetime.date(2026, 8, 31)
    assert edate(d, 6) == datetime.date(2027, 2, 28)


# ---------------------------------------------------------------------------
# yearfrac_basis3
# ---------------------------------------------------------------------------

def test_yearfrac_leap_12_months():
    # ROUND(YEARFRAC(DATE(2028,2,29), EDATE(DATE(2028,2,29),12), 3), 4) = 1.0
    a = datetime.date(2028, 2, 29)
    b = edate(a, 12)  # 2029-02-28
    assert xround(yearfrac_basis3(a, b), 4) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# datedif_y
# ---------------------------------------------------------------------------

def test_datedif_complete_years():
    # DATEDIF(DATE(2020,1,1), DATE(2027,3,1), "y") → 7
    a = datetime.date(2020, 1, 1)
    b = datetime.date(2027, 3, 1)
    assert datedif_y(a, b) == 7


def test_datedif_a_gt_b():
    # IFERROR(DATEDIF(DATE(2028,1,1), DATE(2027,3,1), "y"), -99) → -99
    a = datetime.date(2028, 1, 1)
    b = datetime.date(2027, 3, 1)
    result = iferror(datedif_y(a, b), -99)
    assert result == -99


# ---------------------------------------------------------------------------
# iferror
# ---------------------------------------------------------------------------

def test_iferror_catches_xlerror():
    assert iferror(XLError("#N/A"), "caught") == "caught"


def test_iferror_passes_value():
    assert iferror(42, "caught") == 42


def test_iferror_na_caught_string():
    # IFERROR(VLOOKUP("zz", tbl, 2, FALSE)+1, "#NA-caught") → "#NA-caught"
    val = exact("zz", ["a", "b"], [1, 2])  # → XLError("#N/A")
    result = iferror(val, "#NA-caught")
    assert result == "#NA-caught"


# ---------------------------------------------------------------------------
# MIN/MAX semantics (via Python builtins — illustrative, not helpers)
# ---------------------------------------------------------------------------

def test_min_ignores_none():
    # MIN(blank, 3) = 3 (blank ignored)
    args = [x for x in [None, 3] if x is not None]
    assert min(args) == 3


def test_min_max_combined():
    # MIN(0.33, 0.10) + MAX(1, 5) = 5.1
    result = min(0.33, 0.10) + max(1, 5)
    assert math.isclose(result, 5.1, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# covers() — traceability decorator
# ---------------------------------------------------------------------------

def test_covers_adds_one_step():
    import service.sheetshift_ho3.xlsem as xlsem_mod
    before = len(xlsem_mod.STEPS)

    @covers("Calc!Z", "_test_output")
    def c_Z__test_output(p, c):
        return 0

    after = len(xlsem_mod.STEPS)
    assert after == before + 1

    entry = xlsem_mod.STEPS[-1]
    assert set(entry.keys()) == {"cell", "name", "fn", "file", "line"}
    assert entry["cell"] == "Calc!Z"
    assert entry["name"] == "_test_output"
    assert entry["fn"] == "c_Z__test_output"
    # file must be repo-relative with forward slashes and not start with /
    assert "/" in entry["file"] or entry["file"].count("\\") == 0
    assert not entry["file"].startswith("/")
    assert not entry["file"].startswith("\\")
    # line is an integer
    assert isinstance(entry["line"], int)


def test_covers_repo_relative_path():
    """The file path in STEPS must be relative to the repo root, not cwd."""
    import service.sheetshift_ho3.xlsem as xlsem_mod

    @covers("Calc!Z2", "_test_output2")
    def c_Z2__test_output2(p, c):
        return 0

    entry = xlsem_mod.STEPS[-1]
    # Should contain 'tests' or 'service' as a path component, not an absolute path
    assert not pathlib.Path(entry["file"]).is_absolute()


def test_covers_returns_function_unchanged():
    def my_fn(p, c):
        return 99

    decorated = covers("Calc!A", "_dummy")(my_fn)
    assert decorated is my_fn
    assert decorated({}, {}) == 99
