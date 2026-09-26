"""Unit U3 — Calc!U..AD — Hurricane & credit columns.

Columns: mit_basic_flag, mit_fort_flag, credit_raw, credit_pct, aop_net,
         hurr_pct_used, hurr_ded_factor, wind_mit_factor, hurr_premium, hurr_capped
"""

from service.sheetshift_ho3.xlsem import (
    XLError,
    covers,
    exact,
    iferror,
    text_eq,
    xmin,
    xround,
)
from service.sheetshift_ho3.tables import column, rows, scalar


# ---------------------------------------------------------------------------
# U — mit_basic_flag
# ---------------------------------------------------------------------------

@covers("Calc!U", "mit_basic_flag")
def c_U_mit_basic_flag(p, c):
    """=IF(Policies!K2="Basic",1,0)"""
    return 1 if text_eq(p["wind_mit"], "Basic") else 0


# ---------------------------------------------------------------------------
# V — mit_fort_flag
# ---------------------------------------------------------------------------

@covers("Calc!V", "mit_fort_flag")
def c_V_mit_fort_flag(p, c):
    """=IF(Policies!K2="Fortified",1,0)"""
    return 1 if text_eq(p["wind_mit"], "Fortified") else 0


# ---------------------------------------------------------------------------
# W — credit_raw
# ---------------------------------------------------------------------------

@covers("Calc!W", "credit_raw")
def c_W_credit_raw(p, c):
    """=SUMPRODUCT(R2:V2,CreditPcts)
    R2:V2 = [alarm_flag, claims_free_flag, new_home_flag, mit_basic_flag, mit_fort_flag]
    CreditPcts = RateTables!$B$40:$F$40
    """
    flags = [
        c["alarm_flag"],
        c["claims_free_flag"],
        c["new_home_flag"],
        c["mit_basic_flag"],
        c["mit_fort_flag"],
    ]
    # Propagate any upstream XLError
    for f in flags:
        if isinstance(f, XLError):
            return f
    weights = rows("RateTables!$B$40:$F$40")[0]
    return sum(f * w for f, w in zip(flags, weights))


# ---------------------------------------------------------------------------
# X — credit_pct
# ---------------------------------------------------------------------------

@covers("Calc!X", "credit_pct")
def c_X_credit_pct(p, c):
    """=MIN(W2,CreditCap)"""
    credit_raw = c["credit_raw"]
    if isinstance(credit_raw, XLError):
        return credit_raw
    cap = scalar("CreditCap")
    return xmin(credit_raw, cap)


# ---------------------------------------------------------------------------
# Y — aop_net
# ---------------------------------------------------------------------------

@covers("Calc!Y", "aop_net")
def c_Y_aop_net(p, c):
    """=ROUND(Q2*(1-X2),2)"""
    aop_premium = c["aop_premium"]
    if isinstance(aop_premium, XLError):
        return aop_premium
    credit_pct = c["credit_pct"]
    if isinstance(credit_pct, XLError):
        return credit_pct
    return xround(aop_premium * (1 - credit_pct), 2)


# ---------------------------------------------------------------------------
# Z — hurr_pct_used
# ---------------------------------------------------------------------------

@covers("Calc!Z", "hurr_pct_used")
def c_Z_hurr_pct_used(p, c):
    """=IF(Policies!I2="",0.02,Policies!I2)  — blank hurr_ded_pct → 0.02"""
    return 0.02 if text_eq(p["hurr_ded_pct"], "") else p["hurr_ded_pct"]


# ---------------------------------------------------------------------------
# AA — hurr_ded_factor
# ---------------------------------------------------------------------------

@covers("Calc!AA", "hurr_ded_factor")
def c_AA_hurr_ded_factor(p, c):
    """=IFERROR(VLOOKUP(Z2,HurrDedTable,2,FALSE),1)
    HurrDedTable = RateTables!$H$31:$I$33 (exact/FALSE match on col 0)
    """
    hurr_pct_used = c["hurr_pct_used"]
    tbl = rows("RateTables!$H$31:$I$33")
    keys = [row[0] for row in tbl]
    vals = [row[1] for row in tbl]
    return iferror(exact(hurr_pct_used, keys, vals), 1)


# ---------------------------------------------------------------------------
# AB — wind_mit_factor
# ---------------------------------------------------------------------------

@covers("Calc!AB", "wind_mit_factor")
def c_AB_wind_mit_factor(p, c):
    """=IFERROR(INDEX($L$31:$L$33,MATCH(K2,$K$31:$K$33,0)),1)
    Keys = RateTables!$K$31:$K$33, Vals = RateTables!$L$31:$L$33 (exact match)
    """
    keys = column("RateTables!$K$31:$K$33")
    vals = column("RateTables!$L$31:$L$33")
    return iferror(exact(p["wind_mit"], keys, vals), 1)


# ---------------------------------------------------------------------------
# AC — hurr_premium
# ---------------------------------------------------------------------------

@covers("Calc!AC", "hurr_premium")
def c_AC_hurr_premium(p, c):
    """=ROUND(F2*D2*J2*AA2*AB2,2)
    F2=hurr_rate, D2=aoi_units, J2=constr_hurr_factor, AA2=hurr_ded_factor, AB2=wind_mit_factor
    """
    hurr_rate = c["hurr_rate"]
    if isinstance(hurr_rate, XLError):
        return hurr_rate
    aoi_units = c["aoi_units"]
    if isinstance(aoi_units, XLError):
        return aoi_units
    constr_hurr_factor = c["constr_hurr_factor"]
    if isinstance(constr_hurr_factor, XLError):
        return constr_hurr_factor
    hurr_ded_factor = c["hurr_ded_factor"]
    if isinstance(hurr_ded_factor, XLError):
        return hurr_ded_factor
    wind_mit_factor = c["wind_mit_factor"]
    if isinstance(wind_mit_factor, XLError):
        return wind_mit_factor
    return xround(hurr_rate * aoi_units * constr_hurr_factor * hurr_ded_factor * wind_mit_factor, 2)


# ---------------------------------------------------------------------------
# AD — hurr_capped
# ---------------------------------------------------------------------------

@covers("Calc!AD", "hurr_capped")
def c_AD_hurr_capped(p, c):
    """=MIN(AC2,Policies!G2*HurrCapPct)"""
    hurr_premium = c["hurr_premium"]
    if isinstance(hurr_premium, XLError):
        return hurr_premium
    cap_pct = scalar("HurrCapPct")
    return xmin(hurr_premium, p["coverage_a"] * cap_pct)
