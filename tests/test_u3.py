"""Tests for U3 — Calc!U..AD — Hurricane & credit columns.

Sample rows:
  row 2:  coverage_a=982093,  hurr_ded_pct=0.1,  wind_mit="None",      ...
  row 8:  coverage_a=650000,  hurr_ded_pct=0.03, wind_mit="fortified",  ...
  row 10: coverage_a=1145264, hurr_ded_pct=0.02, wind_mit="Basic",      ...
  row 37: coverage_a=1327494, hurr_ded_pct=blank, wind_mit=blank,       ...
  row 40: coverage_a=1010000, hurr_ded_pct=0.05, wind_mit="Fortified",  (hurr_rate=#N/A)
"""

import pytest
from service.sheetshift_ho3.xlsem import XLError
from service.sheetshift_ho3.units.u3_hurricane import (
    c_U_mit_basic_flag,
    c_V_mit_fort_flag,
    c_W_credit_raw,
    c_X_credit_pct,
    c_Y_aop_net,
    c_Z_hurr_pct_used,
    c_AA_hurr_ded_factor,
    c_AB_wind_mit_factor,
    c_AC_hurr_premium,
    c_AD_hurr_capped,
)


# ---------------------------------------------------------------------------
# Sample row fixtures
# ---------------------------------------------------------------------------

# Row 2
P2 = {"coverage_a": 982093, "hurr_ded_pct": 0.1, "wind_mit": "None"}
C2 = {
    "aoi_units": 982.093,
    "hurr_rate": 4.625,
    "constr_hurr_factor": 1,
    "aop_premium": 3997.6,
    "alarm_flag": 0,
    "claims_free_flag": 1,
    "new_home_flag": 0,
    "mit_basic_flag": 0,
    "mit_fort_flag": 0,
}

# Row 8
P8 = {"coverage_a": 650000, "hurr_ded_pct": 0.03, "wind_mit": "fortified"}
C8 = {
    "aoi_units": 650,
    "hurr_rate": 5.875,
    "constr_hurr_factor": 0.7,
    "aop_premium": 6149.64,
    "alarm_flag": 1,
    "claims_free_flag": 0,
    "new_home_flag": 0,
    "mit_basic_flag": 0,
    "mit_fort_flag": 1,
}

# Row 10
P10 = {"coverage_a": 1145264, "hurr_ded_pct": 0.02, "wind_mit": "Basic"}
C10 = {
    "aoi_units": 1145.264,
    "hurr_rate": 1.25,
    "constr_hurr_factor": 0.7,
    "aop_premium": 11851.53,
    "alarm_flag": 1,
    "claims_free_flag": 0,
    "new_home_flag": 0,
    "mit_basic_flag": 1,
    "mit_fort_flag": 0,
}

# Row 37 — blank hurr_ded_pct and wind_mit
P37 = {"coverage_a": 1327494, "hurr_ded_pct": None, "wind_mit": None}
C37 = {
    "aoi_units": 1327.494,
    "hurr_rate": 0.875,
    "constr_hurr_factor": 0.8,
    "aop_premium": 7775.65,
    "alarm_flag": 1,
    "claims_free_flag": 0,
    "new_home_flag": 0,
    "mit_basic_flag": 0,
    "mit_fort_flag": 0,
}

# Row 40 — hurr_rate is #N/A
P40 = {"coverage_a": 1010000, "hurr_ded_pct": 0.05, "wind_mit": "Fortified"}
C40 = {
    "aoi_units": 1010,
    "hurr_rate": XLError("#N/A"),
    "constr_hurr_factor": 1,
    "aop_premium": XLError("#N/A"),
    "alarm_flag": 0,
    "claims_free_flag": 1,
    "new_home_flag": 0,
    "mit_basic_flag": 0,
    "mit_fort_flag": 1,
}


# ---------------------------------------------------------------------------
# Helper: build c progressively through all 10 columns
# ---------------------------------------------------------------------------

def run_u3(p, c_in):
    """Run all 10 U3 column functions in order, returning the extended c dict."""
    c = dict(c_in)
    c["mit_basic_flag"] = c_U_mit_basic_flag(p, c)
    c["mit_fort_flag"] = c_V_mit_fort_flag(p, c)
    c["credit_raw"] = c_W_credit_raw(p, c)
    c["credit_pct"] = c_X_credit_pct(p, c)
    c["aop_net"] = c_Y_aop_net(p, c)
    c["hurr_pct_used"] = c_Z_hurr_pct_used(p, c)
    c["hurr_ded_factor"] = c_AA_hurr_ded_factor(p, c)
    c["wind_mit_factor"] = c_AB_wind_mit_factor(p, c)
    c["hurr_premium"] = c_AC_hurr_premium(p, c)
    c["hurr_capped"] = c_AD_hurr_capped(p, c)
    return c


# ---------------------------------------------------------------------------
# Row 2 tests
# ---------------------------------------------------------------------------

class TestRow2:
    def setup_method(self):
        self.c = run_u3(P2, C2)

    def test_mit_basic_flag(self):
        assert self.c["mit_basic_flag"] == 0

    def test_mit_fort_flag(self):
        assert self.c["mit_fort_flag"] == 0

    def test_credit_raw(self):
        assert self.c["credit_raw"] == pytest.approx(0.1, abs=1e-6)

    def test_credit_pct(self):
        assert self.c["credit_pct"] == pytest.approx(0.1, abs=1e-6)

    def test_aop_net(self):
        assert self.c["aop_net"] == pytest.approx(3597.84, abs=1e-6)

    def test_hurr_pct_used(self):
        assert self.c["hurr_pct_used"] == pytest.approx(0.1, abs=1e-6)

    def test_hurr_ded_factor(self):
        assert self.c["hurr_ded_factor"] == pytest.approx(0.72, abs=1e-6)

    def test_wind_mit_factor(self):
        assert self.c["wind_mit_factor"] == pytest.approx(1.0, abs=1e-6)

    def test_hurr_premium(self):
        assert self.c["hurr_premium"] == pytest.approx(3270.37, abs=1e-6)

    def test_hurr_capped(self):
        assert self.c["hurr_capped"] == pytest.approx(3270.37, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 8 tests
# ---------------------------------------------------------------------------

class TestRow8:
    def setup_method(self):
        self.c = run_u3(P8, C8)

    def test_mit_basic_flag(self):
        assert self.c["mit_basic_flag"] == 0

    def test_mit_fort_flag(self):
        assert self.c["mit_fort_flag"] == 1

    def test_credit_raw(self):
        assert self.c["credit_raw"] == pytest.approx(0.15, abs=1e-6)

    def test_credit_pct(self):
        assert self.c["credit_pct"] == pytest.approx(0.15, abs=1e-6)

    def test_aop_net(self):
        assert self.c["aop_net"] == pytest.approx(5227.19, abs=1e-6)

    def test_hurr_pct_used(self):
        assert self.c["hurr_pct_used"] == pytest.approx(0.03, abs=1e-6)

    def test_hurr_ded_factor(self):
        assert self.c["hurr_ded_factor"] == pytest.approx(1.0, abs=1e-6)

    def test_wind_mit_factor(self):
        assert self.c["wind_mit_factor"] == pytest.approx(0.65, abs=1e-6)

    def test_hurr_premium(self):
        assert self.c["hurr_premium"] == pytest.approx(1737.53, abs=1e-6)

    def test_hurr_capped(self):
        assert self.c["hurr_capped"] == pytest.approx(1737.53, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 10 tests
# ---------------------------------------------------------------------------

class TestRow10:
    def setup_method(self):
        self.c = run_u3(P10, C10)

    def test_mit_basic_flag(self):
        assert self.c["mit_basic_flag"] == 1

    def test_mit_fort_flag(self):
        assert self.c["mit_fort_flag"] == 0

    def test_credit_raw(self):
        assert self.c["credit_raw"] == pytest.approx(0.09, abs=1e-6)

    def test_credit_pct(self):
        assert self.c["credit_pct"] == pytest.approx(0.09, abs=1e-6)

    def test_aop_net(self):
        assert self.c["aop_net"] == pytest.approx(10784.89, abs=1e-6)

    def test_hurr_pct_used(self):
        assert self.c["hurr_pct_used"] == pytest.approx(0.02, abs=1e-6)

    def test_hurr_ded_factor(self):
        assert self.c["hurr_ded_factor"] == pytest.approx(1.0, abs=1e-6)

    def test_wind_mit_factor(self):
        assert self.c["wind_mit_factor"] == pytest.approx(0.85, abs=1e-6)

    def test_hurr_premium(self):
        assert self.c["hurr_premium"] == pytest.approx(851.79, abs=1e-6)

    def test_hurr_capped(self):
        assert self.c["hurr_capped"] == pytest.approx(851.79, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 37 tests — blank hurr_ded_pct and wind_mit
# ---------------------------------------------------------------------------

class TestRow37:
    def setup_method(self):
        self.c = run_u3(P37, C37)

    def test_mit_basic_flag(self):
        assert self.c["mit_basic_flag"] == 0

    def test_mit_fort_flag(self):
        assert self.c["mit_fort_flag"] == 0

    def test_credit_raw(self):
        assert self.c["credit_raw"] == pytest.approx(0.05, abs=1e-6)

    def test_credit_pct(self):
        assert self.c["credit_pct"] == pytest.approx(0.05, abs=1e-6)

    def test_aop_net(self):
        assert self.c["aop_net"] == pytest.approx(7386.87, abs=1e-6)

    def test_hurr_pct_used(self):
        # blank → 0.02
        assert self.c["hurr_pct_used"] == pytest.approx(0.02, abs=1e-6)

    def test_hurr_ded_factor(self):
        assert self.c["hurr_ded_factor"] == pytest.approx(1.0, abs=1e-6)

    def test_wind_mit_factor(self):
        # blank wind_mit → no match → 1
        assert self.c["wind_mit_factor"] == pytest.approx(1.0, abs=1e-6)

    def test_hurr_premium(self):
        assert self.c["hurr_premium"] == pytest.approx(929.25, abs=1e-6)

    def test_hurr_capped(self):
        assert self.c["hurr_capped"] == pytest.approx(929.25, abs=1e-6)


# ---------------------------------------------------------------------------
# Row 40 tests — hurr_rate = #N/A propagates
# ---------------------------------------------------------------------------

class TestRow40:
    def setup_method(self):
        self.c = run_u3(P40, C40)

    def test_mit_basic_flag(self):
        assert self.c["mit_basic_flag"] == 0

    def test_mit_fort_flag(self):
        assert self.c["mit_fort_flag"] == 1

    def test_credit_raw(self):
        assert self.c["credit_raw"] == pytest.approx(0.2, abs=1e-6)

    def test_credit_pct(self):
        assert self.c["credit_pct"] == pytest.approx(0.2, abs=1e-6)

    def test_aop_net(self):
        # aop_premium is #N/A → propagates
        assert isinstance(self.c["aop_net"], XLError)
        assert self.c["aop_net"].code == "#N/A"

    def test_hurr_pct_used(self):
        assert self.c["hurr_pct_used"] == pytest.approx(0.05, abs=1e-6)

    def test_hurr_ded_factor(self):
        assert self.c["hurr_ded_factor"] == pytest.approx(0.85, abs=1e-6)

    def test_wind_mit_factor(self):
        assert self.c["wind_mit_factor"] == pytest.approx(0.65, abs=1e-6)

    def test_hurr_premium(self):
        # hurr_rate is #N/A → propagates
        assert isinstance(self.c["hurr_premium"], XLError)
        assert self.c["hurr_premium"].code == "#N/A"

    def test_hurr_capped(self):
        # hurr_premium is #N/A → propagates
        assert isinstance(self.c["hurr_capped"], XLError)
        assert self.c["hurr_capped"].code == "#N/A"
