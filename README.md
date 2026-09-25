# SheetShift: rating spreadsheets to verified code

**SheetShift uses IBM Bob to turn the spreadsheet that prices your policies into code you own, with tests. It then checks, cell by cell, that the code agrees with the spreadsheet, groups every difference, and traces each one to a signed decision or reports it as unexplained.** Bob does the translation. A grader that Bob's commits cannot change (CI rejects them) does the checking. A person decides every spreadsheet anomaly, citing the filed rating manual.

All data is synthetic. The carrier is **Example Mutual Insurance Co. (FICTIONAL)**, and the three anomalies in the demo workbook were seeded by the team on purpose.

> Draft README by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. Values in `[brackets]` are placeholders until the final run.

| | |
|---|---|
| Live app | [LIVE_APP_URL] (Vercel) |
| Static mirror | [PAGES_URL] (GitHub Pages, precomputed results) |
| Demo video | [VIDEO_URL] |
| Bob task evidence | [`bob_sessions/`](bob_sessions/) and [`bob_sessions/INDEX.md`](bob_sessions/INDEX.md) |
| Certificate | `reports/certificate.json` · `reports/certificate.html` (committed after the final run) |

## The result

<!-- headline:start (written by `python -m tools.build_site_data --readme` from reports/certificate.json; do not edit by hand) -->
**[C] cells compared: [E] identical to the workbook, [D] differing only in rows traced to [A] human-signed decisions, [U] unexplained.**

- Decision-patched workbook: [Cp] of [Cp] cells identical.
- Harness sensitivity: [K] of [M] mutants of Bob's code caught.
- A 20-quote spot check misses naive rounding [P20] of the time.
- Certificate status: [STATUS] · seed 2026 · 10,000 policies · oracle: LibreOffice 24.2, forced recalculation, recorded.
<!-- headline:end -->

- Time: one person hand-translating unit [Ux] took [Hman] min; Bob took [Hbob] min (n = 1).
- Bob-authored lines: [Lb] of [Lt] non-generated lines (`python3 tools/check_evidence.py`).

How to read it. Seed 2026 gives 10,000 generated policies, including boundary cases. Each one goes through the original workbook (recalculated once in LibreOffice with full recalculation forced) and through Bob's service, and all 43 output columns are compared: numbers within 1e-6, dates and text exactly, errors by code. A cell is **unexplained** when it differs in a row whose root cells no signed decision covers. A second comparison, against a copy of the workbook patched with the decisions, must match in every cell, so a decision cannot hide a translation bug.

## How it works

1. **Map.** `make map` dumps the workbook's formulas into 43 column rules, a dependency graph, four translation units and a lint report (`build/`). The lint finds the three seeded anomalies.
2. **Plan.** In Plan mode, Bob reads the workbook, the rating-manual PDF and the map, and is asked to write a service plan that flags every place the workbook and the manual disagree, without deciding them (`docs/design/service_plan.md`, task T01).
3. **Translate.** Bob spawns four subagents in parallel, one per unit. Each function is tagged `@covers("Calc!<col>", "<output>")`, so every workbook rule traces to code.
4. **Verify.** The harness compares the service with the recorded workbook values on 10,000 policies and groups mismatches by root cell. A hook is configured to re-run a smoke check after every edit Bob makes to the service; task T00 records whether hooks also fire inside subagents (`docs/notes/probe_*.md`).
5. **Triage.** Translation bugs go back to Bob. Spreadsheet anomalies go to a decision queue; Bob drafts a brief quoting the manual rule.
6. **Decide.** A teammate acting as pricing lead decides each anomaly with `tools/decide.py`, which refuses to run without a person at the terminal. Bob implements the decision.
7. **Certify.** `make certify` writes the certificate: both reconciliations, the mutation self-test, the spot-check odds, traceability, hashes of the workbook, code, grader, inputs and decisions, and the limits.

Custom modes restrict what Bob may edit, and a PreToolUse hook is configured to block edits and shell writes to the workbook, harness, golden data and decision log. The hook is a best-effort, fast check (T00 records whether it fires inside subagents); the enforcing control is CI (`tools/check_protected.py`), which rejects any Bob commit that touches those paths.

## Quick start

```
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements-dev.txt
make map                  # workbook -> build/ (deterministic)
make verify               # compare the service with the golden oracle (no LibreOffice needed)
make mutate spot certify  # mutation self-test, spot check, certificate
make site                 # public/data/*.json for the pages
python3 -m uvicorn api.index:app --reload   # the API; the pages are static files in public/
```

LibreOffice Calc is needed only to recompute the oracle (`make oracle patch`), which CI does when `workbook/` or `decisions/` changes.

API: `GET /api/health`, `GET /api/verify?n=200&sample_seed=7`, `POST /api/quote`, `GET /api/trace?cell=Calc!O`, OpenAPI at `/docs`. The app reads no environment variables and stores nothing.

## Limits

- Evidence over sampled and boundary inputs, not a formal proof.
- The oracle is LibreOffice 24.2 with full recalculation forced, not Excel. Excel parity is unverified unless the optional cross-check (`tools/excel_crosscheck.py`) is run.
- Macros and VBA are not supported, and `.xlsm` files are never opened.
- Volatile functions (NOW, TODAY, RAND, OFFSET, INDIRECT) are reported as unsupported.
- External links, array and dynamic-array formulas, data tables and iterative calculation are out of scope.
- The whole-book Summary cells are declared out of scope for single-quote rating.
- The three anomalies in the demo workbook were seeded by the team, and all data is synthetic.

## Who did what

SheetShift separates duties, and this repository records who wrote each file ([ATTRIBUTION.md](ATTRIBUTION.md)).

- **IBM Bob** writes the rating service (`service/sheetshift_ho3/`), its tests, every `@covers` tag, the anomaly briefs, every translation-bug fix, the implementation of each decision, the trace and verify page scripts, and the run summary. Each Bob commit carries a `Bob-Task: TNN (mN)` trailer, and each task has a screenshot in `bob_sessions/`.
- **Claude Code**, an AI coding agent from Anthropic, is not a team member and cannot run Bob. It wrote the grader and tooling: the workbook generator, the mapping tools, the equivalence harness and its golden data, the synthetic rating manual, the page shells and styles, the API entry-point stub, CI, the Dockerfile, and drafts of the Bob pack (`.bob/`, `AGENTS.md`), this README and other documents, which people review and edit. It never writes service code, service tests, Bob's design notes or briefs, the page scripts, or decisions.
- **People** choose the defaults, review the Bob pack, run and approve every Bob task, decide every anomaly, record the video, edit the statements, deploy and submit.

## Running it elsewhere

- **Vercel** (primary): `public/` is served statically and `api/index.py` serves the API. Vercel has no build step, so before each deploy run `make certify site` on Bob's service and commit `reports/certificate.*` and `public/data/*.json` (CI rejects committed results from a stand-in service); `vercel.json` routes `/api/*`, `/docs` and `/openapi.json` to it. Until Bob's `api.py` lands, `api/index.py` serves a stub whose health check reports `"status": "stub"`.
- **GitHub Pages** (fallback): `.github/workflows/pages.yml` publishes the same pages with precomputed results and an "API offline" banner.
- **Container / IBM Code Engine** (documented, not deployed): `docker build -t sheetshift .` then `docker run -p 8080:8080 sheetshift`. The image holds only `api/`, `service/` and the published reports, runs as a non-root user and needs no secrets.

## Licence

MIT; see [LICENSE](LICENSE). Runtime dependencies are permissive only (checked by `tools/license_gate.py`); LibreOffice is an external tool and is not distributed. Provenance and data sources: [PROVENANCE.md](PROVENANCE.md), [DATA_SOURCES.md](DATA_SOURCES.md).
