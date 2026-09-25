# Rating manual: how it is generated

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md.

`manual/example_mutual_ho3_rating_manual.pdf` is the synthetic "filed" rating manual for
**Example Mutual Insurance Co. (FICTIONAL)**, Homeowners HO-3, Edition 2026-10. The carrier does not
exist. All names, rates and rules were invented for a software demonstration. Every page footer
carries the banner "FICTIONAL — all names, rates and rules invented for a software demonstration".

## Build

```sh
make map                    # refreshes build/rate_tables.json from the workbook
python3 -m tools.make_manual            # writes the PDF, then checks it
python3 -m tools.make_manual --no-check # writes the PDF only
```

Options: `--tables PATH` (default `build/rate_tables.json`) and `--out PATH` (default
`manual/example_mutual_ho3_rating_manual.pdf`). The tool needs `reportlab` (BSD, dev-only, in
`requirements-dev.txt`). The self-check also uses `pypdf` (BSD) when it is installed.

## Sources

| Part of the PDF | Source |
|---|---|
| Every rate table and factor, plus the scalars (credit cap, minimum premium, assessment rate, hurricane cap) | `build/rate_tables.json`, which `tools/dump_workbook.py` extracts from `workbook/example_mutual_ho3_rater.xlsx` |
| Rule wording (R-100, R-110, R-205, R-310, R-320, R-410, R-420, R-510, R-520, R-900), definitions and layout | `tools/make_manual.py` |

Because the tables come from the same file the workbook is mapped to, the manual and the workbook
share one set of numbers. The workbook contains anomalies that were seeded deliberately for the
demonstration. They are listed in `docs/CONTRACT.md` §1.5. At those anomalies the workbook's
formulas do not follow the manual, and that difference is intended.

To change a rule's wording, edit `tools/make_manual.py`. To change a rate, change the workbook
generator and run `make map`. Do not edit the PDF by hand. The manual is protected: a person must
review any change.

## Determinism

The build is byte-for-byte repeatable for a given reportlab version. It uses:

- reportlab `invariant=1`, which fixes the document ID;
- a fixed creation and modification date, `D:20261001000000+00'00'`;
- fixed metadata;
- only the standard PDF fonts (Helvetica and Courier), which are not embedded.

Upgrading reportlab can change the bytes (the Producer string and object layout) without changing
the text.

## Checks

`python3 -m tools.make_manual` fails if either of these does not hold:

- the PDF has 7 to 10 pages;
- the text layer contains every rule number, "10,000" and "FICTIONAL".

In CI, `pdftotext manual/example_mutual_ho3_rating_manual.pdf - | grep -c R-205` should be ≥ 1.
