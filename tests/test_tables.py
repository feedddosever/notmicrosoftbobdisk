"""Tests for service/sheetshift_ho3/tables.py.

Verifies:
1. data/rate_tables.json is byte-identical to build/rate_tables.json
2. table(), rows(), column(), scalar() work on ranges from build/units/U1.md
"""

import hashlib
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from service.sheetshift_ho3 import tables

_BUILD = pathlib.Path("build/rate_tables.json")
_SERVICE = pathlib.Path("service/sheetshift_ho3/data/rate_tables.json")


# ---------------------------------------------------------------------------
# 1. Byte-identical copy
# ---------------------------------------------------------------------------

def _sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_rate_tables_byte_identical():
    assert _sha256(_BUILD) == _sha256(_SERVICE), (
        "service/sheetshift_ho3/data/rate_tables.json differs from build/rate_tables.json"
    )


# ---------------------------------------------------------------------------
# 2. table() — named table and literal ref
# ---------------------------------------------------------------------------

def test_table_named_baserates():
    t = tables.table("BaseRates")
    assert t["ref"] == "RateTables!$A$3:$D$10"
    assert t["header"] == ["Zone", "AOP rate/1000", "Hurr rate/1000", "Tax rate"]
    assert len(t["rows"]) == 8
    # First row: T01
    assert t["rows"][0][0] == "T01"
    assert t["rows"][0][1] == pytest.approx(3.125, abs=1e-9)


def test_table_literal_ref_construction():
    # U1.md lists RateTables!$A$13:$C$16 as a table key
    t = tables.table("RateTables!$A$13:$C$16")
    assert t["ref"] == "RateTables!$A$13:$C$16"
    assert t["header"][0] == "Construction"
    assert len(t["rows"]) == 4


# ---------------------------------------------------------------------------
# 3. rows() — sub-range resolution
# ---------------------------------------------------------------------------

def test_rows_full_construction_table():
    # Full table: RateTables!$A$13:$C$16
    r = tables.rows("RateTables!$A$13:$C$16")
    assert len(r) == 4
    # ["Frame", 1, 1] is the first row
    assert r[0][0] == "Frame"
    assert r[0][1] == pytest.approx(1.0, abs=1e-9)


def test_rows_sub_range_column_b_construction():
    # One column inside the construction table: B13:B16 (AOP factors)
    r = tables.rows("RateTables!$B$13:$B$16")
    assert len(r) == 4
    assert r[0] == [pytest.approx(1.0, abs=1e-9)]   # Frame AOP factor
    assert r[1] == [pytest.approx(0.88, abs=1e-9)]  # Masonry AOP factor


def test_rows_dedbands_short_range():
    # Lint A1: the formula uses $A$31:$B$35 (5 rows, inside DedBands $A$31:$B$36)
    r = tables.rows("RateTables!$A$31:$B$35")
    assert len(r) == 5
    # Keys: 0, 500, 1000, 2500, 5000
    keys = [row[0] for row in r]
    assert keys == [0, 500, 1000, 2500, 5000]


def test_rows_unknown_ref_raises():
    with pytest.raises(KeyError):
        tables.rows("RateTables!$Z$99:$Z$100")


# ---------------------------------------------------------------------------
# 4. column() — single-column range
# ---------------------------------------------------------------------------

def test_column_construction_names():
    # RateTables!$A$13:$A$16 — construction names column
    col = tables.column("RateTables!$A$13:$A$16")
    assert col == ["Frame", "Masonry", "MasonryVeneer", "FireResistive"]


def test_column_aop_factors():
    # RateTables!$B$13:$B$16 — AOP factors
    col = tables.column("RateTables!$B$13:$B$16")
    assert col == pytest.approx([1.0, 0.88, 0.94, 0.80], abs=1e-9)


def test_column_hurr_factors():
    # RateTables!$C$13:$C$16 — hurricane factors
    col = tables.column("RateTables!$C$13:$C$16")
    assert col == pytest.approx([1.0, 0.8, 0.9, 0.7], abs=1e-9)


# ---------------------------------------------------------------------------
# 5. scalar()
# ---------------------------------------------------------------------------

def test_scalar_min_premium():
    assert tables.scalar("MinPremium") == pytest.approx(350, abs=1e-9)


def test_scalar_credit_cap():
    assert tables.scalar("CreditCap") == pytest.approx(0.25, abs=1e-9)


def test_scalar_assess_rate():
    assert tables.scalar("AssessRate") == pytest.approx(0.013, abs=1e-9)


def test_scalar_hurr_cap_pct():
    assert tables.scalar("HurrCapPct") == pytest.approx(0.006, abs=1e-9)


def test_scalar_unknown_raises():
    with pytest.raises(KeyError):
        tables.scalar("NoSuchScalar")
