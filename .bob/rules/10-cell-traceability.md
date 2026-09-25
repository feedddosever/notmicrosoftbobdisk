# Cell traceability

- Tag every column function with `@covers("<Sheet>!<Col>", "<output_name>")`, for example `@covers("Calc!O", "ded_factor")`. The decorator comes from `service/sheetshift_ho3/xlsem.py`.
- `covers` appends `{"cell", "name", "fn", "file", "line"}` to `xlsem.STEPS` and returns the function unchanged. `name` is the output name, `fn` the function name (`f.__name__`), `file` the repo-relative path with forward slashes, and `line` is `f.__code__.co_firstlineno` (the `@covers` line).
- Every Calc column A..AQ is tagged exactly once. Never tag a column twice or leave one untagged.
- Items that are deliberately not translated go in `service/sheetshift_ho3/OUT_OF_SCOPE.json`, each with an exact cell address taken from `build/graph.json` (for example `Summary!B2`), a reason, and a decision ID if a person escalated it.
- `harness/trace.py` fails on a missing or doubly tagged column and on an out-of-scope cell that is not in the graph.
