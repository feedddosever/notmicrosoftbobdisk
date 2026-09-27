---
marp: true
size: 16:9
paginate: true
title: SheetShift
description: Rating spreadsheets to verified code, built with IBM Bob
style: |
  section { font-family: "Atkinson Hyperlegible", "Segoe UI", Arial, sans-serif; font-size: 27px; color: #16212b; background: #f7f8f6; padding: 56px 72px; }
  h1, h2 { font-family: "Archivo", "Segoe UI", Arial, sans-serif; color: #0c3b37; letter-spacing: -0.01em; }
  h1 { font-size: 64px; margin-bottom: 8px; }
  h2 { font-size: 42px; border-bottom: 3px solid #0c6a60; padding-bottom: 8px; }
  code { font-family: "JetBrains Mono", Consolas, monospace; background: #e6ece9; padding: 1px 6px; border-radius: 4px; font-size: 0.85em; }
  strong { color: #0c6a60; }
  table { font-size: 22px; border-collapse: collapse; }
  th, td { border-bottom: 1px solid #c9d3cf; padding: 6px 10px; text-align: left; }
  footer { color: #5d6b72; font-size: 16px; }
  section.lead { background: #0c3b37; color: #f2f5f3; }
  section.lead h1 { color: #ffffff; }
  section.lead strong { color: #8fe0d4; }
footer: "SheetShift · IBM Bob 2.0 Hackathon · synthetic data for a fictional carrier"
---

<!-- _class: lead -->
<!-- Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. Numbers come from reports/certificate.json and bob_sessions/INDEX.md. -->

# SheetShift

Your rating spreadsheet, as code you own, checked cell by cell. Built with **IBM Bob**.

**430,000 cells compared · 409,539 identical · 20,461 traced to 3 signed decisions · 0 unexplained**

---

## The problem

- Premiums are often computed by a **rating workbook**. An engineer re-codes it by hand for the policy system, then spot-checks a few quotes.
- The dangerous errors are rare. In our workbook a hard-coded tax and a missing credit cap each touch **1 policy in 10,000**: a 20-quote spot check misses each **99.8%** of the time.
- Python's `round()` instead of Excel's `ROUND` changes **2,552 of 10,000** quotes.
- Field audits found errors in at least 86% of the spreadsheets they examined (Panko).
- In May 2026 Washington fined an insurer $55,000 for incorrect charges on 585 policies.

---

## The workflow, and the Bob feature behind each step

| Step | What happens | Bob feature |
|---|---|---|
| Map | Formulas → dependency graph, 4 units, 3 lints | Command + skill |
| Plan | Reads the .xlsx formulas and the PDF manual; flags disagreements | **Plan mode**, native document reading |
| Translate | 4 units in parallel, every function `@covers` its cells | **Subagents**, Sheet Translator mode |
| Verify | 430,000 cells vs the recorded workbook | PostToolUse smoke after every edit, even in subagents |
| Triage + briefs | Classify groups; brief each anomaly from the PDF | Sheet Triage and Sheet Analyst modes |
| Decide | A person chooses, citing the manual | Hook blocks Bob from the decision log |
| Certify | Certificate, traceability, mutation self-test | CI re-runs it on every push |

---

## Governed autonomy

- **Custom modes:** the translator edits only `service/` and `tests/`; the analyst writes only notes.
- **PreToolUse hook:** blocks edits to the workbook, grader, golden data and decision log. In a prompted guard test Bob tried a diff edit and a shell write into the grader; the hook blocked both.
- **CI is the enforcing control:** it rejects any Bob-tagged commit that touches those paths and re-hashes the grader.
- **Separation of duties:** Bob builds the service, Claude Code built the exam, a person decides.

---

## Evidence

- Original workbook: **430,000** cells, **409,539** identical, **20,461** in rows traced to **3** decisions, **0** unexplained.
- Decision-patched workbook: **430,000 of 430,000** cells identical, so no decision hides a translation bug.
- Mutation self-test: **51 of 60** injected bugs caught; the 9 survivors are labelled by a person (8 cannot change any output, 1 input-domain gap).
- Traceability: **43 of 43** formula columns mapped to a tagged function; 5 whole-book totals declared out of scope.
- Oracle: LibreOffice 24.2 with forced recalculation, recorded; not cross-checked against Excel.
- Limits: sampled inputs, not a formal proof; no macros or volatile functions; anomalies seeded by us.

---

## Demo

1. Bob in Plan mode reads a formula whose cached value (99) no longer matches the formula (7.5).
2. Four subagents translate the rating chain in parallel.
3. A hook's smoke check catches a translation bug mid-task; the subagent fixes it. A person decides three anomalies; Bob implements them.
4. Live: pick a workbook cell on `/trace` and see the function; run `/verify` on recorded policies.

**https://sheetshift-rho.vercel.app**

---

## Business value

- **Buyers:** pricing and actuarial IT at carriers and MGAs, whose rates live in workbooks.
- **Why now:** AI made translation cheap. Verification is the bottleneck, and regulators ask for evidence.
- **Pricing idea:** per workbook migrated, plus per verification run in CI.
- **Different from the alternatives:** Excel-as-an-API platforms keep you on Excel; spreadsheet copilots edit the sheet. SheetShift gives owned code plus a certificate, traceability and a signed decision log.

---

## Roadmap

- Excel cross-check at scale, next to the LibreOffice oracle
- More Excel functions and whole-book (Summary) rules
- The equivalence check as a required CI gate on every rate filing
- Batches of workbooks, one certificate each
- An offline mode that runs the translated service in the browser

---

## Who did what

- **IBM Bob:** the rating service, its API and tests, every `@covers` tag, the translation-bug fix, the service plan, triage note and anomaly briefs, and the decisions' implementation. **4,151 of 16,861** non-generated lines. About **16** Bobcoins over **8** tasks.
- **Claude Code** (AI coding agent): the grader, the mapping tools, the synthetic workbook and manual, CI, the site shell, and drafts of the Bob pack and these slides.
- **The builder:** ran and approved every Bob task, decided every anomaly, recorded the video, submitted.

Repository: **github.com/feedddosever/notmicrosoftbobdisk** · Evidence: `bob_sessions/` · Attribution: `ATTRIBUTION.md`
