# Third-party licences

SheetShift is MIT-licensed (see LICENSE). This file lists what it depends on. Generated with `python3 tools/license_gate.py --markdown` on 26 Sep 2026, which installs `requirements.txt` into a clean virtual environment and reads each package's licence; CI runs the same gate and fails on anything outside MIT, BSD, Apache-2.0, PSF-2.0 or ISC.

Drafted by Claude Code (AI agent) — scaffold; see ATTRIBUTION.md.

## Runtime (deployed with the API)

| Package | Version | Licence |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| fastapi | 0.141.1 | MIT |
| idna | 3.20 | BSD-3-Clause |
| pydantic | 2.13.5 | MIT |
| pydantic_core | 2.46.5 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |

The rating service itself (`service/sheetshift_ho3/`, except `api.py`) uses only the Python standard library.

## Development and tooling only (not deployed)

Listed in `requirements-dev.txt`: pytest, openpyxl, httpx, pip-licenses, pyyaml, reportlab, pypdf, uvicorn. They build the workbook and manual, run the tests and checks, and serve the API locally. None is shipped with the application.

## External tools (not distributed)

- **LibreOffice Calc** (MPL-2.0) recalculates the original workbook to produce the recorded oracle in `golden/`. It runs in CI and in the `oracle` workflow; SheetShift neither bundles nor modifies it.
- **Microsoft Excel** is used only by the optional cross-check (`tools/excel_crosscheck.py`), on the builder's own licence.

## Pinned third-party code

None. No third-party source code is copied into this repository.
