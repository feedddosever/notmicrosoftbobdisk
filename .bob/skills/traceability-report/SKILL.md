---
name: traceability-report
description: Explain coverage from reports/traceability.json and write the one-file HTML summary when asked.
---

# Explain traceability

1. Read `reports/traceability.json`. It holds one entry per rule, `{cell, template, functions, tests, status}`, plus a reverse index from each function to its cells.
2. Report:
   - how many of the 48 rules are covered and how many are out of scope;
   - any rule with a missing or duplicate tag;
   - the function for any cell the person asks about, as `file:line`.
3. Quote numbers exactly as they appear in `reports/*.json`. Never round or restate them.
4. Only when explicitly asked, write the one-file HTML summary `docs/bob_run_summary.html`:
   - inline CSS only, no scripts from the network, no external requests;
   - certificate numbers quoted from `reports/certificate.json`;
   - the decision table;
   - traceability coverage and the limits.
