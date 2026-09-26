# Attribution ledger

Who wrote every file in this repository. SheetShift separates duties: **IBM Bob** builds the product under test (the service in `service/sheetshift_ho3/`, its tests, the anomaly briefs, `public/trace.js` and `public/verify.js`, and the run summary). **Claude Code**, an AI agent that is not a team member and cannot run Bob, built the exam: the harness, the mapping tools, the page shells, CI and drafts. **People** decide every anomaly, review and edit the drafts, run every Bob task, deploy and submit.

How this ledger is kept:
- A row is added when a file is first committed. "Reviewed by" is a handle (`m1`..`m4`), never a name or an email.
- Bob's rows name the task and member, for example `T03, m1`, and match the `Bob-Task: TNN (mN)` trailer of the commit that added the file. `tools/check_evidence.py --final` fails if a tracked file under `service/` is missing from this ledger or was not added by a Bob-Task commit.
- Generated files name the tool that writes them. They are excluded from the Bob-authored line ratio.
- `decisions/decisions.jsonl` is written by people only, one signed line per decision (the `by` field names the handle).

Drafted by Claude Code (AI agent) — scaffold; a member reviews it.

## Reserved paths (rows added when the files exist)

| Path | Author | Bob task / tool | Reviewed by | First commit |
|---|---|---|---|---|
| `service/sheetshift_ho3/**` (except `data/verify_sample_2026.json.gz`) | IBM Bob | T02–T08 | – | – |
| `tests/test_xlsem.py`, `tests/test_tables.py`, `tests/test_u1..u4*.py`, `tests/test_rater_order.py`, `tests/test_api.py` | IBM Bob | T02, T03, T04, T07 | – | – |
| `public/trace.js`, `public/verify.js` | IBM Bob | T10 | – | – |
| `docs/design/`, `docs/anomalies/`, `docs/notes/`, `docs/architecture.md`, `docs/how_it_works.md`, `docs/bob_run_summary.html` | IBM Bob | T01, T06, T09 | – | – |
| `decisions/decisions.jsonl` | People (per-line `by`) | `tools/decide.py` | – | – |
| `bob_sessions/*.png`, `bob_sessions/*_history.md` | People (screenshots and exports of Bob tasks) | per INDEX.md row | – | – |
| `audit/<handle>/*.jsonl`, `reports/run_log.jsonl` | Written by the Bob hooks in `.bob/hooks/` during Bob tasks | – | – | – |

## Files in the repository

| Path | Author | Bob task / tool | Reviewed by | First commit |
|---|---|---|---|---|
| `.bob/commands/sheetshift.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-map.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-plan.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-report.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-translate.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-triage.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/commands/shift-verify.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/custom_modes.yaml` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/_common.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/guard.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/post_edit.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/prompt_context.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/session_status.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/hooks/stop_report.py` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules-sheet-translator/translator.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules-sheet-triage/triage.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules/00-project.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules/10-cell-traceability.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules/20-excel-semantics.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules/30-protected-paths.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/rules/40-money-and-rounding.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/settings.json` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/equivalence-triage/SKILL.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/manual-adjudication/SKILL.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/traceability-report/SKILL.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/translate-sheet/SKILL.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/xlsx-dependency-map/SKILL.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.bob/skills/shift-report/SKILL.md` | IBM Bob IDE, automatic migration of `.bob/commands/shift-report.md` on first load (body unchanged) | – | m1 | pending |
| `.bob/skills/shift-translate/SKILL.md` | IBM Bob IDE, automatic migration of `.bob/commands/shift-translate.md` on first load (body unchanged) | – | m1 | pending |
| `.bob/skills/shift-triage/SKILL.md` | IBM Bob IDE, automatic migration of `.bob/commands/shift-triage.md` on first load (body unchanged) | – | m1 | pending |
| `.bob/skills/shift-verify/SKILL.md` | IBM Bob IDE, automatic migration of `.bob/commands/shift-verify.md` on first load (body unchanged) | – | m1 | pending |
| `.bobignore` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `.dockerignore` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.gitattributes` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.github/denylist.sha256` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.github/workflows/oracle.yml` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.github/workflows/pages.yml` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.github/workflows/verify.yml` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.gitignore` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.gitleaks.toml` | Claude Code (AI agent), scaffold | – | pending | pending |
| `.vercelignore` | Claude Code (AI agent), scaffold | – | pending | pending |
| `AGENTS.md` | Claude Code (AI agent) draft; a member reviews and edits | – | pending | pending |
| `ATTRIBUTION.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `DATA_SOURCES.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `Dockerfile` | Claude Code (AI agent), scaffold | – | pending | pending |
| `LICENSE` | Claude Code (AI agent), scaffold | – | pending | pending |
| `Makefile` | Claude Code (AI agent), scaffold | – | pending | pending |
| `PROVENANCE.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `README.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `api/index.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `bob_sessions/INDEX.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `bob_sessions/README.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `bob_sessions/roster.json` | Claude Code (AI agent), scaffold | – | pending | pending |
| `build/graph.json` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/lints.json` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/rate_tables.json` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/sheets/Calc.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/sheets/Calc_exceptions.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/units.json` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/units/U1.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/units/U2.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/units/U3.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/units/U4.md` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `build/workbook_values.json` | Generated by tools/dump_workbook.py (Claude Code) | `make map` | pending | pending |
| `docs/CONTRACT.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `docs/bob_prompts.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `docs/SCAFFOLD_STATUS.md` | Claude Code (AI agent), scaffold (integration check) | – | pending | pending |
| `golden/expanded_200.xlsx` | Generated by harness/ (Claude Code), recorded LibreOffice oracle | `make oracle` | pending | pending |
| `golden/inputs_2026.json.gz` | Generated by harness/ (Claude Code), recorded LibreOffice oracle | `make oracle` | pending | pending |
| `golden/oracle_2026_Calc.csv.gz` | Generated by harness/ (Claude Code), recorded LibreOffice oracle | `make oracle` | pending | pending |
| `golden/oracle_meta.json` | Generated by harness/ (Claude Code), recorded LibreOffice oracle | `make oracle` | pending | pending |
| `harness/EXPECTED_TREE_SHA256` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/__init__.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/_hash_tree.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/certify.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/common.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/compare.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/expand.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/export_sample.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/generate.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/lo_profile/registrymodifications.xcu` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/mutate.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/oracle_lo.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/patch_workbook.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/run.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/smoke.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/spotcheck.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/trace.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `harness/triage.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `manual/example_mutual_ho3_rating_manual.pdf` | Generated by tools/make_manual.py (Claude Code) | – | pending | pending |
| `manual/src/README.md` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/app.css` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/certificate.html` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/data/.gitkeep` | Claude Code (AI agent), scaffold; public/data/*.json are generated by tools/build_site_data.py | `make site` | pending | pending |
| `public/index.html` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/replay.html` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/site.js` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/trace.html` | Claude Code (AI agent), scaffold | – | pending | pending |
| `public/verify.html` | Claude Code (AI agent), scaffold | – | pending | pending |
| `requirements-dev.txt` | Claude Code (AI agent), scaffold | – | pending | pending |
| `requirements.txt` | Claude Code (AI agent), scaffold | – | pending | pending |
| `service/sheetshift_ho3/data/verify_sample_2026.json.gz` | Generated by harness/export_sample.py (Claude Code); read-only for Bob | `make sample` | pending | pending |
| `sheetshift.json` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tests/test_harness_selfcheck.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tests/test_no_env.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/__init__.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/build_site_data.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/check_evidence.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/check_modes.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/check_protected.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/check_video.sh` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/decide.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/denylist_scan.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/depgraph.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/dump_workbook.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/excel_crosscheck.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/gen_workbook.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/license_gate.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/lo_recalc.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/make_manual.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/tests/test_check_evidence.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/tests/test_excel_crosscheck.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/tests/test_guard.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `tools/units.py` | Claude Code (AI agent), scaffold | – | pending | pending |
| `vercel.json` | Claude Code (AI agent), scaffold | – | pending | pending |
| `workbook/SHA256SUMS` | Generated by tools/gen_workbook.py (Claude Code) | `make workbook` | pending | pending |
| `workbook/example_mutual_ho3_rater.xlsx` | Generated by tools/gen_workbook.py (Claude Code) | `make workbook` | pending | pending |
| `workbook/probe/stale_cache.xlsx` | Generated by tools/gen_workbook.py (Claude Code) | `make workbook` | pending | pending |
