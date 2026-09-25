---
description: Map the workbook's formulas, units and lints (deterministic, no AI reading of values)
argument-hint: <workbook-path>
---
Use the xlsx-dependency-map skill on $1 (default workbook/example_mutual_ho3_rater.xlsx).
Run `python3 -m tools.dump_workbook --expect-lints 3` (add `--workbook $1` for another workbook). Then summarise build/lints.json and build/units.json: the formula count, the column rules, the functions, and each lint with its cell and manual rule.
