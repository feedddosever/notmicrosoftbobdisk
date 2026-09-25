# Project rules

- Code under `service/sheetshift_ho3/` uses the Python standard library only. The one exception is `api.py`, which may import fastapi and pydantic.
- File I/O happens only in `tables.py` (reads `data/rate_tables.json`) and `api.py` (reads `data/verify_sample_2026.json.gz` and `reports/certificate.json`). No network calls, no environment variables.
- One function per Calc column: `c_<col>_<output_name>(p, c)`, where `p` is the policy dict (14 inputs, blanks are `None`) and `c` is the dict of outputs computed so far.
- Use the canonical output names from `build/units.json` and `docs/CONTRACT.md` exactly.
- `rater.py` holds `ORDER` as a literal tuple of the 43 output names. `tests/test_rater_order.py` asserts that it equals `topo_order` in `build/graph.json`. `rater.py` never reads `build/` at runtime.
- `quote(policy)` returns a dict with all 43 outputs. It never raises for a spreadsheet error; it returns an `XLError` value in that output (and in every output that depends on it).
- Tests may read `build/` for expected values. Service code may not.
