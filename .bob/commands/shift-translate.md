---
description: Translate units into tagged Python with one general subagent per unit
argument-hint: <all|U1|U2|U3|U4>
---
Translate $1 in sheet-translator mode. For `all`, spawn four general subagents in parallel, one per unit U1-U4. Otherwise spawn one subagent for $1.

Give each subagent this task:
- Read only @build/units/<U>.md, @service/sheetshift_ho3/xlsem.py and @service/sheetshift_ho3/tables.py, and use the translate-sheet skill.
- Write service/sheetshift_ho3/units/<u>_<topic>.py in one write_file call, and tests/test_<u>.py in one call.
- Tag every function @covers("Calc!<col>", "<output_name>") with the canonical output names.
- Run `python3 -m harness.smoke --unit <U>`. Stop after at most 2 fix iterations and list the remaining failures.

When all subagents finish (only for `all`), write service/sheetshift_ho3/rater.py:
- ORDER as a literal tuple copied from build/graph.json topo_order;
- quote(policy), which returns all 43 outputs;
- no reads of build/ at runtime.

Also write tests/test_rater_order.py. Then run `python3 -m harness.smoke --n 200` and paste the table.

Do not edit harness/, golden/, workbook/, decisions/, tools/ or .bob/.
