# Video script: SheetShift (2:50)

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. The builder records, narrates and edits the video.

**Rules the edit must meet (lablab):** MP4, 3:00 or shorter (aim for 2:50), at least 90 s of the solution working on screen, narrated, and IBM Bob clearly visible. Here the product footage runs 0:26–2:16, which is **110 s**. Check the final file with `tools/check_video.sh`.

**How to record:**
- Record the Bob moments live while doing the tasks: T01, T03, T05 and T06 together, and T08. Never re-run a Bob task just for footage.
- OBS scenes: A = Bob panel and editor, B = terminal, C = browser. Record at 1080p30.
- Turn off notifications and hide your email and account name.
- Label any sped-up clip on screen as "sped up ×N".
- Narrate at a calm pace, about 150 words a minute. Each line below fits its slot at that pace.
- Numbers in `[brackets]` come only from `reports/*.json` or the task screenshots.

| Time | Shot | Narration | On-screen caption |
|---|---|---|---|
| 0:00–0:15 | Split screen: `=ROUND(E2*D2,2)` beside Python `round(e*d, 2)`; a terminal counter ticks up to [R0] | "Translate this rating spreadsheet into Python the obvious way, and [R0] of 10,000 premiums come out a cent wrong, because Python's round isn't Excel's ROUND. A twenty-quote spot check misses that [P20] percent of the time." | "[R0]/10,000 rows · synthetic workbook · reports/mutation_report.json" |
| 0:15–0:26 | Headline card read from `reports/certificate.json` | "SheetShift, built on IBM Bob, turns a rating workbook into code you own, and accounts for every cell." | "[C] cells: [E] identical · [D] traced to [A] signed decisions · [U] unexplained" |
| 0:26–0:44 | Bob in **Plan mode** with the workbook and manual attached; the `office_read` result for one cell (formula, cached value, computed value); then the plan's FLAGS table | "In Plan mode, Bob reads the workbook's formulas directly, down to cached values that no longer match their formulas, and the filed rating manual. It designs the service and flags every disagreement. It doesn't decide them." | "Plan mode · native .xlsx + .pdf reading" |
| 0:44–0:54 | Settings → Modes (Sheet Translator's edit scope) and Settings → Hooks | "Bob is onboarded like a teammate. The translator mode edits only the service folder, and a hook guards the workbook, the grader and the decision log." | "Governed: custom modes + PreToolUse hook + CI" |
| 0:54–1:12 | T03: the subagent spawn approvals, the parallel subagent panel with its cost, then one unit file with `@covers` tags | "Bob spawns four subagents in parallel, one per part of the rating chain, and tags every function with the exact cells it covers." | "4 subagents, approved one by one" (change to "parallel background tasks" if T03 used them instead) |
| 1:12–1:26 | Terminal: `/shift-verify` output with the mismatch groups | "We recalculated the original workbook in LibreOffice for ten thousand policies, including [B] boundary cases. Every run compares all [C] cells in about a second." | "Oracle: LibreOffice 24.2, forced recalculation, recorded" |
| 1:26–1:42 | T05 fixing a translation bug (only if a real one happened), with `reports/smoke_last.json` refreshing in scene B; then the task panel with T05 and T06 running together | "Translation bugs go back to Bob, and a hook re-checks after every edit. Meanwhile a second Bob task drafts the anomaly briefs in parallel." | "Parallel tasks: triage + anomaly briefs" |
| 1:42–1:52 | The guard test: Bob attempts an edit to `harness/common.py`; the hook answers "SheetShift guard blocked this call: protected path (harness/common.py)"; `audit/m1/hook_events.jsonl` in the terminal | "As a test, we told Bob to edit the grader. The hook refused, and CI re-hashes the grader on every run." | "Guard test (prompted)" |
| 1:52–2:06 | `docs/anomalies/D-001.md` quoting rule R-205; the builder runs `tools/decide.py` in a terminal | "Spreadsheet anomalies go to a person. Bob quotes the manual rule; I decide as pricing lead, and the decision is logged." | "Anomalies seeded by us for the demo · decisions/decisions.jsonl" |
| 2:06–2:16 | Bob's review findings panel (3 s), the certificate page, then the live `/trace` and `/verify` pages | "Bob's review flagged [R] issues. The certificate hashes the workbook, code, grader and seed, and it's live: pick a cell, see the code." | App URL. If R = 0, cut the review shot and give the time to `/trace`. |
| 2:16–2:44 | Impact slide | "Every rate filing, a pricing engineer re-codes the actuary's workbook by hand. Other platforms keep you running Excel or edit the sheet. SheetShift gives you owned code plus the evidence a reviewer asks for: a certificate, traceability and a signed decision log. AI made translation cheap; verification is the bottleneck. Bob's modes, hooks and approved subagents let us govern it like a new hire." | "Mutation [K]/[M] · spot check misses [P20]% · unit U3: [Hman] min by hand vs [Hbob] min with Bob (n=1)" |
| 2:44–2:50 | End card | "SheetShift: code you own, verified against the spreadsheet, built with IBM Bob." | URL · repository · "/sheetshift" |

**Words to avoid:** "proof", "proven" or "proves" (say "verified", "evidence" or "certificate over [N] inputs"); "replaces actuaries"; "SR 11-7 compliant"; "an Excel error caused a $6B loss"; "Bob tried to edit the grader" (the test was prompted).

**If T03 or the time baseline is missing:** drop the U3 timing from the impact caption rather than estimating it.
