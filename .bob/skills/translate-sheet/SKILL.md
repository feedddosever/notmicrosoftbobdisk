---
name: translate-sheet
description: Translate one unit's formula columns from build/units/<U>.md into tagged Python functions.
---

# Translate one unit

Inputs: `build/units/<U>.md` (column rules, reads, open lints, 5 sample rows) and `service/sheetshift_ho3/xlsem.py`. Read nothing else unless the unit file points to it.

## Rules
- Write one function per column, named `c_<col>_<output_name>(p, c)` and decorated with `@covers("Calc!<col>", "<output_name>")`. Use the canonical output names from the unit file.
  - `p` is the policy dict, with blanks as `None`.
  - `c` holds the outputs already computed. Read upstream values only from `c`.
- Use only `xlsem` helpers for rounding, lookups, text comparison, blanks, dates and errors.
- Errors pass through as `XLError`. If an input value in `c` is an `XLError`, return it unless the formula catches it (IFERROR).
- Load tables through `tables.py` and never open files in a unit module.
- If a formula disagrees with its table or the manual, translate the **column rule** faithfully and add `# SHEETSHIFT-FLAG <id>: <reason>`. Do not fix it.
- Write the module in one `write_file` call: `service/sheetshift_ho3/units/<u>_<topic>.py`, for example `u2_aop.py`.
- Write its tests in one call: `tests/test_<u>.py`, using the 5 sample rows in the unit file.
  - Compare numbers with `pytest.approx(abs=1e-6)`.
  - Compare dates and text exactly.
  - Compare errors by `.code`.
- Run `python3 -m harness.smoke --unit <U>`. Stop after at most 2 fix iterations and list anything still failing.

## Trap checklist
1. ROUND halves away from zero at 15 significant digits.
2. Approximate-match band edges: use `bisect_right - 1`, and a value below the first key gives `#N/A`.
3. Blanks:
   - roof age × 1 = 0;
   - MIN ignores a blank claims count;
   - a blank hurricane % means 2%.
4. Text compares ignore case (`y`, `fortified`, `t01`); concatenation keeps the input's case.
5. ROUNDUP to whole dollars.
6. Dates:
   - EDATE at month end;
   - 29 Feb 2028;
   - YEARFRAC basis 3.
7. DATEDIF `#NUM!` when start > end, caught by IFERROR.
8. Zone `T09` gives `#N/A` all the way through. An error must equal an error.
9. Construction MATCH is case-insensitive (`frame` finds `Frame`).
