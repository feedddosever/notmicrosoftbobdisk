"""Unit U1: Calc!A..J — base rating inputs for SheetShift HO-3."""
import datetime

from service.sheetshift_ho3.xlsem import (
    covers, XLError,
    iferror, datedif_y, n0, exact, xround, _propagate,
)
from service.sheetshift_ho3.tables import table, column

# ---------------------------------------------------------------------------
# Module-level table loads
# ---------------------------------------------------------------------------
_br = table("BaseRates")
_br_zones = [row[0] for row in _br["rows"]]
_br_base  = [row[1] for row in _br["rows"]]
_br_hurr  = [row[2] for row in _br["rows"]]
_br_tax   = [row[3] for row in _br["rows"]]

_constr_keys   = column("RateTables!$A$13:$A$16")
_constr_aop    = column("RateTables!$B$13:$B$16")
_constr_hurr   = column("RateTables!$C$13:$C$16")


# ---------------------------------------------------------------------------
# Column functions
# ---------------------------------------------------------------------------

@covers("Calc!A", "policy_id")
def c_A_policy_id(p, c):
    return p["policy_id"]


@covers("Calc!B", "home_age")
def c_B_home_age(p, c):
    year_built = p["year_built"]
    effective_date = p["effective_date"]
    start = datetime.date(year_built, 1, 1)
    return iferror(datedif_y(start, effective_date), 0)


@covers("Calc!C", "roof_age_used")
def c_C_roof_age_used(p, c):
    return n0(p["roof_age"]) * 1


@covers("Calc!D", "aoi_units")
def c_D_aoi_units(p, c):
    return p["coverage_a"] / 1000


@covers("Calc!E", "base_rate")
def c_E_base_rate(p, c):
    return exact(p["zone"], _br_zones, _br_base)


@covers("Calc!F", "hurr_rate")
def c_F_hurr_rate(p, c):
    return exact(p["zone"], _br_zones, _br_hurr)


@covers("Calc!G", "tax_rate")
def c_G_tax_rate(p, c):
    return exact(p["zone"], _br_zones, _br_tax)


@covers("Calc!H", "base_premium")
def c_H_base_premium(p, c):
    err = _propagate(c["base_rate"], c["aoi_units"])
    if err is not None:
        return err
    return xround(c["base_rate"] * c["aoi_units"], 2)


@covers("Calc!I", "constr_factor")
def c_I_constr_factor(p, c):
    return exact(p["construction"], _constr_keys, _constr_aop)


@covers("Calc!J", "constr_hurr_factor")
def c_J_constr_hurr_factor(p, c):
    return exact(p["construction"], _constr_keys, _constr_hurr)
