---
description: Write docs/design/service_plan.md from the workbook, manual and map (run in Plan mode)
argument-hint: (none: the HO-3 workbook only)
---
Run this in Plan mode. Read @workbook/example_mutual_ho3_rater.xlsx, @manual/example_mutual_ho3_rating_manual.pdf, @build/sheets/Calc.md, @build/sheets/Calc_exceptions.md, @build/units.json and @build/lints.json.

Write docs/design/service_plan.md with:
- one section per unit U1-U4, giving for each column the formula, precedents, Excel hazards (cite .bob/rules/20-excel-semantics.md), function name and @covers tag;
- the interface quote(policy) -> dict of 43 outputs, and the shared c dict;
- a FLAGS table of every place where the workbook disagrees with the manual or a lint, with rule numbers. Do not decide them;
- the out-of-scope items.

Do not write code.
