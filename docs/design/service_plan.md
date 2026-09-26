# SheetShift HO-3 Service Plan

Author: IBM Bob (Plan mode), onboarding session T01.
Source documents: `build/sheets/Calc.md`, `build/sheets/Calc_exceptions.md`,
`build/units/U1..U4.md`, `build/units.json`, `build/lints.json`,
`workbook/example_mutual_ho3_rater.xlsx`, `manual/example_mutual_ho3_rating_manual.pdf`,
`.bob/rules/20-excel-semantics.md`, `docs/CONTRACT.md`.
Oracle: LibreOffice 24.2. All data is synthetic; carrier is Example Mutual Insurance Co. (FICTIONAL).

---

## 1. Interface: `quote(policy) → dict`

```
quote(policy: dict) -> dict
```

- **Input `p`:** a dict with exactly the 14 keys from `Policies!A..N` (see `docs/CONTRACT.md` §1.1).
  Blank cells arrive as `None`. `effective_date` is a `datetime.date`.
- **Output:** a dict with all 43 output names in `topo_order` from `build/graph.json`.
  Numbers are `int`/`float`, dates are `datetime.date`, text is `str`.
  An error in any cell is returned as `XLError(code)` (e.g. `XLError("#N/A")`); it is never raised.
  Every downstream output that depends on an `XLError` value must also return an `XLError`.
- **`c` dict:** the running accumulation of computed outputs. Each column function receives `(p, c)`
  and appends its output to `c` before the next function runs. Column functions must not mutate `p`.
  `rater.py` drives the loop in `ORDER`, a literal 43-element tuple equal to `graph.json` `topo_order`.
- **Error propagation:** `XLError` propagates through arithmetic, `ROUND`/`ROUNDUP`, `MIN`/`MAX`,
  comparisons, and `&` (string concatenation). `IFERROR(x, alt)` catches any `XLError` and returns
  `alt`. All helpers in `xlsem.py` must handle `XLError` inputs by propagating.

### 14 inputs

| Key | Type | Notes |
|---|---|---|
| `policy_id` | str | Identifier only; not used in rating |
| `zone` | str | T01–T08 eligible; T09 and others → `#N/A` in base_rate/hurr_rate/tax_rate |
| `construction` | str | Frame, Masonry, MasonryVeneer, FireResistive; case-insensitive in MATCH |
| `protection_class` | int | 1–10 |
| `year_built` | int | ≤ effective year |
| `roof_age` | int or None | blank → treated as 0 by `*1` arithmetic |
| `coverage_a` | int | dwelling limit in dollars |
| `deductible` | int | 250, 500, 1000, 1500, 2500, 5000, 7500, 10000, 25000 |
| `hurr_ded_pct` | float or None | 0.02, 0.03, 0.05, 0.10 or blank |
| `alarm` | str or None | Y/N/y/Yes or blank |
| `wind_mit` | str or None | "None" (text), Basic, Fortified, blank |
| `claims_3yr` | int or None | 0–4; blank → rated as 3+ per manual R-320/Table 100-F caveat |
| `effective_date` | datetime.date | |
| `term_months` | int | 6 or 12 |

### 43 outputs (`ORDER` tuple in `rater.py`)

```python
ORDER = (
    "policy_id", "home_age", "roof_age_used", "aoi_units",
    "base_rate", "hurr_rate", "tax_rate", "base_premium",
    "constr_factor", "constr_hurr_factor",                        # U1 end
    "pc_factor", "age_factor", "roof_factor", "aoi_factor",
    "ded_factor", "claims_factor", "aop_premium",
    "alarm_flag", "claims_free_flag", "new_home_flag",            # U2 end
    "mit_basic_flag", "mit_fort_flag", "credit_raw", "credit_pct",
    "aop_net", "hurr_pct_used", "hurr_ded_factor", "wind_mit_factor",
    "hurr_premium", "hurr_capped",                                # U3 end
    "subtotal", "exp_date", "term_factor", "term_premium",
    "min_applied", "premium_rounded", "policy_fee",
    "assessment", "tax", "total_due", "refer_flag",
    "rate_per_1000", "rate_class",                                # U4 end
)
```

---

## 2. Unit U1 — Calc!A..J (base rates and structure factors)

**File:** `service/sheetshift_ho3/units/u1_base.py`
**Reads p:** `policy_id`, `zone`, `construction`, `year_built`, `roof_age`, `coverage_a`, `effective_date`
**Reads c:** nothing (U1 is the root unit)
**Tables:** `BaseRates` (named), `RateTables!$A$13:$A$16`, `RateTables!$B$13:$B$16`, `RateTables!$C$13:$C$16`

| Col | output_name | Formula (row 2) | Key precedents | Excel hazard | Function name | @covers tag |
|---|---|---|---|---|---|---|
| A | `policy_id` | `=Policies!A2` | p.policy_id | None | `c_A_policy_id` | `@covers("Calc!A","policy_id")` |
| B | `home_age` | `=IFERROR(DATEDIF(DATE(Policies!E2,1,1),Policies!M2,"y"),0)` | p.year_built, p.effective_date | `DATEDIF` returns `#NUM!` when year_built > effective year → IFERROR→0; see §20 Dates | `c_B_home_age` | `@covers("Calc!B","home_age")` |
| C | `roof_age_used` | `=Policies!F2*1` | p.roof_age | blank×1=0 (§20 Blanks); converts None→0 | `c_C_roof_age_used` | `@covers("Calc!C","roof_age_used")` |
| D | `aoi_units` | `=Policies!G2/1000` | p.coverage_a | None | `c_D_aoi_units` | `@covers("Calc!D","aoi_units")` |
| E | `base_rate` | `=VLOOKUP(Policies!B2,BaseRates,2,FALSE)` | p.zone | Exact VLOOKUP is case-insensitive; zone T09 → `#N/A` (R-900: only T01–T08 eligible); §20 Lookups | `c_E_base_rate` | `@covers("Calc!E","base_rate")` |
| F | `hurr_rate` | `=VLOOKUP(Policies!B2,BaseRates,3,FALSE)` | p.zone | Same as E; `#N/A` propagates | `c_F_hurr_rate` | `@covers("Calc!F","hurr_rate")` |
| G | `tax_rate` | `=VLOOKUP(Policies!B2,BaseRates,4,FALSE)` | p.zone | Same as E; `#N/A` propagates | `c_G_tax_rate` | `@covers("Calc!G","tax_rate")` |
| H | `base_premium` | `=ROUND(E2*D2,2)` | c.base_rate, c.aoi_units | Use `xlsem.xl_round(x,2)` — not `round()`; §20 Rounding; `XLError` in either arg propagates | `c_H_base_premium` | `@covers("Calc!H","base_premium")` |
| I | `constr_factor` | `=INDEX($B$13:$B$16,MATCH(Policies!C2,$A$13:$A$16,0))` | p.construction | `MATCH(...,0)` is case-insensitive; unknown construction → `#N/A`; §20 Lookups | `c_I_constr_factor` | `@covers("Calc!I","constr_factor")` |
| J | `constr_hurr_factor` | `=INDEX($C$13:$C$16,MATCH(Policies!C2,$A$13:$A$16,0))` | p.construction | Same as I | `c_J_constr_hurr_factor` | `@covers("Calc!J","constr_hurr_factor")` |

**Excel hazard notes (U1):**
- **§20-Dates / DATEDIF:** `DATEDIF(a,b,"y")` returns `#NUM!` when `a > b`. The `IFERROR` wrapper converts this to 0, matching the manual definition "if the year built is later than the effective date, the home age is 0."
- **§20-Blanks / `*1`:** `roof_age=None` → `None*1 = 0`, so missing roof is rated as a new roof (0 years). Manual §1.4 confirms this.
- **§20-Lookups / exact VLOOKUP:** Zone codes compare case-insensitively; `t08` matches `T08`. T09 and any other unrecognised zone produce `#N/A` which propagates forward through all money columns.

---

## 3. Unit U2 — Calc!K..T (rating factors and flags)

**File:** `service/sheetshift_ho3/units/u2_factors.py`
**Reads p:** `construction`, `protection_class`, `coverage_a`, `deductible`, `alarm`, `claims_3yr`
**Reads c:** `home_age`, `roof_age_used`, `base_premium`, `constr_factor`
**Tables:** `AOIBands`, `AgeBands`, `ClaimsTable`, `RoofBands`, `RateTables!$A$19:$A$28`, `RateTables!$A$31:$B$35`, `RateTables!$B$19:$C$28`

| Col | output_name | Formula (row 2) | Key precedents | Excel hazard | Function name | @covers tag |
|---|---|---|---|---|---|---|
| K | `pc_factor` | `=INDEX($B$19:$C$28,MATCH(Policies!D2,$A$19:$A$28,0),IF(Policies!C2="Frame",1,2))` | p.construction, p.protection_class | `MATCH(...,0)` case-insensitive; column selector: Frame→col1, all others→col2 (§20 Text); invalid pc → `#N/A` | `c_K_pc_factor` | `@covers("Calc!K","pc_factor")` |
| L | `age_factor` | `=VLOOKUP(B2,AgeBands,2,TRUE)` | c.home_age | Approximate VLOOKUP uses `bisect_right(keys,v)-1` (§20 Lookups); home_age≥0 always (IFERROR in B), so no `#N/A` risk | `c_L_age_factor` | `@covers("Calc!L","age_factor")` |
| M | `roof_factor` | `=VLOOKUP(C2,RoofBands,2,TRUE)` | c.roof_age_used | Same bisect_right pattern; roof_age_used≥0 | `c_M_roof_factor` | `@covers("Calc!M","roof_factor")` |
| N | `aoi_factor` | `=VLOOKUP(Policies!G2,AOIBands,2,TRUE)` | p.coverage_a | Same bisect_right; coverage_a > 0 always | `c_N_aoi_factor` | `@covers("Calc!N","aoi_factor")` |
| O | `ded_factor` | `=VLOOKUP(Policies!H2,RateTables!$A$31:$B$35,2,TRUE)` | p.deductible | **Lint A1**: range `$A$31:$B$35` is 1 row short of `DedBands` (`$A$31:$B$36`); key 10000 (factor 0.66) is unreachable. Translate the formula *as written* (`$A$31:$B$35`); do not silently adopt `DedBands`. Add `# FLAG A1` comment. §20 Lookups / bisect_right | `c_O_ded_factor` | `@covers("Calc!O","ded_factor")` |
| P | `claims_factor` | `=VLOOKUP(MIN(Policies!L2,3),ClaimsTable,2,FALSE)` | p.claims_3yr | `MIN(blank,3)=3` per §20 Blanks; exact VLOOKUP case-insensitive (numeric keys); claims_3yr>3 clamped to 3 | `c_P_claims_factor` | `@covers("Calc!P","claims_factor")` |
| Q | `aop_premium` | `=ROUND(H2*I2*K2*L2*M2*N2*O2*P2,2)` | all 7 prior factors + base_premium | `xl_round(...,2)`; any `XLError` input propagates | `c_Q_aop_premium` | `@covers("Calc!Q","aop_premium")` |
| R | `alarm_flag` | `=IF(Policies!J2="Y",1,0)` | p.alarm | `"y"="Y"` is TRUE (§20 Text); any value other than Y/y → 0 (manual R-310: "any alarm indicator other than Y, including blank, earns no alarm credit") | `c_R_alarm_flag` | `@covers("Calc!R","alarm_flag")` |
| S | `claims_free_flag` | `=IF(AND(Policies!L2=0,B2>=3),1,0)` | p.claims_3yr, c.home_age | blank=0 (§20 Blanks), so blank claims counts as 0 here — **differs from claims_factor** where blank→3 (see FLAGS table §7) | `c_S_claims_free_flag` | `@covers("Calc!S","claims_free_flag")` |
| T | `new_home_flag` | `=IF(B2<=5,1,0)` | c.home_age | Simple integer comparison; no hazard | `c_T_new_home_flag` | `@covers("Calc!T","new_home_flag")` |

**Excel hazard notes (U2):**
- **§20-Lookups / `bisect_right`:** All approximate VLOOKUPs (`AgeBands`, `RoofBands`, `AOIBands`, and the `DedBands` subset) use `bisect_right(keys, v) - 1`. Using `bisect_left` gives wrong answers exactly on band-edge values.
- **§20-Text / case-insensitive `=`:** The alarm condition `"Y"="Y"` is TRUE and `"y"="Y"` is also TRUE (Excel text equality is case-insensitive). `"Yes"="Y"` is FALSE.
- **§20-Blanks / `MIN`:** `MIN(None, 3)` = 3 (blank is ignored by MIN/MAX). So a blank `claims_3yr` is capped to 3 and maps to the 1.50 factor — consistent with the manual's "not reported" row.

---

## 4. Unit U3 — Calc!U..AD (credits and hurricane)

**File:** `service/sheetshift_ho3/units/u3_credits_hurr.py`
**Reads p:** `coverage_a`, `hurr_ded_pct`, `wind_mit`
**Reads c:** `aoi_units`, `hurr_rate`, `constr_hurr_factor`, `aop_premium`, `alarm_flag`, `claims_free_flag`, `new_home_flag`
**Tables:** `CreditCap`, `CreditPcts`, `HurrCapPct`, `HurrDedTable`, `RateTables!$K$31:$K$33`, `RateTables!$L$31:$L$33`

| Col | output_name | Formula (row 2) | Key precedents | Excel hazard | Function name | @covers tag |
|---|---|---|---|---|---|---|
| U | `mit_basic_flag` | `=IF(Policies!K2="Basic",1,0)` | p.wind_mit | Case-insensitive: `"basic"="Basic"` is TRUE (§20 Text); blank → 0 | `c_U_mit_basic_flag` | `@covers("Calc!U","mit_basic_flag")` |
| V | `mit_fort_flag` | `=IF(Policies!K2="Fortified",1,0)` | p.wind_mit | Same; `"fortified"="Fortified"` is TRUE — verified by oracle (row 8 in U3 sample: `"fortified"` → mit_fort_flag=1) | `c_V_mit_fort_flag` | `@covers("Calc!V","mit_fort_flag")` |
| W | `credit_raw` | `=SUMPRODUCT(R2:V2,CreditPcts)` | alarm_flag, claims_free_flag, new_home_flag, mit_basic_flag, mit_fort_flag | `CreditPcts` is a 5-element row `[0.05, 0.10, 0.08, 0.04, 0.10]`; plain dot product; result inherits `XLError` if any flag is error | `c_W_credit_raw` | `@covers("Calc!W","credit_raw")` |
| X | `credit_pct` | `=MIN(W2,CreditCap)` | c.credit_raw | **Lint A3** at row 31: `=W31` (cap missing for that row). Translate `MIN(W, CreditCap)` per column rule; add `# FLAG A3`. §20 Blanks: `MIN(error, cap)` propagates the error | `c_X_credit_pct` | `@covers("Calc!X","credit_pct")` |
| Y | `aop_net` | `=ROUND(Q2*(1-X2),2)` | c.aop_premium, c.credit_pct | `xl_round(...,2)`; `XLError` in either arg propagates | `c_Y_aop_net` | `@covers("Calc!Y","aop_net")` |
| Z | `hurr_pct_used` | `=IF(Policies!I2="",0.02,Policies!I2)` | p.hurr_ded_pct | blank=`""` (§20 Blanks); None maps to 0.02 (default hurricane deductible per R-410) | `c_Z_hurr_pct_used` | `@covers("Calc!Z","hurr_pct_used")` |
| AA | `hurr_ded_factor` | `=IFERROR(VLOOKUP(Z2,HurrDedTable,2,FALSE),1)` | c.hurr_pct_used | Exact VLOOKUP; only 3 keys (0.02, 0.05, 0.10); any other percentage → `#N/A` → IFERROR→1.0 (manual R-410: "a percentage that is not one of these options takes factor 1.00") | `c_AA_hurr_ded_factor` | `@covers("Calc!AA","hurr_ded_factor")` |
| AB | `wind_mit_factor` | `=IFERROR(INDEX($L$31:$L$33,MATCH(Policies!K2,$K$31:$K$33,0)),1)` | p.wind_mit | Exact MATCH case-insensitive; blank or unrecognised → `#N/A` → IFERROR→1.0 (manual R-410: "not reported → 1.00") | `c_AB_wind_mit_factor` | `@covers("Calc!AB","wind_mit_factor")` |
| AC | `hurr_premium` | `=ROUND(F2*D2*J2*AA2*AB2,2)` | hurr_rate, aoi_units, constr_hurr_factor, hurr_ded_factor, wind_mit_factor | `xl_round(...,2)`; any `XLError` propagates (T09 zone → hurr_rate is `#N/A`) | `c_AC_hurr_premium` | `@covers("Calc!AC","hurr_premium")` |
| AD | `hurr_capped` | `=MIN(AC2,Policies!G2*HurrCapPct)` | p.coverage_a, c.hurr_premium | `HurrCapPct`=0.006; `MIN(XLError, cap)` propagates error (§20 Blanks/Errors) | `c_AD_hurr_capped` | `@covers("Calc!AD","hurr_capped")` |

**Excel hazard notes (U3):**
- **§20-Text / case-insensitive IF:** `"fortified"="Fortified"` is TRUE. Oracle row 8 (`wind_mit="fortified"`) produces `mit_fort_flag=1`, confirming this.
- **§20-Blanks / `hurr_pct_used`:** blank `hurr_ded_pct` arrives as `None`; the formula tests `=""` which is `True` for blank, so the default 2% applies. Translate as `if p.get("hurr_ded_pct") is None: return 0.02`.
- **IFERROR fallback:** Both `hurr_ded_factor` and `wind_mit_factor` use `IFERROR(..., 1)`. The 1.0 fallback is load-bearing: it means no mitigation discount for unrecognised values (manual R-410).

---

## 5. Unit U4 — Calc!AE..AQ (term, fees and referral)

**File:** `service/sheetshift_ho3/units/u4_term_fees.py`
**Reads p:** `zone`, `construction`, `protection_class`, `coverage_a`, `claims_3yr`, `effective_date`, `term_months`
**Reads c:** `roof_age_used`, `aoi_units`, `tax_rate`, `aop_net`, `hurr_capped`
**Tables:** `AssessRate` (scalar 0.013), `FeeTable`, `MinPremium` (scalar 350)

| Col | output_name | Formula (row 2) | Key precedents | Excel hazard | Function name | @covers tag |
|---|---|---|---|---|---|---|
| AE | `subtotal` | `=Y2+AD2` | c.aop_net, c.hurr_capped | No rounding (R-110: subtotal uses amounts as-is); `XLError` propagates | `c_AE_subtotal` | `@covers("Calc!AE","subtotal")` |
| AF | `exp_date` | `=EDATE(Policies!M2,Policies!N2)` | p.effective_date, p.term_months | `EDATE(d,m)` clamps to end-of-month (§20 Dates); e.g. 2026-08-31 + 6 months = 2027-02-28 | `c_AF_exp_date` | `@covers("Calc!AF","exp_date")` |
| AG | `term_factor` | `=ROUND(YEARFRAC(Policies!M2,AF2,3),4)` | p.effective_date, c.exp_date | `YEARFRAC(a,b,3)` = `(b-a).days / 365`; `xl_round(...,4)`; leap-year boundary tested in probe table | `c_AG_term_factor` | `@covers("Calc!AG","term_factor")` |
| AH | `term_premium` | `=ROUND(AE2*AG2,2)` | c.subtotal, c.term_factor | `xl_round(...,2)`; `XLError` propagates | `c_AH_term_premium` | `@covers("Calc!AH","term_premium")` |
| AI | `min_applied` | `=MAX(AH2,MinPremium)` | c.term_premium | `MinPremium`=350; `MAX(XLError, 350)` propagates error (§20 Errors); R-110: no rounding here | `c_AI_min_applied` | `@covers("Calc!AI","min_applied")` |
| AJ | `premium_rounded` | `=ROUNDUP(AI2,0)` | c.min_applied | `xl_roundup(...,0)` (rounds away from zero); §20 Rounding; written premium always a whole dollar | `c_AJ_premium_rounded` | `@covers("Calc!AJ","premium_rounded")` |
| AK | `policy_fee` | `=VLOOKUP(Policies!N2,FeeTable,2,FALSE)` | p.term_months | Exact VLOOKUP; keys 6→$15, 12→$25; any other term → `#N/A` | `c_AK_policy_fee` | `@covers("Calc!AK","policy_fee")` |
| AL | `assessment` | `=ROUND(AJ2*AssessRate,2)` | c.premium_rounded | `AssessRate`=0.013; `xl_round(...,2)`; `XLError` propagates | `c_AL_assessment` | `@covers("Calc!AL","assessment")` |
| AM | `tax` | `=ROUND((AJ2+AK2)*G2,2)` | c.tax_rate, c.premium_rounded, c.policy_fee | **Lint A2** at row 17: hardcoded `48.17` instead of formula. Translate column rule `ROUND((AJ+AK)*G,2)`; add `# FLAG A2`. | `c_AM_tax` | `@covers("Calc!AM","tax")` |
| AN | `total_due` | `=AJ2+AK2+AL2+AM2` | premium_rounded, policy_fee, assessment, tax | No rounding (R-110); `XLError` propagates | `c_AN_total_due` | `@covers("Calc!AN","total_due")` |
| AO | `refer_flag` | `=IF(OR(Policies!G2>1000000,C2>20,Policies!L2>=3),"REFER","OK")` | p.coverage_a, p.claims_3yr, c.roof_age_used | `C2` is `roof_age_used`; blank `claims_3yr` = 0 (§20 Blanks), so blank does NOT trigger referral (manual R-520 §3 confirms: "a claims count that is not reported does not by itself cause a referral") | `c_AO_refer_flag` | `@covers("Calc!AO","refer_flag")` |
| AP | `rate_per_1000` | `=ROUND(AH2/D2,3)` | c.aoi_units, c.term_premium | `xl_round(...,3)`; statistical field (Appendix A); `XLError` propagates | `c_AP_rate_per_1000` | `@covers("Calc!AP","rate_per_1000")` |
| AQ | `rate_class` | `=Policies!B2&"-"&LEFT(Policies!C2,1)&TEXT(Policies!D2,"00")` | p.zone, p.construction, p.protection_class | `&` and `LEFT` preserve input case (§20 Text); `TEXT(pc,"00")` formats as two digits; e.g. `"T03-F08"` | `c_AQ_rate_class` | `@covers("Calc!AQ","rate_class")` |

**Excel hazard notes (U4):**
- **§20-Dates / `EDATE`:** Month-end clamp. `2026-08-31 + 6 = 2027-02-28`. Use `datetime.date` arithmetic with correct last-day-of-month logic.
- **§20-Dates / `YEARFRAC` basis 3:** Exactly `(exp_date - effective_date).days / 365`, rounded to 4 dp. For a 12-month policy spanning a leap day (2028-02-29 → 2029-02-28), the result is `366/365 = 1.0027` (verified in probe table).
- **§20-Rounding / `ROUNDUP`:** `premium_rounded` uses `ROUNDUP(x, 0)`: always rounds away from zero, so `865.001 → 866`. Never use `math.ceil`.
- **§20-Text / `TEXT` and `LEFT`:** `LEFT("FireResistive", 1)` = `"F"` preserving case of the input string, not uppercased. `TEXT(9, "00")` = `"09"`.

---

## 6. Workbook formula vs. Calc.md comparison (5 cells via `office_read`)

Five cells read with `office_read mode:get` from `workbook/example_mutual_ho3_rater.xlsx`:

| Cell | Unit | Formula from workbook (`office_read`) | Formula in `Calc.md` | Match? |
|---|---|---|---|---|
| `Calc!B2` | U1 | `IFERROR(DATEDIF(DATE(Policies!E2,1,1),Policies!M2,"y"),0)` | `=IFERROR(DATEDIF(DATE(Policies!E2,1,1),Policies!M2,"y"),0)` | ✓ |
| `Calc!H2` | U1 | `ROUND(E2*D2,2)` | `=ROUND(E2*D2,2)` | ✓ |
| `Calc!O2` | U2 | `VLOOKUP(Policies!H2,RateTables!$A$31:$B$35,2,TRUE)` | `=VLOOKUP(Policies!H2,RateTables!$A$31:$B$35,2,TRUE)` | ✓ (range `$A$31:$B$35` confirmed — not `DedBands`) |
| `Calc!W2` | U3 | `SUMPRODUCT(R2:V2,CreditPcts)` | `=SUMPRODUCT(R2:V2,CreditPcts)` | ✓ |
| `Calc!AF2` | U4 | `EDATE(Policies!M2,Policies!N2)` | `=EDATE(Policies!M2,Policies!N2)` | ✓ |

All five formulas match `Calc.md` exactly (leading `=` is stripped by `office_read`).
Lint A1 is confirmed: `Calc!O2` uses the literal range `$A$31:$B$35`, not the named range `DedBands`.

---

## 7. FLAGS table — workbook vs. manual disagreements and lints

No flags are decided here. These are observations only; a person decides each one via `tools/decide.py`.

| ID | Type | Cell(s) | Workbook behaviour | Manual rule | Rule text | Options |
|---|---|---|---|---|---|---|
| **A1** | `range_short_of_table` | `Calc!O2:O41` (`ded_factor`) | VLOOKUP uses `$A$31:$B$35` (5 rows); key 10000 → last row (7500, factor 0.66 unreachable via `bisect_right`) | R-205 | Table 205 has a row "$10,000 and over → 0.66"; `DedBands` (`$A$31:$B$36`) includes that row; the formula's range does not | keep-workbook, adopt-manual, escalate |
| **A2** | `hardcoded_value_in_formula_column` | `Calc!AM17` (`tax`) | Cell `AM17` contains the literal number `48.17` instead of the formula `=ROUND((AJ17+AK17)*G17,2)` | R-510 | R-510 states "There are no per-policy overrides of tax: the premium tax is always calculated by this rule and is never entered or adjusted by hand for an individual policy." | adopt-manual, escalate |
| **A3** | `inconsistent_formula` | `Calc!X31` (`credit_pct`) | Row 31: `=W31` (raw credits used without cap); column rule is `=MIN(W31,CreditCap)` | R-310 | R-310: "the total credits shall not exceed 25%". Row 31's policy has credits of 33%, so the cap should fire but doesn't. | adopt-manual, escalate |
| **FLAG-Z** | Manual vs. workbook blank-handling disagreement (not a lint) | `Calc!S2:S41` (`claims_free_flag`) | Formula `AND(claims_3yr=0, home_age>=3)`: blank claims_3yr=0 → **eligible for claims-free credit** | R-320 | R-320 says "a blank claims count counts as zero" for the claims-free credit — this matches the workbook | (consistent, no action) |
| **FLAG-P** | Manual vs. workbook blank-handling (documented) | `Calc!P2:P41` (`claims_factor`) | `VLOOKUP(MIN(blank,3),...)`: blank→MIN(None,3)=3→factor 1.50 | Table 100-F | Manual Table 100-F: "Not reported (blank) → 1.50". Workbook achieves same result via `MIN` arithmetic. Consistent. | (consistent, no action) |

**Summary:** Three open lints (A1, A2, A3) require a human decision. No other workbook-vs-manual disagreements found. FLAG-Z and FLAG-P are observations that the two blank-handling paths (S vs P) are intentionally different but both consistent with the manual.

---

## 8. Out-of-scope items

The following cells are in `build/graph.json` `cells` but are not part of `quote()`. They must be declared in `service/sheetshift_ho3/OUT_OF_SCOPE.json` with a reason, so that `harness/trace.py` does not flag them as uncovered.

| Cell | Label | Formula | Reason |
|---|---|---|---|
| `Summary!B2` | Policies | `=COUNTA(Calc!A2:A41)` | Whole-book aggregate; `Calc.md` §0: "Summary!B2..B6 are whole-book aggregates, not part of quote()" |
| `Summary!B3` | Written premium | `=SUM(Calc!AJ2:AJ41)` | Same: whole-book aggregate |
| `Summary!B4` | Total due | `=SUM(Calc!AN2:AN41)` | Same: whole-book aggregate |
| `Summary!B5` | Avg rate/1000 | `=AVERAGE(Calc!AP2:AP41)` | Same: whole-book aggregate |
| `Summary!B6` | Hurricane share | `=SUMPRODUCT(Calc!AD2:AD41)/SUM(Calc!AE2:AE41)` | Same: whole-book aggregate |

No decision IDs are needed for these — they are declared out of scope in the contract (`docs/CONTRACT.md` §1.4), not because of a lint.

---

## 9. Service file layout

```
service/
  sheetshift_ho3/
    __init__.py          # empty or minimal
    xlsem.py             # XLError, covers, STEPS, xl_round, xl_roundup,
                         # xl_vlookup_approx, xl_vlookup_exact, xl_match,
                         # xl_iferror, xl_datedif, xl_edate, xl_yearfrac
    tables.py            # table(), rows(), column(), scalar() — I/O boundary
    rater.py             # ORDER tuple, quote(policy) -> dict
    OUT_OF_SCOPE.json    # 5 Summary cells
    data/
      rate_tables.json   # byte copy of build/rate_tables.json
      verify_sample_2026.json.gz  # protected; do not overwrite
    units/
      __init__.py
      u1_base.py         # c_A_policy_id .. c_J_constr_hurr_factor
      u2_factors.py      # c_K_pc_factor .. c_T_new_home_flag
      u3_credits_hurr.py # c_U_mit_basic_flag .. c_AD_hurr_capped
      u4_term_fees.py    # c_AE_subtotal .. c_AQ_rate_class

tests/
  test_xlsem.py          # probe values from .bob/rules/20-excel-semantics.md
  test_tables.py         # table/rows/column/scalar
  test_u1_base.py        # sample rows from build/units/U1.md
  test_u2_factors.py     # sample rows from build/units/U2.md
  test_u3_credits_hurr.py# sample rows from build/units/U3.md
  test_u4_term_fees.py   # sample rows from build/units/U4.md
  test_rater_order.py    # ORDER == topo_order from build/graph.json
```

---

## 10. `xlsem.py` helper inventory

| Helper | Implements | Key rule (§20) |
|---|---|---|
| `XLError(code)` | Error type with `.code` | §20 Errors |
| `covers(cell, name)` | Decorator; appends to `STEPS` | `10-cell-traceability.md` |
| `STEPS` | List of `{cell, name, fn, file, line}` | `10-cell-traceability.md` |
| `xl_round(x, d)` | `ROUND` via 15-sig-fig Decimal + ROUND_HALF_UP | §20 Rounding |
| `xl_roundup(x, d)` | `ROUNDUP` via 15-sig-fig Decimal + ROUND_UP | §20 Rounding |
| `xl_vlookup_approx(v, keys, vals)` | `bisect_right(keys,v)-1`; `#N/A` if i<0 | §20 Lookups |
| `xl_vlookup_exact(v, keys, vals)` | case-insensitive linear search; `#N/A` on miss | §20 Lookups |
| `xl_match_exact(v, arr)` | 1-based index, case-insensitive; `#N/A` on miss | §20 Lookups |
| `xl_iferror(x, alt)` | returns `alt` if `x` is `XLError`, else `x` | §20 Errors |
| `xl_datedif_y(a, b)` | complete years a→b; `XLError("#NUM!")` if a>b | §20 Dates |
| `xl_edate(d, m)` | same day m months later, clamped to EOM | §20 Dates |
| `xl_yearfrac_3(a, b)` | `(b-a).days / 365` | §20 Dates |
| `xl_sumproduct(vec_a, vec_b)` | dot product; propagates `XLError` | — |
| `xl_text(v, fmt)` | `TEXT(v, fmt)`; only `"00"` format needed | §20 Text |
| `xl_left(s, n)` | `LEFT(s, n)`; preserves case | §20 Text |

---

## 11. Onboarding amendments to AGENTS.md

Up to 5 changes that would improve clarity or prevent mistakes, based on this onboarding session:

1. **Add a note about `bisect_right` being the only approved lookup pattern.** The rule is in `.bob/rules/20-excel-semantics.md` but not surfaced in `AGENTS.md`. Adding one line — "Approximate VLOOKUP always uses `bisect_right(keys, v) - 1`; `bisect_left` is wrong on band edges" — would prevent the most common lookup translation bug.

2. **Clarify the blank-claims dual behaviour.** `claims_3yr=None` maps to factor 1.50 in `claims_factor` (col P) but to 0 in `claims_free_flag` (col S). This is correct and consistent with the manual, but the difference is surprising. AGENTS.md could note: "Blank `claims_3yr` is 0 for the claims-free credit (R-320) but treated as 3+ for the claims factor (Table 100-F), because `MIN(blank,3)=3` while `blank=0` in arithmetic."

3. **Name the xlsem.py helpers expected at T02.** AGENTS.md says `xlsem.py` owns `XLError, covers, STEPS` but does not name the rounding and lookup helpers. A short inventory line (even just the names) would let translators use the helpers consistently rather than reimplementing them per unit.

4. **Clarify what "translate the formula as written" means for lints.** For A1, the correct behaviour is to use `$A$31:$B$35` (as in the workbook) and add `# FLAG A1` — not to quietly adopt `DedBands`. For A3, use `MIN(W, CreditCap)` (the column rule) and add `# FLAG A3`. AGENTS.md could state: "For an open lint, translate the **column rule** (not the exception cell); mark the column function with `# FLAG <ID>`."

5. **State the oracle version explicitly.** AGENTS.md mentions "the harness" but does not name LibreOffice 24.2. A translator who uses a different oracle may get different rounding for probe values. Adding "Oracle: LibreOffice 24.2 (full recalculation forced); see `.bob/rules/20-excel-semantics.md` for the measured probe values" makes the dependency explicit.
