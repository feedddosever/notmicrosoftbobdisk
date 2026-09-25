"""LibreOffice headless recalculation helper for the mapping tools (forced full recalc).

Converts an .xlsx to one CSV per sheet with a private LibreOffice profile that sets
OOXMLRecalcMode=0 ("always recalculate"). Without it LibreOffice keeps the cached values
stored in the file (see workbook/probe/stale_cache.xlsx), so the forced profile is mandatory.

The harness has its own oracle (harness/oracle_lo.py); this helper only serves
tools/dump_workbook.py, which recalculates the 40-row customer book once to fill the
sample rows in build/units/U*.md.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import csv
import datetime as dt
import glob
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "cache")
PROFILE = os.path.join(CACHE, "lo_profile")
XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse"><value>0</value></prop></item>
</oor:items>
"""
# Filter tokens: comma, double quote, UTF-8, from line 1, default cell format, language 0,
# not quoted-as-text, detect special numbers, raw values (not "as shown"), no formulas,
# keep spaces, sheet -1 = one CSV per sheet (LibreOffice >= 7.2).
CSV_FILTER = "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,false,false,false,-1"


def soffice():
    """Path of the soffice binary, or None if LibreOffice is not installed."""
    return shutil.which("soffice") or shutil.which("libreoffice")


def version():
    """LibreOffice version string, e.g. 'LibreOffice 24.2.7.2 420(Build:2)'."""
    exe = soffice()
    if not exe:
        return None
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=120)
    return out.stdout.strip()


def ensure_profile(profile=PROFILE, forced=True):
    """Create a user profile; forced=True writes the always-recalculate settings."""
    os.makedirs(os.path.join(profile, "user"), exist_ok=True)
    path = os.path.join(profile, "user", "registrymodifications.xcu")
    if forced:
        with open(path, "w") as f:
            f.write(XCU)
    return profile


def recalc_to_csv(xlsx, outdir, profile=PROFILE, forced=True, timeout=900):
    """Recalculate `xlsx` headlessly and export every sheet; returns {sheet_name: csv_path}."""
    exe = soffice()
    if not exe:
        raise RuntimeError("LibreOffice (soffice) not found; install libreoffice-calc")
    ensure_profile(profile, forced)
    os.makedirs(outdir, exist_ok=True)
    home = os.path.join(os.path.dirname(profile), "lo_home")
    os.makedirs(home, exist_ok=True)
    env = dict(os.environ, HOME=home)
    subprocess.run([exe, f"-env:UserInstallation=file://{os.path.abspath(profile)}", "--headless",
                    "--convert-to", CSV_FILTER, "--outdir", outdir, os.path.abspath(xlsx)],
                   check=True, env=env, timeout=timeout, capture_output=True)
    stem = os.path.splitext(os.path.basename(xlsx))[0]
    return {os.path.basename(p)[len(stem) + 1:-4]: p
            for p in sorted(glob.glob(os.path.join(outdir, stem + "-*.csv")))}


def parse_cell(s, is_date=False):
    """CSV text -> None | float | datetime.date | str (errors stay as '#...' strings)."""
    if s == "":
        return None
    if is_date:
        try:
            return dt.date.fromisoformat(s)
        except ValueError:
            return s
    try:
        return float(s)
    except ValueError:
        return s


def read_sheet(path, date_columns=()):
    """Returns (header, rows); rows[i] is a dict {header: value} for sheet row i + 2."""
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        rows = [{h: parse_cell(v, h in date_columns) for h, v in zip(header, rec)} for rec in rdr]
    return header, rows


def recalc_sheet(xlsx, sheet, date_columns=(), profile=PROFILE, forced=True):
    """Convenience: recalculate `xlsx` in a temporary directory and read one sheet."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "book.xlsx")
        shutil.copyfile(xlsx, src)
        sheets = recalc_to_csv(src, os.path.join(tmp, "csv"), profile, forced)
        return read_sheet(sheets[sheet], date_columns)


if __name__ == "__main__":
    import sys
    hdr, rows = recalc_sheet(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Calc")
    print(version(), f"rows={len(rows)} cols={len(hdr)}")
