# Bob task index

One row per Bob task, including T00 and any aborted, re-run or fallback task. `tools/check_evidence.py` checks this table; see README.md for the rules.

| Task | Member | Mode | Subagents | Files changed | Commit | Gauge before | Gauge after | Screenshot | Export | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| T00 | m1 | ask, agent, sheet-translator | 0 | none (probes only; guard blocks in audit/m1/hook_events.jsonl) | – | – | task cost 1.08 | sheetshift_task00_probes_m1_summary.png | – | re-run |
