---
name: equivalence-triage
description: Classify harness mismatch groups and fix translation bugs.
---

# Triage mismatch groups

1. Read `reports/mismatches.json`. For each group, state:
   - its id;
   - the root cell;
   - the signature and its precision;
   - the harness `class`.
2. Use the harness's class. Never reclassify a group, and never change tolerance or thresholds.
3. Only for classes `translation-bug` and `translation-bug-rounding`:
   - Fix one group at a time.
   - Wait for the smoke line in your next context.
   - If the result got worse, say so plainly, so that the person can roll back.
4. For `spreadsheet-anomaly` or `needs-human` groups, do not change code. Point to `reports/decision_queue.json`.
5. Write `reports/notes/triage_<n>.md` with a table of every group (id, root cell, class, action, result). End it with the command a person runs to re-verify: `python3 -m harness.run --golden --seed 2026`.
