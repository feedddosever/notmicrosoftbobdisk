# Sheet Triage

- The harness classifies; you fix. Never change tolerance or classifier thresholds, and never reclassify a group.
- Fix only groups classed `translation-bug` or `translation-bug-rounding`. Fix one group at a time; after each fix read reports/smoke_last.json (field `line`) with the read tool, or run `python3 -m harness.smoke --unit <U>`.
- A group joined to a lint is a spreadsheet anomaly. Write a brief for it; never write a code fix.
