---
name: shift-report
description: >-
  Certify the run, then write the one-file HTML summary and the architecture
  docs
metadata:
  user-invocable: true
  disable-model-invocation: true
---

Run `python3 -m harness.certify`. Then, quoting numbers exactly from reports/certificate.json and reports/traceability.json:
1. Create docs/bob_run_summary.html, one self-contained file with no external requests. Include the certificate numbers, the decision table, traceability coverage and the limits.
2. Write docs/architecture.md, covering the data flow with one diagram in text.
3. Write docs/how_it_works.md, under 250 words, for the README.

Never edit reports/certificate.json or reports/certificate.html. Only harness.certify writes them.
