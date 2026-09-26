"""Tests for Unit U1: Calc!A..J — base rating inputs."""
import datetime
import importlib
import pytest

# Import the unit module (registers @covers functions as a side-effect)
import service.sheetshift_ho3.units.u1_base as u1

from service.sheetshift_ho3.xlsem import XLError

# ---------------------------------------------------------------------------
# Helper: run all U1 columns in order for a policy dict
# ---------------------------------------------------------------------------
_FUNCS = [
    u1.c_A_policy_id,
    u1.c_B_home_age,
    u1.c_C_roof_age_used,
    u1.c_D_aoi_units,
    u1.c_E_base_rate,
    u1.c_F_hurr_rate,
    u1.c_G_tax_rate,
    u1.c_H_base_premium,
    u1.c_I_constr_factor,
    u1.c_J_constr_hurr_factor,
]
_NAMES = [
    "policy_id", "home_age", "roof_age_used", "aoi_units",
    "base_rate", "hurr_rate", "tax_rate", "base_premium",
    "constr_factor", "constr_hurr_factor",
]


def run(p):
    c = {}
    for fn, name in zip(_FUNCS, _NAMES):
        c[name] = fn(p, c)
    return c


# ---------------------------------------------------------------------------
# Sample policies
# ---------------------------------------------------------------------------

ROW7 = {
    "policy_id": "HO-000006",
    "zone": "T08",
    "construction": "Masonry",
    "year_built": 2005,
    "roof_age": 21,
    "coverage_a": 1514116,
    "effective_date": datetime.date(2026, 5, 26),
}

ROW10 = {
    "policy_id": "HO-000009",
    "zone": "T03",
    "construction": "FireResistive",
    "year_built": 1933,
    "roof_age": 19,
    "coverage_a": 1145264,
    "effective_date": datetime.date(2027, 4, 9),
}

ROW25 = {
    "policy_id": "HO-000024",
    "zone": "T06",
    "construction": "MasonryVeneer",
    "year_built": 1963,
    "roof_age": 23,
    "coverage_a": 953000,
    "effective_date": datetime.date(2026, 10, 16),
}

ROW40 = {
    "policy_id": "HO-000039",
    "zone": "T09",  # not in table → #N/A
    "construction": "Frame",
    "year_built": 1959,
    "roof_age": 25,
    "coverage_a": 1010000,
    "effective_date": datetime.date(2026, 10, 2),
}

ROW41 = {
    "policy_id": "HO-000040",
    "zone": "T05",
    "construction": "FireResistive",
    "year_built": 1976,
    "roof_age": None,  # blank
    "coverage_a": 790319,
    "effective_date": datetime.date(2026, 10, 2),
}


# ---------------------------------------------------------------------------
# Row 7
# ---------------------------------------------------------------------------

def test_row7_policy_id():
    assert run(ROW7)["policy_id"] == "HO-000006"

def test_row7_home_age():
    assert run(ROW7)["home_age"] == 21

def test_row7_roof_age_used():
    assert run(ROW7)["roof_age_used"] == pytest.approx(21, abs=1e-6)

def test_row7_aoi_units():
    assert run(ROW7)["aoi_units"] == pytest.approx(1514.116, abs=1e-6)

def test_row7_base_rate():
    assert run(ROW7)["base_rate"] == pytest.approx(2.875, abs=1e-6)

def test_row7_hurr_rate():
    assert run(ROW7)["hurr_rate"] == pytest.approx(6.5, abs=1e-6)

def test_row7_tax_rate():
    assert run(ROW7)["tax_rate"] == pytest.approx(0.025, abs=1e-6)

def test_row7_base_premium():
    assert run(ROW7)["base_premium"] == pytest.approx(4353.08, abs=1e-6)

def test_row7_constr_factor():
    assert run(ROW7)["constr_factor"] == pytest.approx(0.88, abs=1e-6)

def test_row7_constr_hurr_factor():
    assert run(ROW7)["constr_hurr_factor"] == pytest.approx(0.8, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 10
# ---------------------------------------------------------------------------

def test_row10_policy_id():
    assert run(ROW10)["policy_id"] == "HO-000009"

def test_row10_home_age():
    assert run(ROW10)["home_age"] == 94

def test_row10_roof_age_used():
    assert run(ROW10)["roof_age_used"] == pytest.approx(19, abs=1e-6)

def test_row10_aoi_units():
    assert run(ROW10)["aoi_units"] == pytest.approx(1145.264, abs=1e-6)

def test_row10_base_rate():
    assert run(ROW10)["base_rate"] == pytest.approx(3.64, abs=1e-6)

def test_row10_hurr_rate():
    assert run(ROW10)["hurr_rate"] == pytest.approx(1.25, abs=1e-6)

def test_row10_tax_rate():
    assert run(ROW10)["tax_rate"] == pytest.approx(0.02, abs=1e-6)

def test_row10_base_premium():
    assert run(ROW10)["base_premium"] == pytest.approx(4168.76, abs=1e-6)

def test_row10_constr_factor():
    assert run(ROW10)["constr_factor"] == pytest.approx(0.8, abs=1e-6)

def test_row10_constr_hurr_factor():
    assert run(ROW10)["constr_hurr_factor"] == pytest.approx(0.7, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 25
# ---------------------------------------------------------------------------

def test_row25_policy_id():
    assert run(ROW25)["policy_id"] == "HO-000024"

def test_row25_home_age():
    assert run(ROW25)["home_age"] == 63

def test_row25_roof_age_used():
    assert run(ROW25)["roof_age_used"] == pytest.approx(23, abs=1e-6)

def test_row25_aoi_units():
    assert run(ROW25)["aoi_units"] == pytest.approx(953.0, abs=1e-6)

def test_row25_base_rate():
    assert run(ROW25)["base_rate"] == pytest.approx(3.505, abs=1e-6)

def test_row25_hurr_rate():
    assert run(ROW25)["hurr_rate"] == pytest.approx(4.625, abs=1e-6)

def test_row25_tax_rate():
    assert run(ROW25)["tax_rate"] == pytest.approx(0.0225, abs=1e-6)

def test_row25_base_premium():
    assert run(ROW25)["base_premium"] == pytest.approx(3340.27, abs=1e-6)

def test_row25_constr_factor():
    assert run(ROW25)["constr_factor"] == pytest.approx(0.94, abs=1e-6)

def test_row25_constr_hurr_factor():
    assert run(ROW25)["constr_hurr_factor"] == pytest.approx(0.9, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 40  (zone T09 → #N/A propagates)
# ---------------------------------------------------------------------------

def test_row40_policy_id():
    assert run(ROW40)["policy_id"] == "HO-000039"

def test_row40_home_age():
    assert run(ROW40)["home_age"] == 67

def test_row40_roof_age_used():
    assert run(ROW40)["roof_age_used"] == pytest.approx(25, abs=1e-6)

def test_row40_aoi_units():
    assert run(ROW40)["aoi_units"] == pytest.approx(1010.0, abs=1e-6)

def test_row40_base_rate():
    r = run(ROW40)["base_rate"]
    assert isinstance(r, XLError)
    assert r.code == "#N/A"

def test_row40_hurr_rate():
    r = run(ROW40)["hurr_rate"]
    assert isinstance(r, XLError)
    assert r.code == "#N/A"

def test_row40_tax_rate():
    r = run(ROW40)["tax_rate"]
    assert isinstance(r, XLError)
    assert r.code == "#N/A"

def test_row40_base_premium():
    r = run(ROW40)["base_premium"]
    assert isinstance(r, XLError)
    assert r.code == "#N/A"

def test_row40_constr_factor():
    assert run(ROW40)["constr_factor"] == pytest.approx(1, abs=1e-6)

def test_row40_constr_hurr_factor():
    assert run(ROW40)["constr_hurr_factor"] == pytest.approx(1, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 41  (blank roof_age → 0)
# ---------------------------------------------------------------------------

def test_row41_policy_id():
    assert run(ROW41)["policy_id"] == "HO-000040"

def test_row41_home_age():
    assert run(ROW41)["home_age"] == 50

def test_row41_roof_age_used():
    assert run(ROW41)["roof_age_used"] == pytest.approx(0, abs=1e-6)

def test_row41_aoi_units():
    assert run(ROW41)["aoi_units"] == pytest.approx(790.319, abs=1e-6)

def test_row41_base_rate():
    assert run(ROW41)["base_rate"] == pytest.approx(4.115, abs=1e-6)

def test_row41_hurr_rate():
    assert run(ROW41)["hurr_rate"] == pytest.approx(3.375, abs=1e-6)

def test_row41_tax_rate():
    assert run(ROW41)["tax_rate"] == pytest.approx(0.0225, abs=1e-6)

def test_row41_base_premium():
    assert run(ROW41)["base_premium"] == pytest.approx(3252.16, abs=1e-6)

def test_row41_constr_factor():
    assert run(ROW41)["constr_factor"] == pytest.approx(0.8, abs=1e-6)

def test_row41_constr_hurr_factor():
    assert run(ROW41)["constr_hurr_factor"] == pytest.approx(0.7, abs=1e-6)
