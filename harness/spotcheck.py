"""What a manual spot-check would catch: p_detect_20 for every group and naive operator.

usage: python -m harness.spotcheck [--seed 2026] [--service MODULE]

p_detect_20 = 1 - (1 - rows/N)^20 is the chance that checking 20 random policies by hand
shows at least one affected row. Reads reports/mismatches.json (running harness.run first if
it is missing) and the naive_baseline of reports/mutation_report.json when present; writes
reports/spotcheck.json.

Standard library only; Python 3.8+.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import os
import sys

from harness import common as C

SAMPLE = 20


def p_detect(rows, n, k=SAMPLE):
    if not n or rows is None:
        return None
    return round(1.0 - (1.0 - float(rows) / n) ** k, 4)


def spotcheck(mismatches, mutation=None):
    n = mismatches["original"]["summary"]["rows"]
    groups = [{"id": g["id"], "class": g["class"], "cell": g["cell"] or g["output_name"],
               "lint": g["lint"], "rows": g["rows"], "p_detect_20": p_detect(g["rows"], n)}
              for g in mismatches["original"]["groups"]]
    naive = {}
    if mutation:
        for op, v in sorted(mutation.get("naive_baseline", {}).items()):
            rows = v if op == "any_rows" else v.get("rows_affected")
            naive[op] = {"rows": rows, "p_detect_20": p_detect(rows, n)}
    return {"_about": "Chance that a 20-policy manual spot-check shows each problem at least once.",
            "run_id": mismatches.get("run_id"), "policies": n, "sample_size": SAMPLE,
            "formula": "p_detect_20 = 1 - (1 - rows/N)^20", "groups": groups,
            "naive_baseline": naive,
            "mutation_service_tree_sha256": (mutation or {}).get("service_tree_sha256")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Spot-check detection probabilities")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    a = ap.parse_args(argv)
    mp = os.path.join(C.REPORTS, "mismatches.json")
    if not os.path.exists(mp):
        from harness import run
        run.main(["--golden", "--seed", str(a.seed), "--service", a.service])
        if not os.path.exists(mp):
            print("spotcheck: no mismatches.json (service pending?)")
            return 0
    mut_p = os.path.join(C.REPORTS, "mutation_report.json")
    doc = spotcheck(C.read_json(mp), C.read_json(mut_p) if os.path.exists(mut_p) else None)
    C.write_json(os.path.join(C.REPORTS, "spotcheck.json"), doc)
    for g in doc["groups"]:
        print("  %s %-10s rows=%-5d p_detect_20=%.3f" % (g["id"], g["cell"], g["rows"], g["p_detect_20"]))
    for op, v in doc["naive_baseline"].items():
        print("  naive %-20s rows=%-5s p_detect_20=%s" % (op, v["rows"], v["p_detect_20"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
