# bob_sessions: evidence of every IBM Bob task

This folder holds the evidence that IBM Bob did the work: one summary screenshot per task and, if Bob IDE has an Export button, one exported task report per task. It is **flat** (no subfolders), and `tools/check_evidence.py` checks it in CI.

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md. Members edit it.

## File names

| What | Pattern | Example |
|---|---|---|
| Task summary screenshot | `<team>_taskNN_<desc>_<handle>_summary.png` | `teamslug_task03_translate_units_m1_summary.png` |
| Exported task report | `<team>_taskNN_<desc>_<handle>_history.md` | `teamslug_task03_translate_units_m1_history.md` |
| Other screenshot (for example the Bobalytics view) | `<team>_misc_<desc>_<handle>.png` | `teamslug_misc_bobalytics_m1.png` |

- `<team>` is `team_slug` from `roster.json`: the registered lablab team name, lowercase letters and digits only.
- `NN` is the two-digit task number from `docs/bob_prompts.md` (T00 to T12). `<desc>` is lowercase letters, digits and underscores.
- `<handle>` is `m1` to `m4`. Handles only: no names, no emails.
- The screenshot regex is `^[a-z0-9]+_task\d{2}_[a-z0-9_]+_m[1-4]_summary\.png$`.

## Capturing a task (right after it finishes)

1. In Bob IDE open Tasks, open the task, and click its header to show the summary.
2. Screenshot the summary. Crop out any email address, account name or notification.
3. If the Export button exists, export the task report and scrub it before adding it:
   `sed -E -i.bak 's#(/Users|/home|[A-Za-z]:(\\){1,2}Users)[/\\]+[^/\\]+#<home>#g' <file> && rm -f <file>.bak` (works with GNU and BSD/macOS sed). Then remove any email address by hand. `check_evidence.py` fails on home paths and on email addresses other than GitHub noreply addresses.
4. Add a row to `INDEX.md` (below).
5. Commit Bob's work with the trailer `Bob-Task: TNN (mN)`, for example `Bob-Task: T03 (m1)`. Do not squash Bob commits.

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
| Export | the `_history.md` file name, or `–` if exports are not available |
| Status | `done`, `aborted`, `re-run` or `fallback` |

## Task exports

T00 records whether Bob IDE 2.0.3 has an Export button for task reports. Set `exports_available` in `roster.json` to `true` or `false`.

- If `true`, every row needs an export (checked with `--final`).
- If `false`, add a screenshot showing the missing button (as a `misc` file) and write the finding here:

> Export button: _not recorded yet (T00)._

## Checking

```
python3 tools/check_evidence.py          # during the event: naming and consistency errors fail, gaps are warnings
python3 tools/check_evidence.py --final  # the Sun 09:00 gate: gaps fail too
```
