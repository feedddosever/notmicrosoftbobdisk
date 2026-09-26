"""Unit U4 – Calc!AE..AQ  (final premium, fees, refer flag, rate info)."""

from service.sheetshift_ho3.xlsem import (
    XLError, _propagate,
    covers, xround, xroundup,
    exact, xmax,
    edate, yearfrac_basis3,
)
from service.sheetshift_ho3.tables import scalar, rows as tbl_rows


# ---------------------------------------------------------------------------
# FeeTable: RateTables!$N$31:$O$32  (term_months → policy_fee)
# ---------------------------------------------------------------------------
def _fee_table():
    data = tbl_rows("RateTables!$N$31:$O$32")
    keys = [r[0] for r in data]
    vals = [r[1] for r in data]
    return keys, vals


# AE ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AE", "subtotal")
def c_AE_subtotal(p, c):
    aop = c["aop_net"]
    hurr = c["hurr_capped"]
    err = _propagate(aop, hurr)
    if err is not None:
        return err
    return aop + hurr


# AF ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AF", "exp_date")
def c_AF_exp_date(p, c):
    return edate(p["effective_date"], p["term_months"])


# AG ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AG", "term_factor")
def c_AG_term_factor(p, c):
    exp = c["exp_date"]
    err = _propagate(exp)
    if err is not None:
        return err
    return xround(yearfrac_basis3(p["effective_date"], exp), 4)


# AH ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AH", "term_premium")
def c_AH_term_premium(p, c):
    subtotal = c["subtotal"]
    term_factor = c["term_factor"]
    err = _propagate(subtotal, term_factor)
    if err is not None:
        return err
    return xround(subtotal * term_factor, 2)


# AI ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AI", "min_applied")
def c_AI_min_applied(p, c):
    tp = c["term_premium"]
    err = _propagate(tp)
    if err is not None:
        return err
    return xmax(tp, scalar("MinPremium"))


# AJ ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AJ", "premium_rounded")
def c_AJ_premium_rounded(p, c):
    mi = c["min_applied"]
    err = _propagate(mi)
    if err is not None:
        return err
    return xroundup(mi, 0)


# AK ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AK", "policy_fee")
def c_AK_policy_fee(p, c):
    keys, vals = _fee_table()
    return exact(p["term_months"], keys, vals)


# AL ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AL", "assessment")
def c_AL_assessment(p, c):
    pr = c["premium_rounded"]
    err = _propagate(pr)
    if err is not None:
        return err
    return xround(pr * scalar("AssessRate"), 2)


# AM ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AM", "tax")
def c_AM_tax(p, c):
    pr = c["premium_rounded"]
    fee = c["policy_fee"]
    tax_rate = c["tax_rate"]
    err = _propagate(pr, fee, tax_rate)
    if err is not None:
        return err
    return xround((pr + fee) * tax_rate, 2)


# AN ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AN", "total_due")
def c_AN_total_due(p, c):
    pr = c["premium_rounded"]
    fee = c["policy_fee"]
    assess = c["assessment"]
    tax = c["tax"]
    for v in (pr, fee, assess, tax):
        if isinstance(v, XLError):
            return v
    return pr + fee + assess + tax


# AO ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AO", "refer_flag")
def c_AO_refer_flag(p, c):
    coverage_a = p["coverage_a"]
    roof_age = c["roof_age_used"]
    claims = p["claims_3yr"] or 0
    if coverage_a > 1_000_000 or roof_age > 20 or claims >= 3:
        return "REFER"
    return "OK"


# AP ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AP", "rate_per_1000")
def c_AP_rate_per_1000(p, c):
    tp = c["term_premium"]
    aoi = c["aoi_units"]
    err = _propagate(tp, aoi)
    if err is not None:
        return err
    return xround(tp / aoi, 3)


# AQ ─────────────────────────────────────────────────────────────────────────
@covers("Calc!AQ", "rate_class")
def c_AQ_rate_class(p, c):
    return (
        p["zone"]
        + "-"
        + p["construction"][0]
        + f"{p['protection_class']:02d}"
    )
