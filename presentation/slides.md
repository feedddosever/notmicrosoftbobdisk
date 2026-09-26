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
<!-- Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. Numbers in [brackets] come from reports/*.json only. -->

# SheetShift

Your rating spreadsheet, as code you own, checked cell by cell. Built with **IBM Bob**.

**[C] cells compared · [E] identical · [D] traced to [A] signed decisions · [U] unexplained**

---

## The problem

- Premiums are often computed by a **rating workbook**. An engineer re-codes it by hand for the policy system, then spot-checks a few quotes.
- Translations fail quietly. On our workbook, Python's `round()` instead of Excel's `ROUND` changes **[R0] of 10,000** premiums by a cent, and a 20-quote spot check misses that **[P20]%** of the time.
- Field audits find errors in most spreadsheets they examine (Panko).
- Charged premiums that drift from filed rates bring fines and restitution.

---

## The workflow, and the Bob feature behind each step

| Step | What happens | Bob feature |
|---|---|---|
| Map | Formulas → dependency graph, 4 units, 3 lints | Command + skill |
| Plan | Reads the .xlsx formulas and the PDF manual; flags disagreements | **Plan mode**, native document reading |
| Translate | 4 units in parallel, every function `@covers` its cells | **Subagents**, Sheet Translator mode |
| Verify | [C] cells vs the recorded workbook | Sheet Verifier mode, PostToolUse smoke |
| Triage + briefs | Fix translation bugs; brief each anomaly | **Parallel tasks**, rollback |
| Decide | A person chooses, citing the manual | Hook blocks Bob from the decision log |
| Certify | Certificate, traceability, one-page summary | `/review`, HTML summary |

---

## Governed autonomy

- **Custom modes:** the translator edits only `service/` and `tests/`; the analyst writes only notes.
- **PreToolUse hook:** blocks edits to the workbook, grader, golden data and decision log. In a prompted guard test Bob tried a diff edit and a shell write into the grader; the hook blocked both.
- **CI is the enforcing control:** it rejects any Bob-tagged commit that touches those paths and re-hashes the grader.
- **Separation of duties:** Bob builds the service, Claude Code built the exam, a person decides.

---

## Evidence

- Original workbook: **[C]** cells, **[E]** identical, **[D]** in rows traced to **[A]** decisions, **[U]** unexplained.
- Decision-patched workbook: **[Cp] of [Cp]** cells identical, so no decision hides a translation bug.
- Mutation self-test: **[K] of [M]** injected bugs caught; [KB] only by boundary rows.
- Traceability: **[T1] of [T2]** workbook rules mapped to code or declared out of scope.
- Excel cross-check: [x of y cells equal, Excel version] (or "not run; LibreOffice oracle").
- Limits: sampled inputs, not a formal proof; no macros or volatile functions; anomalies seeded by us.

---

## Demo

1. Bob in Plan mode reads a formula whose cached value (99) no longer matches the formula (7.5).
2. Four subagents translate the rating chain in parallel.
3. Triage and anomaly briefs run as two Bob tasks at once.
4. Live: pick a workbook cell on `/trace` and see the function; run `/verify` on recorded policies.

**[APP_URL]**

---

## Business value

- **Buyers:** pricing and actuarial IT at carriers and MGAs. US MGA premium was $114.1B in 2024 (Conning). Confirm before submitting.
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

- **IBM Bob:** the rating service, its tests, every `@covers` tag, every translation-bug fix, the anomaly briefs, the page scripts and the run summary. **[Lb] of [Lt]** non-generated lines. **[X]** Bobcoins over **[T]** tasks.
- **Claude Code** (AI coding agent): the grader, the mapping tools, the synthetic workbook and manual, CI, the site shell, and drafts of the Bob pack and these slides.
- **The builder:** ran and approved every Bob task, decided every anomaly, recorded the video, submitted.

Repository: **[REPO_URL]** · Evidence: `bob_sessions/` · Attribution: `ATTRIBUTION.md`
