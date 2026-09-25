---
description: Classify mismatch groups and fix translation bugs one group at a time
---
Use the equivalence-triage skill on reports/mismatches.json.
- Fix only translation-bug groups, one at a time; after each fix read reports/smoke_last.json (field line) with the read tool, or run python3 -m harness.smoke --unit <U>.
- If a fix makes things worse, say so so that the person can roll back.
- Write reports/notes/triage_<n>.md.
- Never change tolerance, thresholds or protected paths.
