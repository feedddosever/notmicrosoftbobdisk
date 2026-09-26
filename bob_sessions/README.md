# bob_sessions: evidence of every IBM Bob task

This folder holds the evidence that IBM Bob did the work: one summary screenshot and one exported task session (Bob IDE's Export button) per task. It is **flat** (no subfolders), and `tools/check_evidence.py` checks it in CI.

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. Members edit it.

## File names

| What | Pattern | Example |
|---|---|---|
| Task summary screenshot | `<team>_taskNN_<desc>_<handle>_summary.png` | `teamslug_task03_translate_units_m1_summary.png` |
| Exported task session (scrubbed) | `<team>_taskNN_<desc>_<handle>_history.json` | `teamslug_task03_translate_units_m1_history.json` |
| Other screenshot (for example the Bobalytics view) | `<team>_misc_<desc>_<handle>.png` | `teamslug_misc_bobalytics_m1.png` |

- `<team>` is `team_slug` from `roster.json`: the registered lablab team name, lowercase letters and digits only.
- `NN` is the two-digit task number from `docs/bob_prompts.md` (T00 to T12). `<desc>` is lowercase letters, digits and underscores.
- `<handle>` is `m1` to `m4`. Handles only: no names, no emails.
- The screenshot regex is `^[a-z0-9]+_task\d{2}_[a-z0-9_]+_m[1-4]_summary\.png$`.

## Capturing a task (right after it finishes)

1. In Bob IDE open Tasks, open the task, and click its header to show the summary.
2. Screenshot the summary (the header with the token count and the Bobcoin cost must be in the picture) and save it as `<team>_taskNN_<desc>_<handle>_summary.png` in this folder. Crop out any email address, account name or notification.
3. Click **Export** in the task header. Bob saves `bob-task-<id>-<date>.json`; the repository root is a fine place for it (`bob-task-*.json` is git-ignored, because the raw file holds home paths).
4. Import it. This scrubs home paths and emails, writes the `_history.json` here, and adds or replaces the task's row in `INDEX.md` (below) from what the export records:
   ```
   python3 tools/import_bob_export.py bob-task-<id>-<date>.json --task T03 --desc translate_units --index
   ```
   Add `--status aborted|re-run|fallback` when it applies. `check_evidence.py` fails on home paths and on email addresses other than GitHub noreply addresses.
5. Commit Bob's work with the trailer `Bob-Task: TNN (mN)`, for example `Bob-Task: T03 (m1)`. Do not squash Bob commits. Then fill in the row's Commit column (a re-import keeps it).

## INDEX.md rows

One row per task, including T00 and every aborted, re-run or fallback task. Exactly one screenshot per row, and every screenshot in this folder must be named by a row.

| Column | Content |
|---|---|
| Task | `T03` |
| Member | `m1` |
| Mode | the Bob mode, for example `sheet-translator` |
| Subagents | how many subagents were spawned (0 if none) |
| Files changed | from `audit/<handle>/bob_edits.jsonl`, for example `service/sheetshift_ho3/units/*.py (8)` |
| Commit | the short SHA of the commit carrying `Bob-Task: TNN (mN)`, once committed |
| Gauge before / Gauge after | the Bobcoin gauge readings |
| Screenshot | the PNG file name in this folder |
| Export | the `_history.json` file name |
| Status | `done`, `aborted`, `re-run` or `fallback` |

## Task exports

> Export button: **yes** (T00, 26 Sep 2026). Bob IDE's task header exports one JSON file per task, `bob-task-<id>-<date>.json`, holding the task (modes, cost, context breakdown) and every message and tool call. `roster.json` records `exports_available: true`, so every row needs an export (checked with `--final`).

## Checking

```
python3 tools/check_evidence.py          # during the event: naming and consistency errors fail, gaps are warnings
python3 tools/check_evidence.py --final  # the Sun 09:00 gate: gaps fail too
```
