"""Unit U2 — AOP rating factors and flags (Calc!K..T).

Reads p : construction (C), protection_class (D), coverage_a (G),
          deductible (H), alarm (J), claims_3yr (L)
Reads c : home_age, roof_age_used, base_premium, constr_factor
"""

from service.sheetshift_ho3 import tables
from service.sheetshift_ho3.xlsem import (
    XLError,
    band,
    covers,
    exact,
    iferror,
    n0,
    text_eq,
    xmin,
    xround,
)

# ---------------------------------------------------------------------------
# Pre-load tables (module-level, loaded once at import)
# ---------------------------------------------------------------------------

# K  pc_factor — INDEX(RateTables!$B$19:$C$28, MATCH(D, $A$19:$A$28, 0), col)
_pc_keys = tables.column("RateTables!$A$19:$A$28")
_pc_data = tables.rows("RateTables!$B$19:$C$28")

# L  age_factor — VLOOKUP(home_age, AgeBands, 2, TRUE)
_age_keys = tables.column("RateTables!$E$12:$E$18")
_age_vals = tables.column("RateTables!$F$12:$F$18")

# M  roof_factor — VLOOKUP(roof_age_used, RoofBands, 2, TRUE)
_roof_keys = tables.column("RateTables!$H$12:$H$16")
_roof_vals = tables.column("RateTables!$I$12:$I$16")

# N  aoi_factor — VLOOKUP(coverage_a, AOIBands, 2, TRUE)
_aoi_keys = tables.column("RateTables!$K$12:$K$18")
_aoi_vals = tables.column("RateTables!$L$12:$L$18")

# O  ded_factor — D-001 adopt-manual: use full DedBands (RateTables!$A$31:$B$36)
#   per R-205; workbook range $A$31:$B$35 stopped 1 row short (lint A1 resolved).
_ded_keys = tables.column("RateTables!$A$31:$A$36")
_ded_vals = tables.column("RateTables!$B$31:$B$36")

# P  claims_factor — VLOOKUP(MIN(L,3), ClaimsTable, 2, FALSE)
_claims_keys = tables.column("RateTables!$E$31:$E$34")
_claims_vals = tables.column("RateTables!$F$31:$F$34")


# ---------------------------------------------------------------------------
# Column functions
# ---------------------------------------------------------------------------

@covers("Calc!K", "pc_factor")
def c_K_pc_factor(p, c):
    """INDEX(RateTables!$B$19:$C$28, MATCH(D2,$A$19:$A$28,0), IF(C2="Frame",1,2))"""
    row_idx = exact(p["protection_class"], _pc_keys, list(range(len(_pc_keys))))
    if isinstance(row_idx, XLError):
        return row_idx
    col_idx = 0 if text_eq(p["construction"], "Frame") else 1
    return _pc_data[row_idx][col_idx]


@covers("Calc!L", "age_factor")
def c_L_age_factor(p, c):
    """VLOOKUP(home_age, AgeBands, 2, TRUE)"""
    return band(c["home_age"], _age_keys, _age_vals)


@covers("Calc!M", "roof_factor")
def c_M_roof_factor(p, c):
    """VLOOKUP(roof_age_used, RoofBands, 2, TRUE)"""
    return band(c["roof_age_used"], _roof_keys, _roof_vals)


@covers("Calc!N", "aoi_factor")
def c_N_aoi_factor(p, c):
    """VLOOKUP(coverage_a, AOIBands, 2, TRUE)"""
    return band(p["coverage_a"], _aoi_keys, _aoi_vals)


@covers("Calc!O", "ded_factor")
def c_O_ded_factor(p, c):
    """VLOOKUP(deductible, DedBands, 2, TRUE)  — D-001 adopt-manual (R-205, full range).
    """
    return band(p["deductible"], _ded_keys, _ded_vals)


@covers("Calc!P", "claims_factor")
def c_P_claims_factor(p, c):
    """VLOOKUP(MIN(claims_3yr,3), ClaimsTable, 2, FALSE)"""
    capped = xmin(p["claims_3yr"], 3)
    return exact(capped, _claims_keys, _claims_vals)


@covers("Calc!Q", "aop_premium")
def c_Q_aop_premium(p, c):
    """ROUND(base_premium * constr_factor * pc_factor * age_factor
              * roof_factor * aoi_factor * ded_factor * claims_factor, 2)"""
    base = c["base_premium"]
    if isinstance(base, XLError):
        return base
    product = (
        base
        * c["constr_factor"]
        * c["pc_factor"]
        * c["age_factor"]
        * c["roof_factor"]
        * c["aoi_factor"]
        * c["ded_factor"]
        * c["claims_factor"]
    )
    if isinstance(product, XLError):
        return product
    return xround(product, 2)


@covers("Calc!R", "alarm_flag")
def c_R_alarm_flag(p, c):
    """IF(alarm="Y", 1, 0)"""
    return 1 if text_eq(p["alarm"], "Y") else 0


@covers("Calc!S", "claims_free_flag")
def c_S_claims_free_flag(p, c):
    """IF(AND(claims_3yr=0, home_age>=3), 1, 0)
    Excel blank==0, so None claims_3yr counts as 0.
    """
    claims_zero = text_eq(p["claims_3yr"], 0)
    age_ok = (c["home_age"] >= 3)
    return 1 if (claims_zero and age_ok) else 0


@covers("Calc!T", "new_home_flag")
def c_T_new_home_flag(p, c):
    """IF(home_age<=5, 1, 0)"""
    return 1 if c["home_age"] <= 5 else 0
