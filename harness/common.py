"""Shared helpers: paths, layout, value encoding, golden I/O, service loading, hashing.

Standard library only; Python 3.8+ compatible (this module is on the Bob-side hook path).

Value model used across the harness (both oracle and service values):
  None            blank cell
  int / float     number
  datetime.date   date
  str             text
  ErrorValue      spreadsheet error, compared by .code ("#N/A", "#NUM!", ...)
JSON encoding (docs/CONTRACT.md section 2): dates {"date": "YYYY-MM-DD"}, errors {"error": code}.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import csv
import datetime as dt
import gzip
import hashlib
import importlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "harness")
GOLDEN = os.path.join(ROOT, "golden")
REPORTS = os.path.join(ROOT, "reports")
BUILD = os.path.join(ROOT, "build")
CACHE = os.path.join(BUILD, "cache", "harness")
DECISIONS = os.path.join(ROOT, "decisions", "decisions.jsonl")
DEFAULT_SERVICE = "service.sheetshift_ho3.rater"
DEFAULT_SEED = 2026
ORACLE_LABEL = "LibreOffice {version}, recorded, golden seed {seed}"


class ErrorValue(object):
    """A spreadsheet error value; equal to another error with the same code."""
    __slots__ = ("code",)

    def __init__(self, code):
        self.code = code

    def __eq__(self, other):
        return isinstance(other, ErrorValue) and other.code == self.code

    def __hash__(self):
        return hash(("ErrorValue", self.code))

    def __repr__(self):
        return self.code


# ---------------------------------------------------------------- layout
_CACHE = {}


def _load_once(key, path):
    if key not in _CACHE:
        with open(path, encoding="utf-8") as f:
            _CACHE[key] = json.load(f)
    return _CACHE[key]


def config():
    """sheetshift.json (sheet names, inputs, outputs, columns)."""
    return _load_once("config", os.path.join(ROOT, "sheetshift.json"))


def graph():
    """build/graph.json."""
    return _load_once("graph", os.path.join(BUILD, "graph.json"))


def lints():
    """The lint list from build/lints.json."""
    return _load_once("lints", os.path.join(BUILD, "lints.json"))["lints"]


def inputs():
    return list(config()["inputs"])


def outputs():
    return list(config()["outputs"])


def output_columns():
    """{output_name: column letter}."""
    c = config()
    return dict(zip(c["outputs"], c["output_columns"]))


def date_outputs():
    return set(config().get("date_outputs", []))


def decision_id_for_lint(lint_id):
    """Stable decision ids: the k-th lint in build/lints.json is D-00k."""
    for k, l in enumerate(lints(), 1):
        if l["id"] == lint_id:
            return "D-%03d" % k
    raise KeyError(lint_id)


def lint_for_decision_id(decision_id):
    k = int(decision_id.split("-")[1])
    return lints()[k - 1]


# ---------------------------------------------------------------- paths
def golden_paths(seed):
    return {
        "inputs": os.path.join(GOLDEN, "inputs_%d.json.gz" % seed),
        "oracle": os.path.join(GOLDEN, "oracle_%d_Calc.csv.gz" % seed),
        "oracle_patched": os.path.join(GOLDEN, "oracle_%d_patched_Calc.csv.gz" % seed),
        "meta": os.path.join(GOLDEN, "oracle_meta.json"),
        "expanded_200": os.path.join(GOLDEN, "expanded_200.xlsx"),
    }


def cache_paths(seed):
    return {
        "expanded": os.path.join(CACHE, "expanded_%d.xlsx" % seed),
        "patched_book": os.path.join(CACHE, "customer_patched.xlsx"),
        "expanded_patched": os.path.join(CACHE, "expanded_%d_patched.xlsx" % seed),
        "patch_manifest": os.path.join(CACHE, "patch_manifest_%d.json" % seed),
    }


def rel(path):
    """Repo-relative path with forward slashes (absolute paths never go into reports)."""
    if not os.path.isabs(path):  # repo-relative already (e.g. a Bob STEPS "file")
        path = os.path.join(ROOT, path)
    try:
        r = os.path.relpath(os.path.abspath(path), ROOT)
    except ValueError:
        return os.path.basename(path)
    if r.startswith(".."):
        return "<outside-repo>/" + os.path.basename(path)
    return r.replace("\\", "/")


# ---------------------------------------------------------------- encoding
def encode(v):
    """Harness value -> JSON-safe value."""
    if isinstance(v, ErrorValue):
        return {"error": v.code}
    if isinstance(v, dt.datetime):
        return {"date": v.date().isoformat()}
    if isinstance(v, dt.date):
        return {"date": v.isoformat()}
    return v


def decode(v):
    if isinstance(v, dict):
        if "date" in v:
            return dt.date.fromisoformat(v["date"])
        if "error" in v:
            return ErrorValue(v["error"])
    return v


def service_error_code(v):
    """Error code if a service value is an error (object with .code or '#...' str), else None."""
    if isinstance(v, str):
        return v if v.startswith("#") else None
    code = getattr(v, "code", None)
    if isinstance(code, str):
        return code
    return None


def show(v):
    """Short human-readable rendering for reports."""
    code = service_error_code(v)
    if code:
        return code
    if v is None:
        return "blank"
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float):
        return repr(round(v, 10))
    return repr(v) if isinstance(v, str) else str(v)


# ---------------------------------------------------------------- deterministic files
def dumps(obj, indent=1):
    return json.dumps(obj, indent=indent, ensure_ascii=False, default=str) + "\n"


def write_text(path, text):
    """Atomic write (temp file + os.replace)."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def write_bytes(path, data):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def write_json(path, obj, indent=1):
    if path.endswith(".gz"):
        write_bytes(path, gzip_bytes(json.dumps(obj, separators=(",", ":"), ensure_ascii=False,
                                                default=str).encode("utf-8")))
    else:
        write_text(path, dumps(obj, indent))


def read_json(path):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def gzip_bytes(data):
    """Deterministic gzip (mtime 0, no file name)."""
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as g:
        g.write(data)
    return buf.getvalue()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_files(top, skip=("EXPECTED_TREE_SHA256",)):
    """Files under `top` that belong to a tree hash (no caches, no bytecode)."""
    from harness import _hash_tree
    return _hash_tree.tree_files(top, skip)


def tree_sha256(top, skip=("EXPECTED_TREE_SHA256",)):
    """Tree hash (single implementation in harness/_hash_tree.py); None if `top` is missing."""
    from harness import _hash_tree
    return _hash_tree.tree_sha256(top, skip)


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------- golden data
def load_inputs(seed):
    """Returns (meta, policies) from golden/inputs_<seed>.json.gz."""
    doc = read_json(golden_paths(seed)["inputs"])
    names = doc["inputs"]
    pols = [dict(zip(names, (decode(v) for v in row))) for row in doc["rows"]]
    meta = {k: v for k, v in doc.items() if k != "rows"}
    return meta, pols


def parse_oracle_cell(s, is_date=False):
    """LibreOffice CSV text -> harness value."""
    if s == "":
        return None
    if s.startswith("#") or s.startswith("Err:"):
        return ErrorValue(s)
    if is_date:
        try:
            return dt.date.fromisoformat(s)
        except ValueError:
            pass
    try:
        return float(s)
    except ValueError:
        return s


def read_oracle_csv_text(text, wanted_rows=None):
    """Parse a Calc CSV; returns list of {output_name: value} (index 0 = sheet row 2).

    wanted_rows: optional set of 0-based data-row indexes to parse (others become None),
    so smoke can read 200 rows of a 10k-row oracle quickly.
    """
    dates = date_outputs()
    rdr = csv.reader(io.StringIO(text))
    header = next(rdr)
    flags = [h in dates for h in header]
    rows = []
    for i, rec in enumerate(rdr):
        if wanted_rows is not None and i not in wanted_rows:
            rows.append(None)
            continue
        rows.append({h: parse_oracle_cell(v, f) for h, v, f in zip(header, rec, flags)})
    return rows


def load_oracle(seed, patched=False, wanted_rows=None):
    """Oracle rows from golden, or None if that oracle has not been produced."""
    p = golden_paths(seed)["oracle_patched" if patched else "oracle"]
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
        return read_oracle_csv_text(f.read(), wanted_rows)


def load_decisions(path=None):
    """decisions/decisions.jsonl records (latest record per id wins)."""
    path = path or DECISIONS
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["id"]] = rec
    return out


# ---------------------------------------------------------------- service loading
class ServiceMissing(Exception):
    """The service module (or a module it imports) is not written yet."""


def import_service(modname):
    """Import the service module; raises ServiceMissing if it does not exist yet."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        return importlib.import_module(modname)
    except ModuleNotFoundError as e:
        raise ServiceMissing(str(e))


def service_package(modname):
    """'service.sheetshift_ho3.rater' -> 'service.sheetshift_ho3'; top-level -> None."""
    return modname.rpartition(".")[0] or None


def service_steps(mod, modname):
    """STEPS list of {cell, name, fn, file, line, name_fn} from the module or its sibling xlsem.

    Bob's covers() records "fn" as the function *name* (a str, so STEPS stays JSON-friendly);
    older shapes carry the callable. Either way the returned "fn" is the callable (resolved
    from the loaded modules by name and file) and "name_fn" is its name.
    """
    steps = getattr(mod, "STEPS", None)
    if steps is None:
        pkg = service_package(modname)
        x = importlib.import_module((pkg + ".xlsem") if pkg else "xlsem")
        steps = getattr(x, "STEPS", [])
    out = []
    for s in steps:
        if isinstance(s, dict):
            s = dict(s)
        else:  # tolerate tuples (cell, name, fn[, file, line])
            s = list(s) + [None] * 5
            s = {"cell": s[0], "name": s[1], "fn": s[2], "file": s[3], "line": s[4]}
        fn = s.get("fn")
        if callable(fn):
            s.setdefault("name_fn", getattr(fn, "__name__", None))
        elif isinstance(fn, str) and fn:
            s["name_fn"] = fn
            s["fn"] = _resolve_fn(fn, s.get("file"), service_package(modname))
        out.append(s)
    return out


def _resolve_fn(name, file, pkg):
    """The loaded function called `name` defined in `file` (repo-relative or absolute), else
    the only such function in the service package; a raising stub if none is found."""
    want = os.path.realpath(file if (file and os.path.isabs(file)) else os.path.join(ROOT, file or ""))
    hits = []
    for mname, m in sorted(list(sys.modules.items()), key=lambda kv: kv[0]):
        if m is None or (pkg and not (mname == pkg or mname.startswith(pkg + "."))):
            continue
        obj = getattr(m, name, None)
        if not callable(obj):
            continue
        code = getattr(obj, "__code__", None)
        if file and code is not None and os.path.realpath(code.co_filename) == want:
            return obj
        hits.append(obj)
    if len(hits) >= 1 and len({id(h) for h in hits}) == 1:
        return hits[0]

    def missing(*_a, **_k):
        raise LookupError("STEPS fn %r (%s) is not an importable function" % (name, file))
    missing.__name__ = name
    return missing


def service_root(modname):
    """Directory holding the service source (package dir, or the module's own directory)."""
    pkg = service_package(modname)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    spec = importlib.util.find_spec(pkg if pkg else modname)
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return list(spec.submodule_search_locations)[0]
    return os.path.dirname(spec.origin)


def xlerror_class(modname):
    """The service's error class (for passing upstream errors into unit functions), or None."""
    pkg = service_package(modname)
    try:
        x = importlib.import_module((pkg + ".xlsem") if pkg else "xlsem")
        return getattr(x, "XLError", None)
    except Exception:
        return None


def call_quote(quote, policy):
    """Run quote(); an exception becomes {'__exception__': 'Type: message'}."""
    try:
        out = quote(dict(policy))
        if not isinstance(out, dict):
            return {"__exception__": "quote() returned %s, not dict" % type(out).__name__}
        return out
    except Exception as e:  # a crash is a finding, not a harness failure
        return {"__exception__": "%s: %s" % (type(e).__name__, str(e)[:200])}
