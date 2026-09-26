# Triage note — run fd00ebc84e8a

Generated after: `python3 -m harness.run --golden --seed 2026`

## Summary

| Cells compared | Cells equal | Decided | Unexplained | Groups |
|---|---|---|---|---|
| 430 000 | 429 988 | 0 | 12 | 2 × spreadsheet-anomaly |

Lint-explained cells: A2:2, A3:10  
Static-only anomaly: A1 (`Calc!O2:O41`, awaiting D-001)

---

## Group table

| ID | Root cell | Output | Class | Lint | Action | Result |
|---|---|---|---|---|---|---|
| G01 | `Calc!X31` | `credit_pct` | spreadsheet-anomaly | A3 `inconsistent_formula` | No code change — awaiting D-003 | n/a |
| G02 | `Calc!AM17` | `tax` | spreadsheet-anomaly | A2 `hardcoded_value_in_formula_column` | No code change — awaiting D-002 | n/a |

---

## G01 — `Calc!X` (`credit_pct`)

- **Signature:** `delta -0.08 x1` | single row 31 (HO-000030)
- **Predicate:** `p.effective_date in [2027-06-01..2027-06-01]` (precision 0.04: 1 of 28 such rows)
- **Workbook value:** 0.33 | **Service value:** 0.25
- **Column rule:** `=MIN(W31,CreditCap)` — row 31 uses `=W31` (cap omitted)
- **Joined lint:** A3 `inconsistent_formula` → harness class is `spreadsheet-anomaly`
- **Decision required:** D-003 (options: `adopt-manual`, `escalate`)

A group joined to a lint is never a translation bug. No code change was made.

---

## G02 — `Calc!AM` (`tax`)

- **Signature:** `delta -21.65 x1` | single row 17 (HO-000016)
- **Predicate:** `c.premium_rounded in [1301..1301]` (precision 0.20: 1 of 5 such rows)
- **Workbook value:** 48.17 | **Service value:** 26.52
- **Column rule:** `=ROUND((AJ17+AK17)*G17,2)` — row 17 contains literal `48.17`
- **Joined lint:** A2 `hardcoded_value_in_formula_column` → harness class is `spreadsheet-anomaly`
- **Decision required:** D-002 (options: `adopt-manual`, `escalate`)

A group joined to a lint is never a translation bug. No code change was made.

---

## Pending decisions

| ID | Cell | Lint type | Output | Status |
|---|---|---|---|---|
| D-001 | `Calc!O2:O41` | `range_short_of_table` | `ded_factor` | PENDING |
| D-002 | `Calc!AM17` | `hardcoded_value_in_formula_column` | `tax` | PENDING |
| D-003 | `Calc!X31` | `inconsistent_formula` | `credit_pct` | PENDING |

---

## Conclusion

Both mismatch groups are `spreadsheet-anomaly` (joined to lints A2 and A3 respectively).  
There are **zero translation bugs** in this run. No service code was changed.  
198/200 random-sample rows are equal; the 2 differing rows are fully explained by the anomalies above.

---

Re-verify with:

```
python3 -m harness.run --golden --seed 2026
```
