"""SheetShift equivalence harness: the exam the translated service must pass.

Modules (run with `python -m harness.<name>`; every command accepts --service MODULE):
generate, expand, oracle_lo, patch_workbook, compare, triage, smoke, run, mutate, spotcheck,
certify, trace, export_sample. The Bob-side path (smoke, run, compare, triage, trace, certify,
spotcheck) is standard library only and Python 3.8+ compatible; generate/expand/patch_workbook
need openpyxl and oracle_lo needs LibreOffice (Claude Code sandbox / CI only).

Protected: IBM Bob never edits this package; certify turns RED if the tree hash differs from
harness/EXPECTED_TREE_SHA256.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
