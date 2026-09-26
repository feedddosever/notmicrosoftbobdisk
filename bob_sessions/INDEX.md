# Bob task index

One row per Bob task, including T00 and any aborted, re-run or fallback task. `tools/check_evidence.py` checks this table; see README.md for the rules.

| Task | Member | Mode | Subagents | Files changed | Commit | Gauge before | Gauge after | Screenshot | Export | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| T00 | m1 | ask, agent, sheet-translator | 0 | none; 2 calls blocked by the guard | – | – | task cost 1.08 | sheetshift_task00_probes_m1_summary.png | sheetshift_task00_probes_m1_history.json | re-run |
| T01 | m1 | plan | 0 | docs/design/service_plan.md | 9e2266a | – | task cost 2.46 | sheetshift_task01_plan_m1_summary.png | sheetshift_task01_plan_m1_history.json | done |
| T02 | m1 | sheet-translator | 1 | service/sheetshift_ho3/ (3), tests/ (2) | 4de71da | – | task cost 2.02 | sheetshift_task02_xlsem_m1_summary.png | sheetshift_task02_xlsem_m1_history.json | done |
| T03 | m1 | sheet-translator | 4 | service/sheetshift_ho3/rater.py, tests/test_rater_order.py; by the 4 subagents (audit/m1/bob_edits.jsonl): service/sheetshift_ho3/units/ (5), tests/test_u1..u4.py (4) | c1c690d | – | task cost 4.22 | sheetshift_task03_translate_m1_summary.png | sheetshift_task03_translate_m1_history.json | done |
| T04 | m1 | sheet-translator | 0 | service/sheetshift_ho3/ (2), tests/test_api.py | f2f3d71 | – | task cost 1.77 | sheetshift_task04_api_m1_summary.png | sheetshift_task04_api_m1_history.json | done |
