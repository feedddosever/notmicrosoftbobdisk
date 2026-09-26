"""Tests for unit U4 – Calc!AE..AQ (final premium, fees, refer flag, rate info).

5 sample rows from LibreOffice 24.2 golden oracle.
"""
import datetime
import importlib
import pytest

from service.sheetshift_ho3.xlsem import XLError

# Import all column functions by loading the unit module
import service.sheetshift_ho3.units.u4_final as u4  # noqa: F401 (registers @covers)

from service.sheetshift_ho3.units.u4_final import (
    c_AE_subtotal,
    c_AF_exp_date,
    c_AG_term_factor,
    c_AH_term_premium,
    c_AI_min_applied,
    c_AJ_premium_rounded,
    c_AK_policy_fee,
    c_AL_assessment,
    c_AM_tax,
    c_AN_total_due,
    c_AO_refer_flag,
    c_AP_rate_per_1000,
    c_AQ_rate_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_all(p, c_upstream):
    """Run all 13 column functions in order and return the full c dict."""
    c = dict(c_upstream)
    fns = [
        ("subtotal",       c_AE_subtotal),
        ("exp_date",       c_AF_exp_date),
        ("term_factor",    c_AG_term_factor),
        ("term_premium",   c_AH_term_premium),
        ("min_applied",    c_AI_min_applied),
        ("premium_rounded",c_AJ_premium_rounded),
        ("policy_fee",     c_AK_policy_fee),
        ("assessment",     c_AL_assessment),
        ("tax",            c_AM_tax),
        ("total_due",      c_AN_total_due),
        ("refer_flag",     c_AO_refer_flag),
        ("rate_per_1000",  c_AP_rate_per_1000),
        ("rate_class",     c_AQ_rate_class),
    ]
    for name, fn in fns:
        c[name] = fn(p, c)
    return c


# ---------------------------------------------------------------------------
# Row 6: zone T07, FireResistive, pc=9, normal rows
# ---------------------------------------------------------------------------

@pytest.fixture
def row6():
    p = {
        "zone": "T07",
        "construction": "FireResistive",
        "protection_class": 9,
        "coverage_a": 151000,
        "claims_3yr": 2,
        "effective_date": datetime.date(2028, 5, 14),
        "term_months": 6,
    }
    c = {
        "roof_age_used": 24,
        "aoi_units": 151.0,
        "tax_rate": 0.025,
        "aop_net": 1094.29,
        "hurr_capped": 620.99,
    }
    return p, c


def test_row6_subtotal(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["subtotal"] == pytest.approx(1715.28, abs=1e-6)


def test_row6_exp_date(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["exp_date"] == datetime.date(2028, 11, 14)


def test_row6_term_factor(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["term_factor"] == pytest.approx(0.5041, abs=1e-6)


def test_row6_term_premium(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["term_premium"] == pytest.approx(864.67, abs=1e-6)


def test_row6_min_applied(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["min_applied"] == pytest.approx(864.67, abs=1e-6)


def test_row6_premium_rounded(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["premium_rounded"] == pytest.approx(865.0, abs=1e-6)


def test_row6_policy_fee(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["policy_fee"] == pytest.approx(15.0, abs=1e-6)


def test_row6_assessment(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["assessment"] == pytest.approx(11.25, abs=1e-6)


def test_row6_tax(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["tax"] == pytest.approx(22.0, abs=1e-6)


def test_row6_total_due(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["total_due"] == pytest.approx(913.25, abs=1e-6)


def test_row6_refer_flag(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["refer_flag"] == "REFER"  # roof_age_used=24 > 20


def test_row6_rate_per_1000(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["rate_per_1000"] == pytest.approx(5.726, abs=1e-6)


def test_row6_rate_class(row6):
    p, c = row6
    c2 = _run_all(p, c)
    assert c2["rate_class"] == "T07-F09"


# ---------------------------------------------------------------------------
# Row 10: zone T03, FireResistive, pc=8, coverage_a>1M, claims_3yr=3
# ---------------------------------------------------------------------------

@pytest.fixture
def row10():
    p = {
        "zone": "T03",
        "construction": "FireResistive",
        "protection_class": 8,
        "coverage_a": 1145264,
        "claims_3yr": 3,
        "effective_date": datetime.date(2027, 4, 9),
        "term_months": 12,
    }
    c = {
        "roof_age_used": 19,
        "aoi_units": 1145.264,
        "tax_rate": 0.02,
        "aop_net": 10784.89,
        "hurr_capped": 851.79,
    }
    return p, c


def test_row10_subtotal(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["subtotal"] == pytest.approx(11636.68, abs=1e-6)


def test_row10_exp_date(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["exp_date"] == datetime.date(2028, 4, 9)


def test_row10_term_factor(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["term_factor"] == pytest.approx(1.0027, abs=1e-6)


def test_row10_term_premium(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["term_premium"] == pytest.approx(11668.1, abs=1e-4)


def test_row10_premium_rounded(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["premium_rounded"] == pytest.approx(11669.0, abs=1e-6)


def test_row10_policy_fee(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["policy_fee"] == pytest.approx(25.0, abs=1e-6)


def test_row10_assessment(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["assessment"] == pytest.approx(151.7, abs=1e-4)


def test_row10_tax(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["tax"] == pytest.approx(233.88, abs=1e-4)


def test_row10_total_due(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["total_due"] == pytest.approx(12079.58, abs=1e-4)


def test_row10_refer_flag(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["refer_flag"] == "REFER"  # coverage_a>1M and claims_3yr>=3


def test_row10_rate_per_1000(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["rate_per_1000"] == pytest.approx(10.188, abs=1e-3)


def test_row10_rate_class(row10):
    p, c = row10
    c2 = _run_all(p, c)
    assert c2["rate_class"] == "T03-F08"


# ---------------------------------------------------------------------------
# Row 32: zone T06, MasonryVeneer, pc=3
# ---------------------------------------------------------------------------

@pytest.fixture
def row32():
    p = {
        "zone": "T06",
        "construction": "MasonryVeneer",
        "protection_class": 3,
        "coverage_a": 306000,
        "claims_3yr": 2,
        "effective_date": datetime.date(2026, 11, 3),
        "term_months": 6,
    }
    c = {
        "roof_age_used": 22,
        "aoi_units": 306.0,
        "tax_rate": 0.0225,
        "aop_net": 1104.76,
        "hurr_capped": 1082.67,
    }
    return p, c


def test_row32_subtotal(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["subtotal"] == pytest.approx(2187.43, abs=1e-6)


def test_row32_exp_date(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["exp_date"] == datetime.date(2027, 5, 3)


def test_row32_term_factor(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["term_factor"] == pytest.approx(0.4959, abs=1e-6)


def test_row32_term_premium(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["term_premium"] == pytest.approx(1084.75, abs=1e-4)


def test_row32_premium_rounded(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["premium_rounded"] == pytest.approx(1085.0, abs=1e-6)


def test_row32_policy_fee(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["policy_fee"] == pytest.approx(15.0, abs=1e-6)


def test_row32_assessment(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["assessment"] == pytest.approx(14.11, abs=1e-4)


def test_row32_tax(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["tax"] == pytest.approx(24.75, abs=1e-4)


def test_row32_total_due(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["total_due"] == pytest.approx(1138.86, abs=1e-4)


def test_row32_refer_flag(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["refer_flag"] == "REFER"  # roof_age_used=22 > 20


def test_row32_rate_per_1000(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["rate_per_1000"] == pytest.approx(3.545, abs=1e-3)


def test_row32_rate_class(row32):
    p, c = row32
    c2 = _run_all(p, c)
    assert c2["rate_class"] == "T06-M03"


# ---------------------------------------------------------------------------
# Row 36: zone T04, Masonry, pc=2 – only "OK" refer_flag row
# ---------------------------------------------------------------------------

@pytest.fixture
def row36():
    p = {
        "zone": "T04",
        "construction": "Masonry",
        "protection_class": 2,
        "coverage_a": 253367,
        "claims_3yr": 1,
        "effective_date": datetime.date(2027, 9, 6),
        "term_months": 6,
    }
    c = {
        "roof_age_used": 14,
        "aoi_units": 253.367,
        "tax_rate": 0.02,
        "aop_net": 692.21,
        "hurr_capped": 430.72,
    }
    return p, c


def test_row36_subtotal(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["subtotal"] == pytest.approx(1122.93, abs=1e-6)


def test_row36_exp_date(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["exp_date"] == datetime.date(2028, 3, 6)


def test_row36_term_factor(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["term_factor"] == pytest.approx(0.4986, abs=1e-6)


def test_row36_term_premium(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["term_premium"] == pytest.approx(559.89, abs=1e-4)


def test_row36_premium_rounded(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["premium_rounded"] == pytest.approx(560.0, abs=1e-6)


def test_row36_policy_fee(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["policy_fee"] == pytest.approx(15.0, abs=1e-6)


def test_row36_assessment(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["assessment"] == pytest.approx(7.28, abs=1e-4)


def test_row36_tax(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["tax"] == pytest.approx(11.5, abs=1e-4)


def test_row36_total_due(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["total_due"] == pytest.approx(593.78, abs=1e-4)


def test_row36_refer_flag(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["refer_flag"] == "OK"


def test_row36_rate_per_1000(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["rate_per_1000"] == pytest.approx(2.21, abs=1e-3)


def test_row36_rate_class(row36):
    p, c = row36
    c2 = _run_all(p, c)
    assert c2["rate_class"] == "T04-M02"


# ---------------------------------------------------------------------------
# Row 40: zone T09 – upstream errors propagate through all numeric outputs
# ---------------------------------------------------------------------------

@pytest.fixture
def row40():
    p = {
        "zone": "T09",
        "construction": "Frame",
        "protection_class": 6,
        "coverage_a": 1010000,
        "claims_3yr": 0,
        "effective_date": datetime.date(2026, 10, 2),
        "term_months": 12,
    }
    c = {
        "roof_age_used": 25,
        "aoi_units": 1010.0,
        "tax_rate": XLError("#N/A"),
        "aop_net": XLError("#N/A"),
        "hurr_capped": XLError("#N/A"),
    }
    return p, c


def test_row40_subtotal_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["subtotal"], XLError)
    assert c2["subtotal"].code == "#N/A"


def test_row40_exp_date(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert c2["exp_date"] == datetime.date(2027, 10, 2)


def test_row40_term_factor(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert c2["term_factor"] == pytest.approx(1.0, abs=1e-6)


def test_row40_term_premium_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["term_premium"], XLError)
    assert c2["term_premium"].code == "#N/A"


def test_row40_min_applied_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["min_applied"], XLError)


def test_row40_premium_rounded_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["premium_rounded"], XLError)


def test_row40_policy_fee(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert c2["policy_fee"] == pytest.approx(25.0, abs=1e-6)


def test_row40_assessment_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["assessment"], XLError)


def test_row40_tax_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["tax"], XLError)


def test_row40_total_due_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["total_due"], XLError)


def test_row40_refer_flag(row40):
    p, c = row40
    c2 = _run_all(p, c)
    # coverage_a=1010000 > 1000000  → REFER
    assert c2["refer_flag"] == "REFER"


def test_row40_rate_per_1000_is_error(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert isinstance(c2["rate_per_1000"], XLError)


def test_row40_rate_class(row40):
    p, c = row40
    c2 = _run_all(p, c)
    assert c2["rate_class"] == "T09-F06"
