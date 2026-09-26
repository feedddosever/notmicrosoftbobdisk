# Submission statements (drafts)

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. The builder edits and approves both texts before submitting.

Rules for filling them in:
- Every `[placeholder]` comes from a file: `reports/certificate.json`, `reports/mutation_report.json`, `reports/spotcheck.json`, `bob_sessions/INDEX.md` or a task screenshot. Never estimate one.
- Each statement must stay at 500 words or fewer (lablab limit). The drafts aim for 450 so filled-in numbers cannot push them over. Recount with `wc -w` after filling in.
- Delete any sentence whose evidence is missing (table under the Bob Usage Statement).
- Before submitting, check the two external facts in the Problem paragraph against their sources and record the quotes in `DATA_SOURCES.md`: the Washington fine (Insurance Journal, 19 May 2026) and the Panko figure. If either cannot be confirmed, delete that sentence.

---

## Problem & Solution Statement

**Problem.** At carriers and managing general agents, the premium a policyholder pays is often computed by a spreadsheet: a rating workbook maintained by pricing analysts. When that logic moves into a policy system, an engineer re-implements it by hand, formula by formula, then spot-checks a handful of quotes. Field audits have found errors in at least 86% of the spreadsheets they examined, and translations fail quietly: on our workbook, using Python's round() instead of Excel's ROUND changes [R0] of 10,000 premiums by a cent, which a 20-quote spot check misses [P20]% of the time. When charged premiums drift from filed rates, regulators act: in May 2026 Washington fined an insurer $55,000 after it charged incorrect amounts on 585 policies.

**Solution.** SheetShift is a governed modernization workflow, run inside IBM Bob 2.0, that turns a rating workbook into an owned, tested Python service and shows, cell by cell, where the two agree and why they differ.

1. Map: a deterministic tool extracts every formula into a dependency graph and lints structural anomalies.
2. Plan: Bob, in Plan mode, reads the workbook's formulas and the PDF rating manual and writes a service design, flagging every place they disagree.
3. Translate: Bob spawns subagents in parallel, one per translation unit. Every function is tagged with the cells it covers.
4. Check: an equivalence harness compares [C] formula cells across [N] generated policies, including [B] boundary cases, against the original workbook recalculated in LibreOffice.
5. Triage: mismatches are grouped by root cell. Translation bugs go back to Bob. Spreadsheet anomalies go to a person, who decides against a cited manual rule; the decision is logged with who, when and why.
6. Certify: the harness issues a certificate hashing the workbook, service, harness and seed, plus a cell-to-code traceability report.

Governance is built in. Custom modes limit which folders Bob can edit. A PreToolUse hook blocks edits to the workbook, the grader and the decision log, and CI rejects any Bob-tagged commit that touches them. A mutation self-test injects [M] bugs into Bob's code; the harness caught [K].

Result on our synthetic homeowners workbook for a fictional carrier: [C] cells compared, [E] identical, [D] differing only in rows traced to [A] human-signed decisions, [U] unexplained. The [A] anomalies (a truncated lookup range, a hard-coded value, one inconsistent row) were seeded by us for the demo. Bob fixed [F] translation bugs. The live demo at [APP_URL] serves the quote API, an oracle spot-check and a traceability explorer.

Limits: the oracle is LibreOffice, not Excel [or: cross-checked against Excel on [x] of [y] cells]; inputs are sampled, so this is strong evidence, not formal proof; macros, volatile functions and external links are out of scope.

---

## IBM Bob Usage Statement

SheetShift is a Bob workflow pack (four custom modes, [S] skills, [Q] slash commands, five lifecycle hooks and project rules) plus a deterministic grader, and Bob runs every step of the modernization. We used Bob IDE [version] for [T] tasks, spending [X] of our 40 Bobcoins. Every task's summary screenshot is in bob_sessions/, indexed in bob_sessions/INDEX.md.

Onboarding Bob like a teammate. AGENTS.md and .bob/rules/ encode cell-traceability tags, Excel rounding and lookup semantics, and protected paths. The Sheet Translator mode can edit only service/ and tests/; Sheet Analyst writes only notes under docs/.

Document understanding. Bob's office_read tool returns each cell's formula together with its cached and recalculated value; in our first probe it showed that a stored value (99) no longer matched its formula (7.5). In Plan mode (task [NN]) Bob read the workbook's formulas and the PDF rating manual and wrote docs/design/service_plan.md, and it quoted manual rules [rule numbers] in each anomaly brief.

Subagents and parallel tasks. In task [NN], Bob spawned [G] subagents, one per translation unit, each approved on screen. They wrote [L] lines with [Fn] tagged functions covering [C1] of [C2] formula columns. In tasks [NN] and [NN], triage and anomaly briefs ran as parallel Bob tasks.

Agent loop with hooks. A PreToolUse hook blocks edits to workbook/, harness/, golden/, decisions/ and .bob/. In a prompted guard test Bob attempted a diff edit to the grader and a shell write into it, and the hook blocked both. The hook is the fast control; CI, which rejects any Bob-tagged commit touching those paths, is the enforcing one. PostToolUse runs a 200-policy smoke test after each edit to service/. The harness found [F] translation bugs; Bob fixed them in task [NN].

Human decisions. Bob never decides a spreadsheet anomaly. For [A] seeded anomalies, Bob drafted a brief citing the manual, the builder acting as pricing lead chose an option with tools/decide.py, and Bob implemented it in task [NN].

Review and reporting. /review raised [R] findings; we fixed [R1] with Fix with Bob and dismissed [R2] with reasons. Bob wrote the one-file HTML run summary and docs/architecture.md. Bob-authored lines: [Lb] of [Lt] non-generated lines.

Outcome: [C] cells compared, [U] unexplained; the mutation self-test caught [K] of [M].

What was not Bob. Claude Code, an AI coding agent, built the workbook generator, rating manual, LibreOffice oracle, harness, mapping tools, CI and site shell, so the agent being graded never wrote its own exam. It also drafted the .bob/ pack and these statements, which the builder reviewed and edited. ATTRIBUTION.md records every file's author, and Bob-authored commits carry a Bob-Task trailer.

### Delete a sentence if its evidence is missing

| Sentence about | Required evidence |
|---|---|
| Subagents "each approved on screen" | The T03 screenshot or footage shows the spawn approvals; otherwise write "[G] parallel background tasks" |
| Parallel tasks | Footage of the task panel with T05 and T06 running together |
| PostToolUse smoke | `audit/m1/bob_edits.jsonl` is non-empty |
| /review findings | The T08 screenshot |
| One-file HTML summary | `docs/bob_run_summary.html` exists |
| Excel cross-check wording | `golden/excel_crosscheck.json` exists |
