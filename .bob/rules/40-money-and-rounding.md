# Money and rounding

- Keep every ROUND and ROUNDUP step of the workbook, in column order. Never merge two steps and never skip one, even where it looks redundant.
- Round through the `xlsem` helpers only. Do money arithmetic in the same order as the formula.
- Tests never compare floats with `==`. Use `pytest.approx(expected, abs=1e-6)` or `math.isclose(a, b, abs_tol=1e-6)`. Compare dates and text exactly, and errors by `.code`.
- Never compare money with `==` in service code either. Compare with `<`, `>`, `min` or `max` exactly as the formula does.
