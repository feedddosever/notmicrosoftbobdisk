# Protected paths (separation of duties)

**Reading is always allowed and expected.** Read the workbook (with `office_read`), the manual PDF, `build/`, `harness/`, `docs/` and every other file freely; your task needs them. The rule below is about **writing** only.

Bob builds the service. The harness, the workbook and the golden data are the exam, and people make the decisions. Bob never edits (writes, modifies, moves or deletes):

- `workbook/`, `manual/`: the customer's workbook and the filed manual.
- `harness/`, `golden/`, `tools/`, `build/`: the exam and its generated map. Regenerate `build/` only with `python3 tools/dump_workbook.py`.
- `decisions/`: only people write decisions, through `tools/decide.py`. Bob never runs it.
- `.bob/`, `.github/`, `AGENTS.md`, `.bobignore`, `sheetshift.json`, `Makefile`, `docs/CONTRACT.md`, `ATTRIBUTION.md`, `PROVENANCE.md`: configuration and records.
- `reports/*.json`, `reports/*.html`, `audit/`: generated evidence. Bob writes only `reports/notes/`.
- `service/sheetshift_ho3/data/verify_sample_2026.json.gz`, `tests/test_harness_selfcheck.py`, `tests/test_no_env.py`.

A PreToolUse hook blocks these writes and CI rejects any commit that changes them. If the harness looks wrong, write `docs/notes/HARNESS-<n>.md` explaining why, then stop.

When the person explicitly says a request is a **guard test**, make the tool call exactly as asked instead of refusing: the hook is the thing being tested, and it will block the call. Report the hook's message verbatim.
