"""LibreOffice oracle: the workbook computes its own truth, with full recalculation forced.

usage: python -m harness.oracle_lo [--seed 2026] [--patched] [--xlsx PATH]

Converts the expanded workbook (build/cache/harness/expanded_<seed>[_patched].xlsx, built by
harness.expand / harness.patch_workbook) to CSV headlessly and stores the Calc sheet as
golden/oracle_<seed>_Calc.csv.gz (or ..._patched_Calc.csv.gz), gzip with mtime 0.
golden/oracle_meta.json records the LibreOffice version, the profile hash, the seconds and
the hashes of everything that went in.

The profile is harness/lo_profile/registrymodifications.xcu (OOXMLRecalcMode=0 and
ODFRecalcMode=0 = always recalculate), copied into build/cache/harness/lo_profile because
LibreOffice writes into its profile. Without it LibreOffice keeps the cached values stored in
the file (workbook/probe/stale_cache.xlsx demonstrates this), so the profile is mandatory.

Needs LibreOffice (libreoffice-calc): Claude Code sandbox / CI only.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import datetime as dt
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from harness import common as C

PROFILE_SRC = os.path.join(C.HARNESS, "lo_profile", "registrymodifications.xcu")
PROFILE_DIR = os.path.join(C.CACHE, "lo_profile")
# Filter tokens: comma, double quote, UTF-8, from line 1, default cell format, language 0,
# not quoted-as-text, detect special numbers, raw values (not "as shown"), no formulas,
# keep spaces, sheet -1 = one CSV per sheet (LibreOffice >= 7.2).
CSV_FILTER = "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1"


def soffice():
    return shutil.which("soffice") or shutil.which("libreoffice")


def version():
    """'LibreOffice 24.2.7.2 420(Build:2)' -> '24.2.7.2' plus the full string."""
    exe = soffice()
    if not exe:
        return None, None
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=120).stdout.strip()
    parts = out.split()
    return (parts[1] if len(parts) > 1 else out), out


def profile_sha256():
    return C.sha256_file(PROFILE_SRC)


def prepare_profile():
    """Fresh copy of the committed forced-recalc settings into the cache profile."""
    user = os.path.join(PROFILE_DIR, "user")
    os.makedirs(user, exist_ok=True)
    shutil.copyfile(PROFILE_SRC, os.path.join(user, "registrymodifications.xcu"))
    return PROFILE_DIR


def recalc_calc_csv(xlsx, timeout=1800):
    """Force-recalculate `xlsx`; returns (Calc CSV bytes, wall seconds)."""
    exe = soffice()
    if not exe:
        raise SystemExit("LibreOffice (soffice) not found; install libreoffice-calc")
    profile = prepare_profile()
    home = os.path.join(C.CACHE, "lo_home")
    os.makedirs(home, exist_ok=True)
    calc = C.config()["sheets"]["calc"]
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "book.xlsx")
        shutil.copyfile(xlsx, src)
        t0 = time.time()
        subprocess.run([exe, "-env:UserInstallation=file://%s" % os.path.abspath(profile), "--headless",
                        "--convert-to", CSV_FILTER, "--outdir", tmp, src],
                       check=True, env=dict(os.environ, HOME=home), timeout=timeout, capture_output=True)
        wall = time.time() - t0
        found = glob.glob(os.path.join(tmp, "book-%s.csv" % calc))
        if not found:
            raise SystemExit("LibreOffice produced no %s CSV" % calc)
        with open(found[0], "rb") as f:
            return f.read(), wall


def check_csv(data, n):
    """Sanity: header = canonical outputs, n data rows; returns counts of errors per code."""
    rows = C.read_oracle_csv_text(data.decode("utf-8"))
    header = data.decode("utf-8").splitlines()[0].split(",")
    if header != C.outputs():
        raise SystemExit("Calc header does not match sheetshift.json outputs")
    if len(rows) != n:
        raise SystemExit("oracle has %d rows, expected %d" % (len(rows), n))
    errors = {}
    for r in rows:
        for v in r.values():
            if isinstance(v, C.ErrorValue):
                errors[v.code] = errors.get(v.code, 0) + 1
    return dict(sorted(errors.items()))


def update_meta(seed, key, entry):
    path = C.golden_paths(seed)["meta"]
    meta = C.read_json(path) if os.path.exists(path) else {}
    meta["_about"] = ("Provenance of the recorded LibreOffice oracle (the only golden file with "
                      "timestamps). Written by harness/oracle_lo.py.")
    meta[key] = entry
    ordered = {k: meta[k] for k in ("_about", "original", "patched") if k in meta}
    C.write_json(path, ordered)


def main(argv=None):
    ap = argparse.ArgumentParser(description="LibreOffice forced-recalc oracle")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--patched", action="store_true", help="recalculate the decision-patched book")
    ap.add_argument("--xlsx", help="expanded workbook (default: build/cache/harness/...)")
    ap.add_argument("--service", default=C.DEFAULT_SERVICE, help="accepted for uniformity; unused")
    a = ap.parse_args(argv)
    cp, gp = C.cache_paths(a.seed), C.golden_paths(a.seed)
    if a.patched and not a.xlsx and not C.load_decisions():
        print("oracle_lo: no decisions yet; no patched oracle to build")
        return 0
    xlsx = a.xlsx or cp["expanded_patched" if a.patched else "expanded"]
    if not os.path.exists(xlsx):
        raise SystemExit("%s missing: run harness.%s first" % (C.rel(xlsx), "patch_workbook" if a.patched else "expand"))
    meta_in, _ = C.load_inputs(a.seed)
    data, wall = recalc_calc_csv(xlsx)
    errors = check_csv(data, meta_in["n"])
    out = gp["oracle_patched" if a.patched else "oracle"]
    C.write_bytes(out, C.gzip_bytes(data))
    ver, full = version()
    entry = {
        "engine": "LibreOffice", "version": ver, "version_string": full,
        "label": C.ORACLE_LABEL.format(version=ver, seed=a.seed),
        "recalc": "forced full recalculation on load (OOXMLRecalcMode=0, ODFRecalcMode=0)",
        "profile": C.rel(PROFILE_SRC), "profile_sha256": profile_sha256(),
        "seed": a.seed, "rows": meta_in["n"], "columns": len(C.outputs()),
        "inputs_sha256": C.sha256_file(gp["inputs"]),
        "workbook": C.rel(os.path.join(C.ROOT, C.config()["workbook"])),
        "workbook_sha256": C.sha256_file(os.path.join(C.ROOT, C.config()["workbook"])),
        "expanded_sha256": C.sha256_file(xlsx),
        "csv": C.rel(out), "csv_gz_sha256": C.sha256_file(out), "csv_sha256": C.sha256_bytes(data),
        "error_cells": errors, "seconds_recalc": round(wall, 2),
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    if a.patched:
        man = C.read_json(cp["patch_manifest"]) if os.path.exists(cp["patch_manifest"]) else {}
        entry["decisions_sha256"] = man.get("decisions_sha256")
        entry["patched_workbook_sha256"] = man.get("patched_workbook_sha256")
        entry["patches"] = man.get("patches", [])
    update_meta(a.seed, "patched" if a.patched else "original", entry)
    print(json.dumps({"out": C.rel(out), "rows": meta_in["n"], "seconds_recalc": round(wall, 2),
                      "bytes": os.path.getsize(out), "error_cells": errors}))


if __name__ == "__main__":
    sys.exit(main())
