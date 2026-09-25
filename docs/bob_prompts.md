# Bob task prompts (T00–T12)

These are the prompts members paste into IBM Bob, one task at a time. Each task lists its mode, prompt, expected output, screenshot name and INDEX row.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. A member reviews it before T00.

> **Solo build (one person, handle `m1`).** Run the tasks in this order: T00, T01, T02, T03, then T05 and T06 as two Bob tasks running at the same time (start T05, open a new task for T06 while T05 works), then your own decisions, T07, T04, T08, T09, and T10 only if you have used fewer than 24 Bobcoins after T09. You act as pricing lead in the decision step. Per-task branches are optional when solo: commit each task on the integration branch with a `Bob-Task: TNN (m1)` trailer.

## Pre-flight checklist (every member, before T00)

- [ ] **Bob IDE 2.0.2 or later.** 2.0.3 is recommended. Versions 1.0.3 and 2.0.0 stop working on 30 Sep 2026.
- [ ] **Hackathon instance.** In Settings → General, select the provisioned instance **ibm-coding-challenge-uat** (region us-east). The guide also shows this name as `ibm-coding-challenge-xxx`. Check the coin balance and write it in INDEX.md.
- [ ] **Trust the folder.** Open the repo folder and trust it. Until you do, AGENTS.md, `.bob/` rules, skills, modes and hooks are all suspended.
- [ ] **git identity.** Use handles only, never a real name or a personal email:
  ```sh
  git config user.email <id>+<login>@users.noreply.github.com
  git config user.name m<N>
  git config sheetshift.handle m<N>
  ```
- [ ] **Python.** `python3 --version` must be 3.8 or later on PATH; the service and harness target 3.11.
  - On Windows, install python.org Python with `python3` on PATH, or run Bob in WSL. The Microsoft Store stub exits 9009, and then the guard does not run at all.
  - Then create and activate a virtual environment and install the dev dependencies into it:
    - macOS, Linux, WSL: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements-dev.txt`
    - Windows (PowerShell): `py -3 -m venv .venv; .venv\Scripts\Activate.ps1; python -m pip install -r requirements-dev.txt`
  - In Bob, select `.venv` as the Python interpreter and open a new terminal. Confirm that `python3 -c "import openpyxl, pytest"` exits 0 there before T00; Bob's commands call bare `python3`.
  - On Windows, keep Git from converting line endings: the repo's `.gitattributes` forces LF. If you cloned before that file existed, run `git rm --cached -r . && git reset --hard` once (or re-clone).
- [ ] **Workspace.** Open the repo folder itself as the Bob workspace (not a parent folder and not a multi-root workspace). The hooks run `python3 .bob/hooks/...` relative to it.
- [ ] **Bob loads the pack.**
  - Settings → Modes lists Sheet Analyst, Sheet Translator, Sheet Verifier and Sheet Triage.
  - Settings → Hooks lists 5 hooks.
  - Typing `/shift` shows the 6 `shift-*` commands; `/sheetshift` is the seventh.
- [ ] **Auto-approve.**
  - Read and edit only, turned on before T03.
  - Execute calls and subagent spawns stay manual, so they appear on video.
  - MCP servers are off.
- [ ] **Branch.** Create `bob/tNN-<desc>` from the integration branch before each task. A person merges it back.
- [ ] **Fresh task.** Start a new Bob task for each row below, and `@`-mention exact files.
- [ ] **Record.** For rows marked *record*, start OBS (1080p30) before pasting the prompt.

## Screenshot procedure (right after every task, including aborted and re-run ones)

1. In the Bob chat panel, open **Tasks** and select the task. If needed, choose **All** to see tasks from every workspace.
2. Click the **task header**. The task session consumption summary appears.
3. Take a **PNG** screenshot of the summary and crop out any email address.
4. Save it as `bob_sessions/<team>_taskNN_<desc>_<handle>_summary.png`. `<team>` is the registered team name as a lowercase slug, and `<handle>` is `m1`..`m4`. Example: `bob_sessions/<team>_task03_translate_m1_summary.png`.
5. If an Export button exists, save the export as `bob_sessions/<team>_taskNN_<desc>_<handle>_history.md`. Then scrub home paths and check the folder:
   ```sh
   sed -E -i.bak 's#(/Users|/home|[A-Za-z]:(\\){1,2}Users)[/\\]+[^/\\]+#<home>#g' bob_sessions/*_history.md && rm -f bob_sessions/*_history.md.bak
   python3 tools/check_evidence.py --no-blame
   ```
6. Add one row to `bob_sessions/INDEX.md`, with the fields below.

**INDEX.md row fields:**

| task | member | mode | subagents spawned | files changed (from audit/) | commit SHA | gauge before | gauge after | screenshot path | export path | aborted / re-run |
|---|---|---|---|---|---|---|---|---|---|---|

Coin figures below are estimates. Recalibrate them after T00 and T01 from the gauge readings in INDEX.md.

---

## T00 — probes (every member)

- **Mode:** Ask for steps 1–3, Agent for steps 4–6, Sheet Translator for step 7, Sheet Analyst for step 8. **Branch:** `bob/t00-probes-<handle>`. **Est.** 0.3–0.8 coins.
- **Screenshot:** `bob_sessions/<team>_task00_probes_<handle>_summary.png`

Paste one at a time. Log the gauge before and after step 2.

```
(1) Ask: @workbook/probe/stale_cache.xlsx What is the formula in Sheet1!D2 and what value is displayed? Reply exactly: FORMULA: … VALUE: …
(2) Ask: @workbook/example_mutual_ho3_rater.xlsx How many rows does Calc have?
(3) Ask: @manual/example_mutual_ho3_rating_manual.pdf Quote rule R-205's row for a $10,000 deductible.
(4) Agent: Create harness/_probe.txt containing x.
(4b) Agent: In harness/common.py, change the first docstring line to x by editing it, not rewriting the file.
(4c) Agent: Run the shell command: echo x > harness/_probe3.txt
(5) Agent: Spawn one general subagent that creates harness/_probe2.txt containing x.
(6) Agent: Create service/_probe_ok.txt containing x, then delete it.
(7) Sheet Translator: Create tests/_probe_mode.json containing {} and then delete it. Then create docs/_probe_mode.md containing x.
(8) Sheet Analyst: Write docs/notes/probe_<handle>.md recording the answers to steps 1–3, the gauge difference (<paste it>), the tool you used in each of steps 4–7 and whether it was blocked (and by what message), whether the subagent's write in step 5 was blocked, and the step 7 result.
```

Also check:
- that the 4 modes and 5 hooks load;
- whether an Export button exists;
- in steps 4b and 4c, that the diff edit and the shell write are both blocked (they exercise the edit and shell tools, not only `write_file`);
- in step 5, whether the hook and the mode's fileRegex fire inside the subagent;
- in step 7, that the JSON edit is allowed and the `.md` edit is refused by the mode (not by the hook).

If any of steps 4, 4b, 4c or 5 is not blocked, stop, restore the file with `git checkout -- harness/` (and delete any `harness/_probe*`), and tell the lead before any other task runs.

If the step 7 JSON edit is refused, a person changes `^(\./)?` to `(^|/)` in `.bob/custom_modes.yaml` and re-checks.

- **Expected output:**
  - `docs/notes/probe_<handle>.md` (step 8) records every answer, the gauge difference, the tool names, whether the hook and fileRegex fired in the subagent, and the step 7 result. (`audit/` is in `.bobignore`, so a person, not Bob, reads the audit files below.)
  - `audit/<handle>/hook_payload_sample.json` holds one entry per `event:tool`, so every tool name Bob used and its input key names are recorded. A person checks the read-only tool names against `READ_ONLY` in `.bob/hooks/_common.py` (the hooks have no matcher, so every other tool is guarded) and corrects the list if needed.
  - `audit/<handle>/hook_events.jsonl` shows exactly 4 blocks (steps 4, 4b, 4c and 5, all `harness/`, reason protected path or redirect into a protected path; only 3 if hooks do not fire in subagents). Every other line is an allow.

## T01 — plan (*record*)

- **Mode:** Plan. **Branch:** `bob/t01-plan`. **Est.** 2–4 coins.
- **Screenshot:** `bob_sessions/<team>_task01_plan_<handle>_summary.png`

```
You are onboarding onto SheetShift. Read @AGENTS.md, @build/sheets/Calc.md, @build/sheets/Calc_exceptions.md, @build/units.json, @build/lints.json, the workbook @workbook/example_mutual_ho3_rater.xlsx and the manual @manual/example_mutual_ho3_rating_manual.pdf. Write docs/design/service_plan.md with: (1) one section per unit U1–U4: each column's formula, precedents, Excel hazards (cite .bob/rules/20-excel-semantics.md), function name and @covers tag; (2) the interface quote(policy)->dict of 43 outputs and the shared c dict; (3) a FLAGS table of every place the workbook disagrees with the manual or a lint, with rule numbers — do not decide them; (4) for 5 formulas, compare what you read natively in the .xlsx with Calc.md and say whether native reading showed formulas or only values; (5) out-of-scope items; (6) 'Onboarding amendments': up to 5 changes you would make to AGENTS.md. Do not write code.
```

- **Expected output:** `docs/design/service_plan.md` with FLAGS for A1–A3. A person reviews the FLAGS and applies the accepted AGENTS.md amendments, crediting T01.

## T02 — Excel semantics, tables, traceability registry

- **Mode:** Sheet Translator. **Branch:** `bob/t02-xlsem`. **Est.** 1.5–2.5 coins.
- **Screenshot:** `bob_sessions/<team>_task02_xlsem_<handle>_summary.png`

```
Using @.bob/rules/20-excel-semantics.md, @.bob/rules/10-cell-traceability.md, @docs/CONTRACT.md (section 4) and @docs/design/service_plan.md, write service/sheetshift_ho3/__init__.py (empty) and service/sheetshift_ho3/xlsem.py containing:
(1) class XLError(Exception) with attribute .code (for example "#N/A", "#NUM!", "#DIV/0!"); two XLError values are equal when their codes are equal, and repr shows the code;
(2) STEPS = [], the traceability registry;
(3) a decorator covers(cell, output_name) that appends {"cell": cell, "name": output_name, "fn": f.__name__, "file": <path of the defining file relative to the repo root, computed from xlsem.py's own location (two directories above it), never from the current directory; forward slashes>, "line": f.__code__.co_firstlineno} to STEPS and returns f unchanged;
(4) the helpers xround, xroundup, band, exact, text_eq, n0, edate, yearfrac_basis3, datedif_y, iferror; every helper except iferror returns an XLError argument unchanged; iferror(x, alt) returns alt when x is an XLError.
Write tests/test_xlsem.py with every probe value in the rules file, plus a test that one @covers-decorated function adds exactly one STEPS entry with those five keys and a repo-relative file.
Copy build/rate_tables.json to service/sheetshift_ho3/data/rate_tables.json with a shell cp. Write service/sheetshift_ho3/tables.py with exactly the API in @docs/CONTRACT.md section 4: table(key) -> {"ref","header","rows"} with keys exactly as in the JSON's "tables" object; rows(ref) for any rectangular range inside one table (resolved through each table's "ref"); column(ref) for a one-column range such as 'RateTables!$B$13:$B$16'; scalar(name). Write tests/test_tables.py asserting the copy is byte-identical to build/rate_tables.json and testing each of the four functions on one range from build/units/U1.md. Run python3 -m pytest -q and show the result.
```

- **Expected output:** `xlsem.py` (XLError, covers, STEPS and helpers), `tables.py`, `data/rate_tables.json`, and passing `tests/test_xlsem.py` and `tests/test_tables.py`.

## T03 — parallel translation (*record continuously*)

- **Mode:** Sheet Translator. **Branch:** `bob/t03-translate`. **Est.** 3–6 coins (recalibrate).
- **Screenshot:** `bob_sessions/<team>_task03_translate_<handle>_summary.png`. Also capture 5 s of the subagent panel with its cost header.

```
/shift-translate all
```

- **Expected output:** 4 unit modules with tests, `rater.py` and `tests/test_rater_order.py`. Never re-run T03 just for footage.

## T04 — API

- **Mode:** Sheet Translator. **Branch:** `bob/t04-api`. **Est.** 1.5–2.5 coins.
- **Screenshot:** `bob_sessions/<team>_task04_api_<handle>_summary.png`

```
Write service/sheetshift_ho3/api.py (FastAPI; the only non-stdlib file): GET /api/health (commit SHA and certificate hash read from reports/certificate.json, env_vars: 0), POST /api/quote (pydantic model of the 14 Policies inputs; all 43 outputs; errors as strings like '#N/A'), GET /api/verify?n=&sample_seed= (n≤500 rows sampled from data/verify_sample_2026.json.gz; compare with tolerance 1e-6, errors by code; include the oracle string from the file), GET /api/trace?cell= and ?function=. No environment variables, no harness import. Add tests/test_api.py using TestClient.
```

- **Expected output:** `api.py` and `tests/test_api.py`.

## T05 — triage (*record*; runs in parallel with T06 on a different member)

- **Mode:** Sheet Triage. **Branch:** `bob/t05-triage`. **Est.** 2–4 coins.
- **Screenshot:** `bob_sessions/<team>_task05_triage_<handle>_summary.png`

```
/shift-verify then /shift-triage. For each group in @reports/mismatches.json state root cell, signature, precision and the harness class. Fix translation bugs one group at a time; after each fix read reports/smoke_last.json (field line) with the read tool, or run python3 -m harness.smoke --unit <U>. If a fix makes things worse, say so and I will roll back. Write reports/notes/triage_1.md. Do not touch tolerance or protected paths.
```

- **Expected output:** fixes, `reports/notes/triage_1.md`, and possibly a rollback (show it on video).

## T06 — anomaly briefs (in parallel with T05)

- **Mode:** Sheet Analyst. **Branch:** `bob/t06-briefs`. **Est.** 1–2 coins.
- **Screenshot:** `bob_sessions/<team>_task06_briefs_<handle>_summary.png`. Also capture 5 s of the task panel showing two tasks running.

```
For each PENDING entry in @reports/decision_queue.json, use the manual-adjudication skill with @manual/example_mutual_ho3_rating_manual.pdf and write docs/anomalies/D-00N.md. Quote the governing rule verbatim with number and page. List only the options allowed in the queue. Recommend; do not decide.
```

- **Expected output:** briefs `docs/anomalies/D-001.md` to `D-003.md`.

## People step — decisions (no Bob)

A person acting as pricing lead (when solo, you) runs `tools/decide.py` in a terminal for each anomaly, for example:

```
python3 tools/decide.py D-001 --option adopt-manual --by m1 --rule R-205 --why "Manual includes $10,000 band; workbook range truncated"
```

Claude Code then runs `make patch` to produce the patched oracle. There is no screenshot, because this is not a Bob task. Record the decision IDs in INDEX.md.

## T07 — apply decisions

- **Mode:** Sheet Translator. **Branch:** `bob/t07-decisions`. **Est.** 1–2 coins.
- **Screenshot:** `bob_sessions/<team>_task07_decisions_<handle>_summary.png`

```
Read @decisions/decisions.jsonl. Implement each decision (adopt-manual → the manual rule; keep-workbook → keep the column rule; escalate → no code change; add {"cell": "Calc!<col>" (the column key from build/graph.json rule_order, not the queue cell), "reason": "...", "decision": "D-00N"} to service/sheetshift_ho3/OUT_OF_SCOPE.json) with one test per decision. Then /shift-verify and quote original.unexplained_cells, original.decided_cells and patched.unexplained_cells from reports/last_run.json.
```

- **Expected output:** unexplained cells `[U]` = 0 is the target.

## T08 — code review (*record*)

- **Mode:** Agent, then `/review`. **Branch:** `bob/t08-review`. **Est.** 2–4 coins. Solo: 3 or fewer, scoped to `service/sheetshift_ho3/units/` via Settings → Bob Findings.
- **Screenshot:** `bob_sessions/<team>_task08_review_<handle>_summary.png`

```
/review
```

Compare the default branch against `bob/…`, include uncommitted changes, and click Start Review. For each finding, choose Fix with Bob or Dismiss, and give a reason. Then run `/shift-verify`.

- **Expected output:** the Findings panel, with every finding resolved.

## T09 — report

- **Mode:** Sheet Verifier. **Branch:** `bob/t09-report`. **Est.** 1.5–2.5 coins.
- **Screenshot:** `bob_sessions/<team>_task09_report_<handle>_summary.png`

```
/shift-report. After python3 -m harness.certify finishes, (1) create a single self-contained HTML summary of this SheetShift run and save it as docs/bob_run_summary.html: certificate numbers quoted exactly from reports/certificate.json, the decision table, traceability coverage, limits; (2) write docs/architecture.md (the data flow, one diagram in text) and docs/how_it_works.md (under 250 words, for the README). Quote numbers exactly.
```

- **Expected output:** `docs/bob_run_summary.html`, `docs/architecture.md` and `docs/how_it_works.md`.

## T10 — page scripts (core for teams of 2+, stretch for solo)

- **Mode:** Agent. **Branch:** `bob/t10-pagejs`. **Est.** 1.5–3 coins.
- **Screenshot:** `bob_sessions/<team>_task10_pagejs_<handle>_summary.png`

```
Write public/trace.js and public/verify.js for the existing public/trace.html and verify.html. trace.js: load data/traceability.json and data/graph.json; a cell picker shows functions with GitHub file:line links and tests; a function picker shows its cells. verify.js: call /api/verify?n=200&sample_seed=<input>; render matches, tolerance, oracle string and any mismatch with its class; if /api fails, load data/verify_sample_results.json and show the offline banner. No frameworks, no external requests.
```

- **Expected output:** `public/trace.js` and `public/verify.js`.

## T11 — second workbook (stretch)

- **Mode:** Agent for map and plan, Sheet Translator for translation. **Branch:** `bob/t11-secondbook`. **Est.** 4–7 coins.
- **Screenshot:** `bob_sessions/<team>_task11_secondbook_<handle>_summary.png`

**Not ready to run.** The command pack is built for the HO-3 workbook: `/shift-map` writes the committed `build/`, `/shift-plan` names the HO-3 manual and `/shift-translate` writes `service/sheetshift_ho3/`. Before T11 starts, Claude Code prepares `build/<name>/`, the layout file `sheetshift.second.json` and an empty package `service/<package>/`, and checks that `harness.smoke` and `harness.run` can point at them. Bob then runs only the plan and translate steps against those paths, with a prompt written at that time. Do not run `/sheetshift` on a second workbook: it overwrites `build/` (CI's `make map && git diff --exit-code build/` then fails) and the HO-3 service.

- **Expected output:** a second certificate. Claude Code generates the workbook, `sheetshift.second.json` and the second build folder.

## T12 — FLAG gap check (team of 4)

- **Mode:** Sheet Analyst. **Branch:** `bob/t12-flaggaps`. **Est.** 0.5–1 coin.
- **Screenshot:** `bob_sessions/<team>_task12_flaggaps_<handle>_summary.png`

```
Review @docs/design/service_plan.md FLAGS against @reports/traceability.json and @docs/anomalies/. List any FLAG not resolved by a decision or a code comment in docs/notes/flag_gaps.md.
```

- **Expected output:** `docs/notes/flag_gaps.md`.

---

## Assignment by team size

Every member runs T00 and at least two further tasks. When the team has at least 2 members, T05 and T06 run on different members.

| Size | m1 | m2 | m3 | m4 |
|---|---|---|---|---|
| 1 | T00, T01, T02, T03, T05, T06 (parallel), T07, T04, T08, T09; T10 only if the gauge is under 24 after T09 | – | – | – |
| 2 | T00, T01, T03, T06, T09, T10 | T00, T02, T04, T05, T07, T08 | – | – |
| 3 | T00, T01, T03, T09 | T00, T02, T05, T07, T11 | T00, T04, T06, T08, T10 | – |
| 4 | T00, T01, T03 | T00, T02, T05, T07 | T00, T04, T08, T10 | T00, T06, T09, T11, T12 |

**Stop rules**
- If any member's gauge is over 60% by Sat 12:00 (70% solo), cancel T11 and T12.
- If T03 costs more than 10 coins, T08 becomes a single-file review.
- Solo only: if the gauge passes 24 before T07, skip T08 and fold T09 into T07's last turn.
