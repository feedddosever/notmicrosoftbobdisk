# Bob task index

One row per Bob task, including T00 and any aborted, re-run or fallback task. `tools/check_evidence.py` checks this table; see README.md for the rules.

| Task | Member | Mode | Subagents | Files changed | Commit | Gauge before | Gauge after | Screenshot | Export | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| T00 | m1 | ask, agent, sheet-translator | 0 | none; 2 calls blocked by the guard | – | – | task cost 1.08 | sheetshift_task00_probes_m1_summary.png | sheetshift_task00_probes_m1_history.json | re-run |
| T01 | m1 | plan | 0 | docs/design/service_plan.md | 9e2266a | – | task cost 2.46 | sheetshift_task01_plan_m1_summary.png | sheetshift_task01_plan_m1_history.json | done |
