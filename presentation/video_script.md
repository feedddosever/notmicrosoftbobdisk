# Video script: SheetShift (2:50)

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. The builder records, narrates and edits the video.

**Rules the edit must meet (lablab):** MP4, 3:00 or shorter (aim for 2:50), at least 90 s of the solution working on screen, narrated, and IBM Bob clearly visible. Product footage runs 0:26–2:16 (**110 s**). Check the final file with `tools/check_video.sh`.

**What you already have:** screen recordings of the Bob tasks you recorded (T01 Plan mode, T03 subagents), the task screenshots in `bob_sessions/` (use them as stills where footage is missing: T00 guard test, T05, T06, T07), the repository files named below, and the live site. Do not re-run Bob tasks for footage; open a finished task in Bob's Tasks list and scroll it instead.

**Tips:** hide email and account name; label a sped-up clip "sped up ×N"; narrate at about 150 words a minute (each line fits its slot).

Every number below is from `reports/certificate.json` or `bob_sessions/INDEX.md`.

| Time | Shot | Narration | On-screen caption |
|---|---|---|---|
| 0:00–0:15 | `docs/anomalies/D-002.md` (the hard-coded 48.17) and `D-003.md` side by side | "Two of the three errors hidden in this rating workbook touch one policy in ten thousand. A twenty-quote spot check misses each of them ninety-nine point eight percent of the time." | "1 row in 10,000 · a 20-quote spot check misses it 99.8% of the time · synthetic workbook" |
| 0:15–0:26 | README headline or `reports/certificate.html` top card | "SheetShift, built on IBM Bob, turns a rating workbook into code you own, and accounts for every cell." | "430,000 cells: 409,539 identical · 20,461 traced to 3 signed decisions · 0 unexplained" |
| 0:26–0:44 | T01 footage: Bob in **Plan mode** reading the workbook with `office_read` (formula and values), then the FLAGS table in `docs/design/service_plan.md` | "In Plan mode, Bob reads the workbook's formulas directly and the filed rating manual. It designs the service and flags every disagreement with the manual. It doesn't decide them." | "Plan mode · native .xlsx + .pdf reading" |
| 0:44–0:54 | Bob Settings → Modes (Sheet Translator's edit scope) and Settings → Hooks | "Bob is onboarded like a teammate. The translator mode edits only the service folder, and a hook guards the workbook, the grader and the decision log." | "Governed: custom modes + PreToolUse hook + CI" |
| 0:54–1:12 | T03 footage (or `bob_sessions/sheetshift_misc_t03_subagents_m1.png`): four subagents running with their costs; then `units/u2_aop.py` with `@covers` tags | "Bob spawns four subagents in parallel, one per part of the rating chain, and tags every function with the exact cells it covers. Forty-three columns, forty-three functions." | "4 parallel subagents · 43/43 columns traced" |
| 1:12–1:26 | Terminal: `python3 -m harness.run --golden --seed 2026` output | "We recalculated the original workbook in LibreOffice for ten thousand policies, including a hundred and seventy boundary cases. Every run compares all four hundred and thirty thousand cells in about ten seconds." | "Oracle: LibreOffice 24.2, recorded · 10,000 policies" |
| 1:26–1:42 | `audit/m1/bob_edits.jsonl` (subagent edits) and the T03 summary screenshot; then `reports/notes/triage_1.md` ("zero translation bugs") | "A hook re-runs a smoke check after every edit, even inside subagents. It caught one translation bug, blank claim counts, and the subagent fixed it. The full check found zero translation bugs." | "Smoke hook caught 18 wrong cells · fixed by Bob" |
| 1:42–1:52 | T00 screenshot `bob_sessions/sheetshift_task00_probes_m1_summary.png`: "SheetShift guard blocked this call: protected path (harness/common.py)" | "As a test, we told Bob to edit the grader. The hook refused, and CI re-hashes the grader on every run." | "Guard test (prompted)" |
| 1:52–2:06 | `docs/anomalies/D-001.md` quoting rule R-205, then `decisions/decisions.jsonl` | "Spreadsheet anomalies go to a person. Bob quotes the manual rule; I decide as pricing lead, the decision is logged, and Bob implements it." | "Anomalies seeded by us for the demo · 3 decisions signed by m1" |
| 2:06–2:16 | Live site: certificate page (GREEN), then `/trace` for one cell and `/verify` | "The certificate hashes the workbook, code, grader and seed, and it's live: pick a cell, see the code." | https://sheetshift-rho.vercel.app |
| 2:16–2:44 | Impact slide | "Every rate filing, a pricing engineer re-codes the actuary's workbook by hand. SheetShift gives you owned code plus the evidence a reviewer asks for: a certificate, traceability and a signed decision log. AI made translation cheap; verification is the bottleneck. Bob's modes, hooks and subagents let us govern it like a new hire." | "Mutation self-test 51/60 · decision-patched workbook 430,000/430,000" |
| 2:44–2:50 | End card (`presentation/cover.png`) | "SheetShift: code you own, verified against the spreadsheet, built with IBM Bob." | URL · repository |

**Words to avoid:** "proof", "proven" or "proves" (say "verified", "evidence" or "certificate over 10,000 policies"); "replaces actuaries"; "Bob tried to edit the grader" (the test was prompted); "parallel tasks" for T05 and T06 (they ran one after the other).
