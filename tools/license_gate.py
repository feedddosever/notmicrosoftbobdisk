"""License gate: every runtime dependency must carry a permissive licence (hackathon rule: public repo, MIT, permissive dependencies).

usage: python3 tools/license_gate.py                 # clean venv from requirements.txt (needs pypi)
       python3 tools/license_gate.py --from-json F   # check a saved `pip-licenses --format=json`
       python3 tools/license_gate.py --markdown      # also print a THIRD_PARTY_LICENSES table

Builds a throwaway virtualenv, installs requirements.txt into it, and runs
`pip-licenses --from=mixed --format=json --python <venv python>` (pip-licenses is a dev
dependency of the calling environment, so it is not itself counted). Fails (exit 1) on any
package whose licence is not in ALLOWED after normalisation. "A OR B" passes if either side
passes; "A AND B" needs both. pip, setuptools and wheel are the venv's own tooling and skipped.

pycel (GPL) and formulas (EUPL) must never appear; openpyxl and reportlab are dev-only.
Standard library only (plus the pip-licenses CLI); Python 3.8+.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "PSF-2.0", "ISC"}
SKIP = {"pip", "setuptools", "wheel", "pkg-resources", "pkg_resources", "distribute"}
BANNED = {"pycel", "formulas", "schedula", "openpyxl", "reportlab"}

# Classifier and free-text spellings -> SPDX ids. "BSD License" alone is ambiguous between
# BSD-2 and BSD-3; both are allowed, so it maps to BSD-3-Clause.
ALIASES = {
    "mit": "MIT", "mit license": "MIT", "the mit license": "MIT",
    "bsd": "BSD-3-Clause", "bsd license": "BSD-3-Clause", "new bsd": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause", "bsd 3-clause": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause", "modified bsd license": "BSD-3-Clause",
    "bsd 2-clause": "BSD-2-Clause", "bsd-2-clause": "BSD-2-Clause", "simplified bsd": "BSD-2-Clause",
    "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0", "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0", "apache license, version 2.0": "Apache-2.0",
    "apache 2": "Apache-2.0", "apache-2": "Apache-2.0",
    "psf": "PSF-2.0", "psf-2.0": "PSF-2.0", "python software foundation license": "PSF-2.0",
    "psf license": "PSF-2.0", "python-2.0": "PSF-2.0",
    "isc": "ISC", "isc license": "ISC", "isc license (iscl)": "ISC",
}


def normalise(text):
    """True if some OR-alternative of the licence text is made only of allowed licences."""
    t = (text or "").strip()
    if not t or t.upper() == "UNKNOWN":
        return False
    parts = [p.strip() for p in re.split(r";|\s+OR\s+|\s+or\s+", t) if p.strip()]
    for part in parts:
        ands = [a.strip(" ()") for a in re.split(r"\s+AND\s+", part)]
        if all(_one(a) for a in ands):
            return True
    return False


def _one(name):
    n = name.strip().strip("()").strip()
    if n in ALLOWED:
        return True
    return ALIASES.get(n.lower()) in ALLOWED


def check(rows):
    """rows: pip-licenses JSON records. Returns (failures, report_rows)."""
    failures, report = [], []
    for r in sorted(rows, key=lambda x: x.get("Name", "").lower()):
        name = r.get("Name", "")
        if name.lower() in SKIP:
            continue
        lic = r.get("License", "")
        ok = normalise(lic) and name.lower() not in BANNED
        report.append((name, r.get("Version", ""), lic, ok))
        if not ok:
            failures.append("%s %s: %r" % (name, r.get("Version", ""), lic))
    return failures, report


def pip_licenses_cli():
    exe = shutil.which("pip-licenses")
    if exe:
        return [exe]
    return [sys.executable, "-m", "piplicenses"]


def collect(requirements):
    """Install requirements into a temp venv and return pip-licenses JSON for it."""
    tmp = tempfile.mkdtemp(prefix="license_gate_")
    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(tmp)
        py = os.path.join(tmp, "Scripts" if os.name == "nt" else "bin", "python")
        subprocess.run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", requirements],
                       check=True)
        out = subprocess.run(pip_licenses_cli() + ["--from=mixed", "--format=json", "--python", py],
                             check=True, stdout=subprocess.PIPE)
        return json.loads(out.stdout.decode("utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail on non-permissive runtime dependencies")
    ap.add_argument("--requirements", default=os.path.join(ROOT, "requirements.txt"))
    ap.add_argument("--from-json", help="check a saved pip-licenses JSON instead of building a venv")
    ap.add_argument("--markdown", action="store_true", help="print a Markdown table of the result")
    a = ap.parse_args(argv)
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as f:
            rows = json.load(f)
    else:
        rows = collect(a.requirements)
    failures, report = check(rows)
    if a.markdown:
        print("| Package | Version | Licence |\n|---|---|---|")
        for name, ver, lic, _ in report:
            print("| %s | %s | %s |" % (name, ver, lic))
    else:
        for name, ver, lic, ok in report:
            print("%-4s %s %s: %s" % ("ok" if ok else "FAIL", name, ver, lic))
    if failures:
        print("license_gate: %d package(s) outside %s" % (len(failures), sorted(ALLOWED)), file=sys.stderr)
        return 1
    print("license_gate: %d runtime packages, all permissive" % len(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
