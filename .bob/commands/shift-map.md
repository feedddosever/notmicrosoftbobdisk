---
description: Map the workbook's formulas, units and lints (deterministic, no AI reading of values)
argument-hint: (none: the HO-3 workbook only)
---
Use the xlsx-dependency-map skill on workbook/example_mutual_ho3_rater.xlsx.
Run `python3 -m tools.dump_workbook --expect-lints 3`. If $1 names any other workbook, stop and tell the person: a second workbook needs its own layout file and build folder, which Claude Code prepares (docs/bob_prompts.md T11); running the map on it would overwrite the committed build/. Then summarise build/lints.json and build/units.json: the formula count, the column rules, the functions, and each lint with its cell and manual rule.
