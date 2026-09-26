"""Tests for decisions in decisions/decisions.jsonl.

D-001  Calc!O  adopt-manual (R-205): full DedBands range includes the
       10 000+ band at factor 0.66 (workbook range stopped one row short).

D-002  Calc!AM adopt-manual (R-510): column rule implements the manual
       formula ROUND((premium_rounded + policy_fee) * tax_rate, 2).
       Cell AM17 is a hand-entered anomaly in the workbook; the column rule
       is correct and Calc!AM remains in quote().

D-003  Calc!X  adopt-manual (R-310): column rule caps credits at CreditCap
       (25 %).  Cell X31 omitted the cap in the workbook; the column rule
       is correct and Calc!X remains in quote().
"""

import pytest

from service.sheetshift_ho3.xlsem import XLError
from service.sheetshift_ho3.units.u2_aop import c_O_ded_factor
from service.sheetshift_ho3.units.u3_hurricane import c_X_credit_pct
from service.sheetshift_ho3.units.u4_final import c_AM_tax
from service.sheetshift_ho3 import tables


# ---------------------------------------------------------------------------
# D-001 — ded_factor now uses the full DedBands range (key 10 000 → 0.66)
# ---------------------------------------------------------------------------

class TestD001DedFactor:
    """R-205 adopt-manual: DedBands row 10000 → factor 0.66 must be reachable."""

    def test_band_10000_returns_066(self):
        """Deductible exactly at the new top band (10 000) gives 0.66."""
        p = {"deductible": 10000}
        result = c_O_ded_factor(p, {})
        assert result == pytest.approx(0.66, abs=1e-6), (
            "D-001: deductible=10000 should map to factor 0.66 (adopt-manual)"
        )

    def test_band_above_10000_also_returns_066(self):
        """A deductible above 10 000 stays in the top band at 0.66."""
        p = {"deductible": 15000}
        result = c_O_ded_factor(p, {})
        assert result == pytest.approx(0.66, abs=1e-6), (
            "D-001: deductible=15000 should still map to 0.66"
        )

    def test_band_9999_returns_074(self):
        """Deductible just below 10 000 must not jump to the new band."""
        p = {"deductible": 9999}
        result = c_O_ded_factor(p, {})
        assert result == pytest.approx(0.74, abs=1e-6), (
            "D-001: deductible=9999 should still map to 0.74 (5000 band)"
        )


# ---------------------------------------------------------------------------
# D-002 — tax column rule follows R-510 (not the hand-entered AM17 anomaly)
# ---------------------------------------------------------------------------

class TestD002TaxColumnRule:
    """R-510 adopt-manual: tax = ROUND((premium_rounded + policy_fee) * tax_rate, 2).
    The column rule must produce the formula result, never a hard-coded value.
    """

    def test_tax_formula_result(self):
        """Standard inputs give the formula-driven result (not 48.17 from AM17)."""
        # tax_rate lives in c (already computed by c_G_tax_rate)
        c = {
            "premium_rounded": 1000,
            "policy_fee": 25,
            "tax_rate": 0.02,
        }
        result = c_AM_tax({}, c)
        # ROUND((1000 + 25) * 0.02, 2) = ROUND(20.50, 2) = 20.50
        assert result == pytest.approx(20.5, abs=1e-6), (
            f"D-002: tax should be formula-driven (20.50), got {result}"
        )

    def test_column_is_covered(self):
        """Calc!AM must be registered in xlsem.STEPS (column is in quote())."""
        from service.sheetshift_ho3 import xlsem
        names = [s["cell"] for s in xlsem.STEPS]
        assert "Calc!AM" in names, "D-002: Calc!AM must be covered in quote()"


# ---------------------------------------------------------------------------
# D-003 — credit_pct column rule enforces the 25 % cap (R-310)
# ---------------------------------------------------------------------------

class TestD003CreditPctCap:
    """R-310 adopt-manual: credit_pct = MIN(credit_raw, CreditCap).
    The column rule always applies the cap; X31 omitted it.
    """

    def _cap(self):
        return tables.scalar("CreditCap")

    def test_credit_below_cap_passes_through(self):
        """When credit_raw < CreditCap the result equals credit_raw."""
        cap = self._cap()
        below = cap - 0.01
        c = {"credit_raw": below}
        result = c_X_credit_pct({}, c)
        assert result == pytest.approx(below, abs=1e-6), (
            "D-003: credit below cap should pass through unchanged"
        )

    def test_credit_above_cap_is_clamped(self):
        """When credit_raw > CreditCap the result is clamped to CreditCap."""
        cap = self._cap()
        above = cap + 0.05
        c = {"credit_raw": above}
        result = c_X_credit_pct({}, c)
        assert result == pytest.approx(cap, abs=1e-6), (
            f"D-003: credit {above} above cap {cap} should be clamped to {cap}"
        )

    def test_credit_exactly_at_cap(self):
        """credit_raw == CreditCap returns CreditCap (edge case)."""
        cap = self._cap()
        c = {"credit_raw": cap}
        result = c_X_credit_pct({}, c)
        assert result == pytest.approx(cap, abs=1e-6), (
            "D-003: credit exactly at cap should return cap"
        )

    def test_column_is_covered(self):
        """Calc!X must be registered in xlsem.STEPS (column is in quote())."""
        from service.sheetshift_ho3 import xlsem
        names = [s["cell"] for s in xlsem.STEPS]
        assert "Calc!X" in names, "D-003: Calc!X must be covered in quote()"
