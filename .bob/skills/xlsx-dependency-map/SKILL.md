---
name: xlsx-dependency-map
description: Build and explain the formula map of a workbook using tools/dump_workbook.py.
---

# Map a workbook

1. Run `python3 -m tools.dump_workbook --expect-lints 3`. For another workbook, add `--workbook <path>`; the default is `workbook/example_mutual_ho3_rater.xlsx`. The run is deterministic and writes only `build/`.
2. Read `build/lints.json` and `build/units.json`. Open `build/sheets/Calc.md` only if you need a specific column rule.
3. Report:
   - the formula cell count and the number of column rules (from `build/graph.json` `stats`);
   - the functions used (`function_inventory`);
   - each lint with its ID, type, cell, formula, column rule and manual rule;
   - the units, with their column ranges.
4. Never work out a formula from cell values. If your native reading of the .xlsx disagrees with the dump, raise a FLAG that names the cell and trust the dump.
5. Do not edit anything under `build/` by hand.
