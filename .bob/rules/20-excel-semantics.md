# Excel semantics (measured)

The oracle is LibreOffice 24.2 with full recalculation forced. Every value below was measured with that oracle. Parity with desktop Excel is not verified. Put these rules in `xlsem.py` helpers and use the helpers everywhere.

## Rounding
- `ROUND(x, d)` first converts x to 15 significant digits, `Decimal(format(x, ".15g"))`, and then rounds halves away from zero (`ROUND_HALF_UP`).
- `ROUNDUP(x, d)` makes the same 15-digit conversion and then rounds away from zero (`ROUND_UP`).
- Never use Python `round()`, which rounds halves to even on the binary value. Never apply `Decimal(x)` to a float without the 15-digit step.

## Lookups
- `VLOOKUP(v, table, k, TRUE)` returns the row with the largest key <= v: `i = bisect_right(keys, v) - 1`. If `i < 0` the result is `#N/A`. `bisect_left` is wrong exactly on band edges.
- Use the range the formula names, not the range you think it should name. If the two disagree, translate the formula and add a FLAG comment.
- Exact `VLOOKUP(.., FALSE)` and `MATCH(.., 0)` compare text case-insensitively. A missing key gives `#N/A`.

## Text
- Text `=` ignores case: `"y"="Y"` is TRUE, and `"Yes"="Y"` is FALSE.
- `&`, `LEFT` and `TEXT` return text exactly as stored. They keep the input's case. `TEXT(7,"00")` is `"07"`.

## Blanks (a blank input arrives as `None`)
- In arithmetic a blank is 0: blank*1 = 0.
- A blank equals `""` and equals 0.
- `MIN` and `MAX` ignore a blank argument, so `MIN(blank, 3)` = 3 and not 0.

## Dates
- `EDATE(d, m)` gives the same day m months later, clamped to the last day of the month.
- `YEARFRAC(a, b, 3)` = (b - a).days / 365.
- `DATEDIF(a, b, "y")` counts complete years. It returns `#NUM!` when a > b.

## Errors
- Errors propagate through arithmetic, ROUND, MIN/MAX, comparisons and `&`. `IFERROR(x, alt)` returns alt for any error.
- `x/0` gives `#DIV/0!`. An error equals another error only when the codes match. Represent errors as `XLError(code)`.

## Probe values (use them in tests/test_xlsem.py)
| Formula | Value |
|---|---|
| `ROUND(628.125,2)` | 628.13 |
| `ROUND(3.505*689,2)` | 2414.95 (Python round gives 2414.94) |
| `ROUND(1.005,2)` | 1.01 |
| `ROUND(2.675,2)` | 2.68 |
| `ROUND(-2.5,0)` | -3 |
| `ROUNDUP(0.1+0.2,1)` | 0.3 |
| `ROUNDUP(682.14,0)` | 683 |
| `VLOOKUP(1000, {0:1.1, 500:1.0, 1000:0.92, 2500:0.82}, 2, TRUE)` | 0.92 |
| same table, key 999 | 1.0 |
| same table, key -1 | #N/A |
| `MATCH("fortified", {"None","Basic","Fortified"}, 0)` | 3 |
| `IF("y"="Y",1,0)` | 1 |
| `blank*1` / `blank=""` / `blank=0` | 0 / TRUE / TRUE |
| `EDATE(DATE(2026,8,31),6)` | 2027-02-28 |
| `ROUND(YEARFRAC(DATE(2028,2,29), EDATE(DATE(2028,2,29),12), 3), 4)` | 1.0 |
| `DATEDIF(DATE(2020,1,1), DATE(2027,3,1), "y")` | 7 |
| `IFERROR(DATEDIF(DATE(2028,1,1), DATE(2027,3,1), "y"), -99)` | -99 |
| `TEXT(7,"00")` / `"T01"&"-"&LEFT("Frame",1)` | "07" / "T01-F" |
| `IFERROR(VLOOKUP("zz", tbl, 2, FALSE)+1, "#NA-caught")` | "#NA-caught" |
| `MIN(0.33, 0.10) + MAX(1, 5)` | 5.1 |
