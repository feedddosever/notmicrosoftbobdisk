"""Tests for Unit U2 — AOP rating factors and flags (Calc!K..T).

Sample rows from build/units/U2.md:
  row 6  (idx 0): FireResistive / pc9 / 151000 / 1000  / alarm=Y / claims=2 / home_age=37 / roof=24
  row 10 (idx 1): FireResistive / pc8 / 1145264 / 1000 / alarm=y / claims=3 / home_age=94 / roof=19
  row 30 (idx 2): MasonryVeneer / pc4 / 664000  / 5000 / alarm=y / claims=4 / home_age=32 / roof=25
  row 36 (idx 3): Masonry       / pc2 / 253367  / 2500 / alarm=blank / claims=1 / home_age=61 / roof=14
  row 40 (idx 4): Frame         / pc6 / 1010000 / 1500 / alarm=N / claims=0 / home_age=67 / roof=25 / base=#N/A
"""

import importlib
import pytest

# Import the unit module (registers @covers decorators as a side-effect)
_mod = importlib.import_module("service.sheetshift_ho3.units.u2_aop")

from service.sheetshift_ho3.xlsem import XLError

# Pull the column functions by their decorated names for clarity
c_K = _mod.c_K_pc_factor
c_L = _mod.c_L_age_factor
c_M = _mod.c_M_roof_factor
c_N = _mod.c_N_aoi_factor
c_O = _mod.c_O_ded_factor
c_P = _mod.c_P_claims_factor
c_Q = _mod.c_Q_aop_premium
c_R = _mod.c_R_alarm_flag
c_S = _mod.c_S_claims_free_flag
c_T = _mod.c_T_new_home_flag


# ---------------------------------------------------------------------------
# Sample policy dicts (p) and upstream context dicts (c)
# ---------------------------------------------------------------------------

ROWS = [
    # row 6
    dict(
        p=dict(
            construction="FireResistive",
            protection_class=9,
            coverage_a=151000,
            deductible=1000,
            alarm="Y",
            claims_3yr=2,
        ),
        c=dict(
            home_age=37,
            roof_age_used=24,
            base_premium=641.75,
            constr_factor=0.8,
        ),
        expect=dict(
            pc_factor=1.3,
            age_factor=1.15,
            roof_factor=1.45,
            aoi_factor=0.9,
            ded_factor=0.92,
            claims_factor=1.25,
            aop_premium=1151.88,
            alarm_flag=1,
            claims_free_flag=0,
            new_home_flag=0,
        ),
    ),
    # row 10
    dict(
        p=dict(
            construction="FireResistive",
            protection_class=8,
            coverage_a=1145264,
            deductible=1000,
            alarm="y",
            claims_3yr=3,
        ),
        c=dict(
            home_age=94,
            roof_age_used=19,
            base_premium=4168.76,
            constr_factor=0.8,
        ),
        expect=dict(
            pc_factor=1.09,
            age_factor=1.35,
            roof_factor=1.25,
            aoi_factor=1.4,
            ded_factor=0.92,
            claims_factor=1.5,
            aop_premium=11851.53,
            alarm_flag=1,
            claims_free_flag=0,
            new_home_flag=0,
        ),
    ),
    # row 30
    dict(
        p=dict(
            construction="MasonryVeneer",
            protection_class=4,
            coverage_a=664000,
            deductible=5000,
            alarm="y",
            claims_3yr=4,
        ),
        c=dict(
            home_age=32,
            roof_age_used=25,
            base_premium=2822,
            constr_factor=0.94,
        ),
        expect=dict(
            pc_factor=0.89,
            age_factor=1.15,
            roof_factor=1.45,
            aoi_factor=1.25,
            ded_factor=0.74,
            claims_factor=1.5,
            aop_premium=5462.28,
            alarm_flag=1,
            claims_free_flag=0,
            new_home_flag=0,
        ),
    ),
    # row 36
    dict(
        p=dict(
            construction="Masonry",
            protection_class=2,
            coverage_a=253367,
            deductible=2500,
            alarm=None,
            claims_3yr=1,
        ),
        c=dict(
            home_age=61,
            roof_age_used=14,
            base_premium=755.03,
            constr_factor=0.88,
        ),
        expect=dict(
            pc_factor=0.84,
            age_factor=1.25,
            roof_factor=1.1,
            aoi_factor=1.0,
            ded_factor=0.82,
            claims_factor=1.1,
            aop_premium=692.21,
            alarm_flag=0,
            claims_free_flag=0,
            new_home_flag=0,
        ),
    ),
    # row 40 — base_premium is #N/A
    dict(
        p=dict(
            construction="Frame",
            protection_class=6,
            coverage_a=1010000,
            deductible=1500,
            alarm="N",
            claims_3yr=0,
        ),
        c=dict(
            home_age=67,
            roof_age_used=25,
            base_premium=XLError("#N/A"),
            constr_factor=1,
        ),
        expect=dict(
            pc_factor=1.0,
            age_factor=1.25,
            roof_factor=1.45,
            aoi_factor=1.4,
            ded_factor=0.92,
            claims_factor=1.0,
            aop_premium=XLError("#N/A"),
            alarm_flag=0,
            claims_free_flag=1,
            new_home_flag=0,
        ),
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_c(row_data: dict) -> dict:
    """Construct a running-context dict that includes intermediate results."""
    p = row_data["p"]
    base_c = dict(row_data["c"])  # home_age, roof_age_used, base_premium, constr_factor
    base_c["pc_factor"] = c_K(p, base_c)
    base_c["age_factor"] = c_L(p, base_c)
    base_c["roof_factor"] = c_M(p, base_c)
    base_c["aoi_factor"] = c_N(p, base_c)
    base_c["ded_factor"] = c_O(p, base_c)
    base_c["claims_factor"] = c_P(p, base_c)
    return base_c


# ---------------------------------------------------------------------------
# Parametrised tests
# ---------------------------------------------------------------------------

ROW_IDS = ["row6", "row10", "row30", "row36", "row40"]


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_pc_factor(row, rid):
    result = c_K(row["p"], row["c"])
    exp = row["expect"]["pc_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: pc_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_age_factor(row, rid):
    result = c_L(row["p"], row["c"])
    exp = row["expect"]["age_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: age_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_roof_factor(row, rid):
    result = c_M(row["p"], row["c"])
    exp = row["expect"]["roof_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: roof_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_aoi_factor(row, rid):
    result = c_N(row["p"], row["c"])
    exp = row["expect"]["aoi_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: aoi_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_ded_factor(row, rid):
    result = c_O(row["p"], row["c"])
    exp = row["expect"]["ded_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: ded_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_claims_factor(row, rid):
    result = c_P(row["p"], row["c"])
    exp = row["expect"]["claims_factor"]
    assert result == pytest.approx(exp, abs=1e-6), f"{rid}: claims_factor"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_aop_premium(row, rid):
    p = row["p"]
    full_c = _build_c(row)
    result = c_Q(p, full_c)
    exp = row["expect"]["aop_premium"]
    if isinstance(exp, XLError):
        assert isinstance(result, XLError) and result.code == exp.code, f"{rid}: aop_premium error"
    else:
        assert result == pytest.approx(exp, abs=1e-6), f"{rid}: aop_premium"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_alarm_flag(row, rid):
    result = c_R(row["p"], row["c"])
    assert result == row["expect"]["alarm_flag"], f"{rid}: alarm_flag"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_claims_free_flag(row, rid):
    p = row["p"]
    full_c = _build_c(row)
    result = c_S(p, full_c)
    assert result == row["expect"]["claims_free_flag"], f"{rid}: claims_free_flag"


@pytest.mark.parametrize("row,rid", zip(ROWS, ROW_IDS), ids=ROW_IDS)
def test_new_home_flag(row, rid):
    p = row["p"]
    full_c = _build_c(row)
    result = c_T(p, full_c)
    assert result == row["expect"]["new_home_flag"], f"{rid}: new_home_flag"
