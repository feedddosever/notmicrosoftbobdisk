---
description: Run the equivalence harness against the golden oracle and quote the result
---
Run `python3 -m harness.run --golden --seed 2026`. Then quote these fields from reports/last_run.json exactly, without rounding or paraphrasing:
- cells compared and equal;
- decided cells;
- unexplained cells;
- the number of mismatch groups by class.

If there are groups, list each one's id, root cell and class from reports/mismatches.json, and each PENDING item in reports/decision_queue.json.
