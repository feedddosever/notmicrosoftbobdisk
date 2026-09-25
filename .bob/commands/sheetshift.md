---
description: Run the whole SheetShift loop on a workbook, stopping for a person at each gate
argument-hint: <workbook-path>
---
Run SheetShift on $1, in this order. Stop and wait for the person at each STOP.

1. Map: follow /shift-map for $1. Report the lints.
2. Plan: ask the person to switch to Plan mode and run /shift-plan $1. STOP until the person approves docs/design/service_plan.md.
3. Translate: in sheet-translator mode, follow /shift-translate all.
4. Verify: follow /shift-verify. STOP and show the person the quoted numbers.
5. Triage: in sheet-triage mode, follow /shift-triage. Briefs for anomalies go to docs/anomalies/.
6. Decisions: a person decides each anomaly with tools/decide.py. You never run it. STOP until decisions/decisions.jsonl has a record for each item. Then confirm with the person before applying any decision.
7. Apply: in sheet-translator mode, implement each recorded decision, then follow /shift-verify again.
8. Report: in sheet-verifier mode, follow /shift-report.

Never edit protected paths (.bob/rules/30-protected-paths.md).
