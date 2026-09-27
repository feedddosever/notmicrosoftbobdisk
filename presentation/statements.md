# Submission statements

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. The builder edits and approves both texts before submitting.

Every number below comes from a file: `reports/certificate.json` (430,000 cells; 409,539 identical; 20,461 decided; 0 unexplained; patched 430,000/430,000; 170 boundary policies; mutation 51/60; spot-check odds), `bob_sessions/INDEX.md` (tasks and Bobcoins), `tools/check_evidence.py` (Bob-authored lines) and `wc -l` on `service/sheetshift_ho3/units/`. The two outside facts are recorded with their quotes in `DATA_SOURCES.md` (S1, S3). Each statement is under the 500-word limit (`wc -w`).

---

## Problem & Solution Statement

**Problem.** At carriers and managing general agents, the premium a policyholder pays is often computed by a spreadsheet: a rating workbook maintained by pricing analysts. Moving it into a policy system means re-coding it by hand and spot-checking a few quotes. Field audits have found errors in at least 86% of the spreadsheets they examined, and the dangerous errors are rare: in our workbook, a hard-coded tax and a missing credit cap each affect one policy in 10,000, so a 20-quote spot check misses each 99.8% of the time. When charged premiums drift from filed rates, regulators act: in May 2026 Washington fined an insurer $55,000 after it charged incorrect amounts on 585 policies.

**Solution.** SheetShift is a governed modernization workflow, run inside IBM Bob 2.0, that turns a rating workbook into an owned, tested Python service and shows, cell by cell, where the two agree and why they differ.

**Who uses it, and how.** A pricing engineer runs one Bob slash command per step. The pricing lead reads Bob's anomaly briefs and decides each one at a terminal. A reviewer opens the certificate and, on the live site, picks any workbook cell to see its code, or re-runs the comparison.

1. Map: every formula goes into a dependency graph; a linter flags structural anomalies.
2. Plan: Bob, in Plan mode, reads the workbook's formulas and the PDF rating manual and writes a service design, flagging every disagreement.
3. Translate: four Bob subagents work in parallel, one per translation unit; every function is tagged with the cells it covers.
4. Check: a harness compares all 43 output columns for 10,000 generated policies (430,000 cells), including 170 boundary cases, against the original workbook recalculated in LibreOffice.
5. Triage: mismatches are grouped by root cell; translation bugs go back to Bob, spreadsheet anomalies to a person, who decides against a cited manual rule in a signed log.
6. Certify: a certificate hashes workbook, service, harness and seed, with cell-to-code traceability.

**What is new.** The AI writes the code, but a harness it cannot edit grades it, and only a person can accept a difference. Custom modes limit Bob's folders, a hook blocks edits to the workbook, grader and decision log, and CI rejects any Bob commit that touches them. The grader is itself tested: of 60 injected bugs it caught 51, and a person labelled the 9 survivors.

**Result** on our synthetic homeowners workbook for a fictional carrier: 430,000 cells compared, 409,539 identical, 20,461 differing only in rows traced to 3 human-signed decisions, 0 unexplained; against the decision-patched workbook, 430,000 of 430,000 match. The three anomalies (a lookup range one row short, mispricing 11 of the workbook's 40 policies; a hard-coded tax; one row missing the credit cap) were seeded by us. Live demo: https://sheetshift-rho.vercel.app.

Limits: LibreOffice oracle, not Excel; sampled inputs are evidence, not proof; no macros or volatile functions.

---

## IBM Bob Usage Statement

SheetShift is a Bob workflow pack (four custom modes, 9 skills, 7 slash commands, five lifecycle hooks and project rules) plus a deterministic grader, and Bob runs every step of the modernization. We used Bob IDE 2.0 for 8 indexed tasks, spending about 16 of our 40 Bobcoins. Every task's summary screenshot and exported session is in bob_sessions/, indexed in bob_sessions/INDEX.md.

Onboarding Bob like a teammate. AGENTS.md and .bob/rules/ encode cell-traceability tags, Excel rounding and lookup semantics, and protected paths. The Sheet Translator mode can edit only service/ and tests/; Sheet Analyst writes only notes under docs/. Bob's own onboarding feedback (T01) added a rule to AGENTS.md.

Document understanding. Bob's office_read tool returns each cell's formula together with its cached and recalculated value; in our first probe it showed that a stored value (99) no longer matched its formula (7.5). In Plan mode (T01) Bob read the workbook's formulas and the PDF rating manual, wrote docs/design/service_plan.md and flagged all three anomalies with rules R-205, R-510 and R-310, which its briefs (T06) quote verbatim. To correct one brief, Bob read the Policies sheet with office_read and counted the 11 affected policies itself.

Subagents. In T03, Bob spawned 4 subagents in parallel, one per translation unit. They wrote 543 lines of service code with 43 @covers-tagged functions covering 43 of 43 formula columns, plus 213 tests.

Agent loop with hooks. A PreToolUse hook blocks edits to workbook/, harness/, golden/, decisions/ and .bob/. In a prompted guard test Bob attempted a diff edit to the grader and a shell write into it, and the hook blocked both. The hooks also fire inside subagents: the audit log records every subagent edit. PostToolUse runs a 200-policy smoke test after each edit to service/; during T03 it caught a blank-claims bug in one unit (18 wrong cells), and that subagent fixed it before finishing. The full harness then found 0 translation bugs.

Human decisions and review. Bob never decides a spreadsheet anomaly. For the 3 seeded anomalies, Bob drafted a brief citing the manual, the builder acting as pricing lead chose adopt-manual with tools/decide.py, and Bob implemented the decisions in T07. We reviewed every task and sent five findings back as follow-ups, all fixed by Bob: blank-cell equality and MIN/MAX helpers, an environment-variable read, an exception wrapper that hid crashes, an understated impact in one brief, and a misused out-of-scope file. Bob-authored lines: 4,151 of 16,861 non-generated lines.

Outcome: 430,000 cells compared, 0 unexplained, certificate GREEN; the mutation self-test caught 51 of 60.

What was not Bob. Claude Code, an AI coding agent, built the workbook generator, rating manual, LibreOffice oracle, harness, mapping tools, CI and site shell, so the agent being graded never wrote its own exam. It also drafted the .bob/ pack and these statements, which the builder reviewed and edited. ATTRIBUTION.md records every file's author, and Bob-authored commits carry a Bob-Task trailer.
