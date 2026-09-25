"""Seeded policy generator: boundary policies + lint-guided rows + random policies.

usage: python -m harness.generate [--seed 2026] [--n 10000] [--out golden/inputs_2026.json.gz]

Row layout of the output (sheet row = index + 2, as in the expanded workbook):
  * The first `fixed_rows` rows are the boundary policies, with the lint-guided policies
    inserted at the rows named by build/lints.json (rows 17 and 31), so those rows' odd
    formulas (A2 typed-over tax, A3 uncapped credit) are exercised at runtime.
  * The rest are random policies from tools.gen_workbook.random_policy (same distribution
    as the customer workbook).
Band edges and table keys are read from build/rate_tables.json, so every approximate-match
band gets "just below" and "exactly on" cases, and every exact-match table gets each key.

Needs tools.gen_workbook (openpyxl): Claude Code sandbox / CI only. Output is deterministic
for (seed, n): no timestamps, gzip mtime 0.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import json
import os
import random

from harness import common as C

EFF_FOR_AGE = dt.date(2027, 3, 1)       # DATEDIF(DATE(y,1,1), 2027-03-01, "y") = 2027 - y


def _keys(tables, name):
    return [r[0] for r in tables[name]["rows"]]


def boundary_cases(tables):
    """[(tag, {field: value})] in a fixed order; values as they would appear in Policies."""
    cases = []
    add = lambda tag, **kw: cases.append((tag, kw))  # noqa: E731
    ded = _keys(tables, "DedBands")                 # full block, incl. the key A1 cannot reach
    vals = sorted({v for k in ded for v in (k - 1, k) if v >= 0} | {ded[-1] + 1, 50000})
    for v in vals:
        add("deductible=%d" % v, deductible=v)
    aoi = _keys(tables, "AOIBands")
    vals = sorted({v for k in aoi if k > 0 for v in (k - 1, k)} | {100000, 1000001})
    for v in vals:
        add("coverage_a=%d" % v, coverage_a=v)
    ages = {0, 2, 3, 6, 101} | {v for k in _keys(tables, "AgeBands") for v in (k - 1, k) if v >= 0}
    for a in sorted(ages):
        add("home_age=%d" % a, year_built=EFF_FOR_AGE.year - a, effective_date=EFF_FOR_AGE)
    add("built_after_effective", year_built=EFF_FOR_AGE.year + 1, effective_date=EFF_FOR_AGE)
    roof = sorted({v for k in _keys(tables, "RoofBands") for v in (k - 1, k) if v >= 0} | {22})
    add("roof_age=blank", roof_age=None)
    for v in roof:
        add("roof_age=%d" % v, roof_age=v)
    for v in [None] + _keys(tables, "HurrDedTable") + [0.03]:
        add("hurr_ded_pct=%s" % v, hurr_ded_pct=v)
    for v in ["Y", "y", "N", None, "Yes"]:
        add("alarm=%s" % v, alarm=v)
    wind = _keys(tables, "RateTables!$K$31:$L$33")
    for v in wind + ["fortified", "BASIC", None]:
        add("wind_mit=%s" % v, wind_mit=v)
    for v in [None] + _keys(tables, "ClaimsTable") + [4, 7]:
        add("claims_3yr=%s" % v, claims_3yr=v)
    cons = _keys(tables, "RateTables!$A$13:$C$16")
    for v in cons + ["frame", "MASONRY"]:
        add("construction=%s" % v, construction=v)
    for v in _keys(tables, "RateTables!$A$19:$C$28"):
        add("protection_class=%s" % v, protection_class=v)
    zones = _keys(tables, "BaseRates")
    for z in zones:                                  # every territory, with maximum credits (33%)
        add("max_credits zone=%s" % z, zone=z, alarm="Y", wind_mit="Fortified", claims_3yr=0,
            year_built=2023, effective_date=dt.date(2027, 6, 1))
    add("zone=T09 (ineligible)", zone="T09")
    add("zone=t01 (case)", zone="t01")
    for d, t in [((2026, 1, 31), 6), ((2026, 8, 31), 6), ((2027, 8, 31), 6), ((2028, 2, 29), 12),
                 ((2028, 2, 29), 6), ((2027, 3, 1), 12), ((2028, 1, 1), 12), ((2026, 12, 31), 12),
                 ((2027, 2, 28), 6)]:
        add("effective=%04d-%02d-%02d term=%d" % (d + (t,)), effective_date=dt.date(*d), term_months=t)
    # credit totals around the 25% cap (alarm 5, claims-free 10, new home 8, basic 4, fortified 10)
    for alarm, wind_mit, claims, age in [("Y", "None", 0, 4), ("Y", "Basic", 0, 4), ("Y", "Fortified", 0, 10),
                                         ("N", "Fortified", 0, 4), ("Y", "Fortified", 1, 4), ("N", "Basic", 0, 4)]:
        add("credits alarm=%s wind=%s claims=%d age=%d" % (alarm, wind_mit, claims, age),
            alarm=alarm, wind_mit=wind_mit, claims_3yr=claims, year_built=2027 - age,
            effective_date=dt.date(2027, 6, 1))
    # minimum-premium boundary: a coverage sweep in the cheapest territory, no credits
    for term, covs in [(12, (100000, 110000, 120000, 130000)), (6, (200000, 220000, 240000, 260000, 280000, 300000))]:
        for cov in covs:
            add("min_premium term=%d coverage_a=%d" % (term, cov), zone="T01", construction="Frame",
                protection_class=5, coverage_a=cov, deductible=1000, term_months=term, alarm="N",
                wind_mit="None", claims_3yr=1, year_built=1990, roof_age=8, hurr_ded_pct=0.02)
    return cases


def rounding_cases(rng, k=40):
    """Coverage in whole thousands against 3-decimal rates: hunts ROUND half-way ties."""
    return [("rounding_tie coverage_a=%d" % ((201 + 2 * i) * 1000),
             {"coverage_a": (201 + 2 * i) * 1000, "zone": rng.choice(["T01", "T02", "T08", "T06"])})
            for i in range(k)]


# Lint-guided policies, keyed by (lint type, output_name); fields override a random policy.
LINT_RECIPES = {
    ("hardcoded_value_in_formula_column", "tax"): {
        "zone": "T03", "construction": "Masonry", "protection_class": 4, "year_built": 1990,
        "roof_age": 8, "coverage_a": 350000, "deductible": 1000, "hurr_ded_pct": 0.02, "alarm": "N",
        "wind_mit": "None", "claims_3yr": 0, "effective_date": dt.date(2026, 5, 1), "term_months": 12},
    ("inconsistent_formula", "credit_pct"): {   # 5% + 10% + 8% + 10% = 33% > 25% cap
        "zone": "T05", "alarm": "Y", "wind_mit": "Fortified", "claims_3yr": 0, "year_built": 2023,
        "effective_date": dt.date(2027, 6, 1), "deductible": 1000},
}


def generate(n, seed):
    """Returns (policies, info); policies[i] is sheet row i + 2."""
    from tools.gen_workbook import random_policy   # openpyxl-backed module; CC/CI only
    tables = C.read_json(os.path.join(C.BUILD, "rate_tables.json"))["tables"]
    rng = random.Random(seed)
    fixed = []
    for tag, fields in boundary_cases(tables) + rounding_cases(rng):
        p = random_policy(rng, 0)
        p.update(fields)
        fixed.append((tag, p))
    n_boundary = len(fixed)
    guided = []
    for l in C.lints():
        if l.get("row"):
            p = random_policy(rng, 0)
            p.update(LINT_RECIPES.get((l["type"], l["output_name"]), {}))
            guided.append((l["row"], "lint %s %s" % (l["id"], l["cell"]), p))
    for row, tag, p in sorted(guided, key=lambda g: g[0]):
        fixed.insert(row - 2, (tag, p))
    if n < len(fixed):
        raise SystemExit("--n %d is smaller than the %d fixed rows" % (n, len(fixed)))
    policies = [p for _, p in fixed]
    policies += [random_policy(rng, 0) for _ in range(n - len(fixed))]
    for i, p in enumerate(policies):
        p["policy_id"] = "HO-%06d" % (i + 1)
    info = {"boundary_policies": n_boundary, "lint_guided_rows": sorted(g[0] for g in guided),
            "fixed_rows": len(fixed), "fixed_tags": [t for t, _ in fixed]}
    return policies, info


def to_document(policies, info, seed):
    names = C.inputs()
    doc = {"_about": "Synthetic HO-3 policies for Example Mutual Insurance Co. (FICTIONAL); "
                     "row i is sheet row i+2. Generated by harness/generate.py.",
           "seed": seed, "n": len(policies), "inputs": names}
    doc.update(info)
    doc["rows"] = [[C.encode(p.get(k)) for k in names] for p in policies]
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seeded golden policy generator")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--out")
    ap.add_argument("--service", default=C.DEFAULT_SERVICE, help="accepted for uniformity; unused")
    a = ap.parse_args(argv)
    policies, info = generate(a.n, a.seed)
    out = a.out or C.golden_paths(a.seed)["inputs"]
    C.write_json(out, to_document(policies, info, a.seed))
    print(json.dumps({"out": C.rel(out), "n": a.n, "boundary_policies": info["boundary_policies"],
                      "lint_guided_rows": info["lint_guided_rows"], "fixed_rows": info["fixed_rows"],
                      "bytes": os.path.getsize(out)}))


if __name__ == "__main__":
    main()
