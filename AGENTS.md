# SheetShift — working agreement for Bob

Mission: translate workbook/example_mutual_ho3_rater.xlsx (sheet Calc, 43 formula columns) into
service/sheetshift_ho3/ so that harness/ reports 0 unexplained differences.

Map (read these, not the whole repo):
- build/sheets/Calc.md (43 column rules) and build/sheets/Calc_exceptions.md
- build/units/U1..U4.md (one per translation unit, with canonical output names) and build/lints.json
- manual/example_mutual_ho3_rating_manual.pdf (the filed rules) and docs/design/service_plan.md
- docs/CONTRACT.md (the interface, when you need it)

Loop: /shift-map → /shift-plan → /shift-translate → /shift-verify → /shift-triage → /shift-report.

Read anything, always: the workbook (use office_read), the manual PDF, build/, harness/, docs/. Reading is
expected. Only writing is restricted.

Never edit (write, modify, move or delete): workbook/ manual/ harness/ golden/ build/ decisions/ tools/ .bob/
.github/ AGENTS.md reports/*.json (a hook blocks this and CI rejects it). If the harness looks wrong, write
docs/notes/HARNESS-<n>.md. When the person says a request is a guard test, make the call as asked; the hook blocks it.

Never run tools/decide.py or decide an anomaly. Write a brief in docs/anomalies/; a person decides.

Never use Python round(), float == on money, or bisect_left for approximate lookups (see .bob/rules).

Always tag each function @covers("Calc!<col>", "<output_name>"). Write one function per column.

Interface:
- quote(policy) -> dict of all 43 outputs.
- Errors are returned as XLError values (.code "#N/A"), never raised.
- xlsem.py owns XLError, covers and STEPS.

After each service/ edit a hook runs smoke and writes reports/smoke_last.json. Its result does not
appear in your context until the next prompt. Read that file with the read tool and use its `line`
field (not cat: the guard blocks shell commands that name reports/*.json). If the file is older
than your edit, run `python3 -m harness.smoke --unit <U>` (about 0.2 s).

service/sheetshift_ho3/: stdlib only, except api.py (fastapi, pydantic). I/O only in tables.py and api.py.

All data is synthetic. The carrier is "Example Mutual Insurance Co. (FICTIONAL)", and the anomalies were seeded on purpose.
