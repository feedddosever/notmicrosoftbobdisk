---
name: manual-adjudication
description: Draft a decision brief for a spreadsheet anomaly using the PDF rating manual.
---

# Draft an anomaly brief

For each PENDING item in `reports/decision_queue.json`, write `docs/anomalies/<id>.md` (for example `D-001.md`) using this template:

| Field | Content |
|---|---|
| Anomaly ID | Decision ID and lint ID |
| Cells | Exact cell or column range |
| Workbook formula | Quoted exactly, next to the column rule |
| Manual rule | Rule number, verbatim quote, page |
| Rows affected | From the queue's `runtime` (or "static only") |
| Premium impact | Minimum, median and maximum difference in `total_due` |
| Options allowed | Only those listed in the queue item |
| Recommendation | One option, with the reason |
| Confidence | High, medium or low, with the reason |

- The manual is `manual/example_mutual_ho3_rating_manual.pdf`. Quote rules verbatim. Never paraphrase a rule as a quote.
- Recommend; do not decide. A person decides with `tools/decide.py`. Never run it and never write under `decisions/`.
- State that the anomaly was seeded for the demonstration.
