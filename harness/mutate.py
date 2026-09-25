"""Mutation self-test: inject plausible translation bugs into a temp copy of the service.

usage: python -m harness.mutate [--seed 2026] [--service MODULE] [--max 60] [--jobs 4]

Generic AST operators (plan section 6.6), applied one site at a time:
  round_mode    ROUND_HALF_UP -> ROUND_HALF_EVEN; ROUND_UP -> ROUND_HALF_UP
  band_lookup   bisect_right -> bisect_left
  comparison    <= <-> <, >= <-> >
  min_max       min <-> max
  text_case     remove .casefold() / .lower() / .upper()
  constant      integer +1 and -1; other numbers x 1.01
  iferror       an `except ...: return default` handler re-raises; iferror(x, d) -> x
  blank         `is None` / `== None` / `in (None, ...)` handling compares with 0 instead
At most --max mutants, chosen by seeded round-robin sampling across operators. A mutant is
killed when its set of mismatching cells (vs the original golden oracle) differs from the
unmutated service's set, or when it crashes on import. Each mutant runs in its own process
on a private copy of the source; the repo is never modified.

Named naive operators (reported under naive_baseline, with the rows each one affects):
  naive_round          the Excel-rounding helper's body becomes Python round()
  bisect_left_band     bisect_right -> bisect_left everywhere, and <= -> < / >= -> > inside
                       band/approximate-lookup helpers
  case_sensitive_text  every .casefold()/.lower()/.upper() call removed
  min_blank_as_zero    blank inputs that feed a MIN() column are passed as 0 (input-level
                       simulation of a translation that treats a blank as 0 inside MIN)
Survivors are listed, never hidden; a person labels each one "equivalent mutant" or "gap" in
reports/mutation_labels.json (keyed by fingerprint).

Needs Python 3.9+ (ast.unparse); standard library only.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import argparse
import ast
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

from harness import common as C
from harness import compare as K
from harness import triage as T

OPS = ["band_lookup", "blank", "comparison", "constant", "iferror", "min_max", "round_mode", "text_case"]
SWAP_CMP = {ast.LtE: ast.Lt, ast.Lt: ast.LtE, ast.GtE: ast.Gt, ast.Gt: ast.GtE}
CMP_TEXT = {ast.LtE: "<=", ast.Lt: "<", ast.GtE: ">=", ast.Gt: ">"}
RENAME = {"ROUND_HALF_UP": ("decimal", "ROUND_HALF_EVEN", "round_mode"),
          "ROUND_UP": ("decimal", "ROUND_HALF_UP", "round_mode"),
          "bisect_right": ("bisect", "bisect_left", "band_lookup")}
TEXT_CALLS = ("casefold", "lower", "upper")
LABELS = os.path.join(C.REPORTS, "mutation_labels.json")
SKIP_FILES = ("api.py",)


def _mod_attr(module, attr):
    """`__import__('module').attr` - valid whatever the file imported."""
    call = ast.Call(func=ast.Name(id="__import__", ctx=ast.Load()), args=[ast.Constant(module)], keywords=[])
    return ast.Attribute(value=call, attr=attr, ctx=ast.Load())


def _covers_cell(fn):
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and getattr(d.func, "id", getattr(d.func, "attr", "")) == "covers":
            if d.args and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str):
                return d.args[0].value
    return None


class Mutator(ast.NodeTransformer):
    """Walks a module; in count mode records sites, in apply mode mutates site (op, k)."""

    def __init__(self, target=None, ops=None, scope=None):
        self.target, self.ops, self.scope = target, ops, scope
        self.count = {}
        self.sites = []
        self.stack = []          # [(function name, covers cell)]
        self.applied = []

    # -- bookkeeping
    def _site(self, op, node, change):
        if self.ops is not None and op not in self.ops:
            return False
        if self.scope and not any(re.search(self.scope, f or "") for f, _ in self.stack):
            return False
        k = self.count.get(op, 0)
        self.count[op] = k + 1
        fn = self.stack[-1][0] if self.stack else "<module>"
        cell = next((c for _, c in reversed(self.stack) if c), None)
        self.sites.append({"op": op, "k": k, "line": getattr(node, "lineno", None),
                           "function": fn, "covers": cell, "change": change})
        hit = self.target == "all" or self.target == (op, k)
        if hit:
            self.applied.append(self.sites[-1])
        return hit

    def visit_FunctionDef(self, node):
        if node.name.startswith("test_"):
            return node
        self.stack.append((node.name, _covers_cell(node)))
        self.generic_visit(node)
        self.stack.pop()
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    # -- operators
    def visit_Name(self, node):
        r = RENAME.get(node.id)
        if r and isinstance(node.ctx, ast.Load) and self._site(r[2], node, "%s -> %s" % (node.id, r[1])):
            return ast.copy_location(_mod_attr(r[0], r[1]), node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        r = RENAME.get(node.attr)
        if r and isinstance(node.ctx, ast.Load) and self._site(r[2], node, "%s -> %s" % (node.attr, r[1])):
            return ast.copy_location(_mod_attr(r[0], r[1]), node)
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        for j, op in enumerate(node.ops):
            t = type(op)
            if t in SWAP_CMP and self._site("comparison", node, "%s -> %s" % (CMP_TEXT[t], CMP_TEXT[SWAP_CMP[t]])):
                node.ops[j] = SWAP_CMP[t]()
        for j, comp in enumerate(node.comparators):
            if isinstance(comp, ast.Constant) and comp.value is None and type(node.ops[j]) in (ast.Is, ast.IsNot, ast.Eq, ast.NotEq):
                if self._site("blank", node, "None -> 0 in comparison"):
                    node.comparators[j] = ast.copy_location(ast.Constant(0), comp)
                    node.ops[j] = ast.Eq() if type(node.ops[j]) in (ast.Is, ast.Eq) else ast.NotEq()
            elif isinstance(comp, (ast.Tuple, ast.List, ast.Set)) and type(node.ops[j]) in (ast.In, ast.NotIn):
                if any(isinstance(e, ast.Constant) and e.value is None for e in comp.elts):
                    if self._site("blank", node, "None -> 0 in membership test"):
                        comp.elts = [ast.Constant(0) if isinstance(e, ast.Constant) and e.value is None else e
                                     for e in comp.elts]
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Name) and f.id in ("min", "max"):
            other = "max" if f.id == "min" else "min"
            if self._site("min_max", node, "%s -> %s" % (f.id, other)):
                node.func = ast.copy_location(ast.Name(id=other, ctx=ast.Load()), f)
            return node
        if isinstance(f, ast.Attribute) and f.attr in TEXT_CALLS and not node.args and not node.keywords:
            if self._site("text_case", node, ".%s() removed" % f.attr):
                return f.value
            return node
        name = getattr(f, "id", getattr(f, "attr", ""))
        if name.lower().endswith("iferror") and len(node.args) >= 2:
            if self._site("iferror", node, "%s(x, default) -> x" % name):
                a0 = node.args[0]
                if isinstance(a0, ast.Lambda) and not a0.args.args:
                    return ast.copy_location(ast.Call(func=a0, args=[], keywords=[]), node)
                return a0
        return node

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.type is not None:
            if self._site("iferror", node, "except handler returning a default -> re-raise"):
                node.body = [ast.copy_location(ast.Raise(), node.body[0])]
        return node

    def visit_Constant(self, node):
        v = node.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return node
        if isinstance(v, int):
            if self._site("constant", node, "%d -> %d" % (v, v + 1)):
                return ast.copy_location(ast.Constant(v + 1), node)
            if self._site("constant", node, "%d -> %d" % (v, v - 1)):
                return ast.copy_location(ast.Constant(v - 1), node)
        elif self._site("constant", node, "%r -> %r" % (v, v * 1.01)):
            return ast.copy_location(ast.Constant(v * 1.01), node)
        return node


class NaiveRound(ast.NodeTransformer):
    """Replace the body of the Excel-rounding helper(s) with Python round()."""
    NAME = re.compile(r"^(x|xl_?|excel_?)?round(_half_up)?$", re.I)

    def __init__(self):
        self.applied = []

    def visit_FunctionDef(self, node):
        args = [a.arg for a in node.args.args]
        if self.NAME.match(node.name) and args:
            digits = ast.Name(id=args[1], ctx=ast.Load()) if len(args) > 1 else ast.Constant(0)
            node.body = [ast.Return(value=ast.Call(func=ast.Name(id="round", ctx=ast.Load()),
                                                   args=[ast.Name(id=args[0], ctx=ast.Load()), digits],
                                                   keywords=[]))]
            self.applied.append({"line": node.lineno, "function": node.name, "change": "body -> round()"})
        return node


# ---------------------------------------------------------------- source handling
def source_layout(service):
    """(copy_src_dir, name inside the temp dir or None, mutation root dir)."""
    root = C.service_root(service)
    pkg = C.service_package(service)
    if pkg:
        top = pkg.split(".")[0]
        spec = importlib.util.find_spec(top)
        top_dir = list(spec.submodule_search_locations)[0]
        return top_dir, top, root
    return root, None, root


def target_files(root):
    out = []
    for p in C.tree_files(root):
        b = os.path.basename(p)
        if p.endswith(".py") and b not in SKIP_FILES and not b.startswith("test_") and os.sep + "tests" + os.sep not in p:
            out.append(p)
    return out


def make_copy(copy_src, name, dest):
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    if name:
        shutil.copytree(copy_src, os.path.join(dest, name), ignore=ignore)
    else:
        shutil.copytree(copy_src, dest, ignore=ignore, dirs_exist_ok=True)
    return dest


def mutated_source(path, transformer):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def enumerate_sites(files, root):
    sites = []
    for f in files:
        m = Mutator()
        m.visit(ast.parse(open(f, encoding="utf-8").read(), filename=f))
        seen = {}
        for s in m.sites:
            s["file"] = os.path.relpath(f, root).replace("\\", "/")
            s["path"] = f
            key = (s["function"], s["op"], s["change"])
            s["occurrence"] = seen.get(key, 0)      # line-independent, for stable fingerprints
            seen[key] = s["occurrence"] + 1
            sites.append(s)
    return sites


def sample_sites(sites, max_n, seed):
    rng = random.Random(seed)
    by_op = {}
    for s in sites:
        by_op.setdefault(s["op"], []).append(s)
    for op in by_op:
        rng.shuffle(by_op[op])
    chosen = []
    while len(chosen) < max_n and any(by_op.values()):
        for op in OPS:
            if by_op.get(op) and len(chosen) < max_n:
                chosen.append(by_op[op].pop())
    return chosen


def fingerprint(s):
    key = "|".join(str(s.get(k)) for k in ("file", "function", "op", "change", "occurrence"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


# ---------------------------------------------------------------- worker
def worker(spec_path):
    """Run one (mutated) service copy over the golden inputs; print a JSON result."""
    spec = C.read_json(spec_path)
    t0 = time.time()
    res = {"crashed": False, "error": None}
    try:
        sys.path.insert(0, spec["path"])
        mod = __import__("importlib").import_module(spec["service"])
        meta, policies = C.load_inputs(spec["seed"])
        for name in spec.get("blank_to_zero", []):
            for p in policies:
                if p.get(name) is None:
                    p[name] = 0
        oracle = C.load_oracle(spec["seed"])
        rows = K.run_service(mod.quote, policies)
    except BaseException as e:  # noqa: B902  import-time crash = killed
        res.update(crashed=True, error="%s: %s" % (type(e).__name__, str(e)[:200]),
                   rows_flagged=None, seconds=round(time.time() - t0, 2))
        print(json.dumps(res))
        return 0
    base = {(i, n) for i, n in C.read_json(spec["baseline"])}
    mism = K.compare(oracle, rows)
    cells = {(i, n) for i, mm in mism.items() for n in mm}
    changed = cells ^ base
    flagged = sorted({i for i, _ in changed})
    cols = T.column_info()
    order = C.graph()["topo_order"]
    roots = {}
    for i in flagged:
        rs, _ = T.roots_of_row(mism.get(i, {}), cols, order)
        for r in rs:
            if (i, r) in changed:
                roots[r] = roots.get(r, 0) + 1
    fixed = meta.get("fixed_rows", 0)
    res.update(changed_cells=len(changed), rows_flagged=len(flagged),
               boundary_rows_flagged=sum(1 for i in flagged if i < fixed),
               random_rows_flagged=sum(1 for i in flagged if i >= fixed),
               exception_rows=sum(1 for r in rows if K.EXCEPTION in r),
               roots=dict(sorted(roots.items())), flagged=flagged, seconds=round(time.time() - t0, 2))
    print(json.dumps(res))
    return 0


def run_worker(spec, tmp, timeout=300):
    sp = os.path.join(tmp, "spec_%s.json" % spec["id"])
    C.write_json(sp, spec)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        out = subprocess.run([sys.executable, "-m", "harness.mutate", "--worker", sp], cwd=C.ROOT,
                             capture_output=True, text=True, timeout=timeout, env=env)
        line = [l for l in out.stdout.splitlines() if l.startswith("{")]
        if not line:
            return {"crashed": True, "error": (out.stderr or "no output")[-300:], "rows_flagged": None}
        return json.loads(line[-1])
    except subprocess.TimeoutExpired:
        return {"crashed": True, "error": "timeout", "rows_flagged": None}


# ---------------------------------------------------------------- driver
def prepare_variant(copy_src, name, root, tmp, vid, edits):
    """Copy the source to tmp/vid and write `edits` {abs original path: new source}."""
    dest = make_copy(copy_src, name, os.path.join(tmp, vid))
    base = os.path.join(dest, name) if name else dest
    for path, src in edits.items():
        rel = os.path.relpath(path, copy_src)
        with open(os.path.join(base, rel), "w", encoding="utf-8") as f:
            f.write(src)
    return dest


def naive_variants(files):
    """{op: (edits, applied sites, extra worker spec)} for the named naive operators."""
    makers = {"naive_round": NaiveRound, "bisect_left_band": _BandLeft,
              "case_sensitive_text": lambda: Mutator(target="all", ops={"text_case"})}
    out = {}
    for op, make in makers.items():
        edits, applied = {}, []
        for f in files:
            t = make()
            src = mutated_source(f, t)
            if t.applied:
                edits[f] = src
                applied.extend(dict(x, file=os.path.basename(f)) for x in t.applied)
        out[op] = (edits, applied, {})
    mins = sorted({i for c in C.graph()["columns"] if "MIN" in c.get("functions", []) for i in c.get("inputs", [])})
    out["min_blank_as_zero"] = ({}, [{"change": "blank %s -> 0" % i} for i in mins], {"blank_to_zero": mins})
    return out


class _BandLeft(ast.NodeTransformer):
    """bisect_right -> bisect_left anywhere; <= -> <, >= -> > inside band-like functions."""

    def __init__(self):
        self.applied, self.depth = [], 0

    def visit_FunctionDef(self, node):
        inside = bool(re.search(r"(?i)band|approx", node.name))
        self.depth += inside
        self.generic_visit(node)
        self.depth -= inside
        return node

    def visit_Name(self, node):
        if node.id == "bisect_right" and isinstance(node.ctx, ast.Load):
            self.applied.append({"line": node.lineno, "change": "bisect_right -> bisect_left"})
            return ast.copy_location(_mod_attr("bisect", "bisect_left"), node)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if node.attr == "bisect_right" and isinstance(node.ctx, ast.Load):
            self.applied.append({"line": node.lineno, "change": "bisect_right -> bisect_left"})
            return ast.copy_location(_mod_attr("bisect", "bisect_left"), node)
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if self.depth:
            for j, op in enumerate(node.ops):
                if type(op) in (ast.LtE, ast.GtE):
                    node.ops[j] = ast.Lt() if isinstance(op, ast.LtE) else ast.Gt()
                    self.applied.append({"line": node.lineno, "change": "%s -> %s" % (
                        CMP_TEXT[type(op)], CMP_TEXT[SWAP_CMP[type(op)]])})
        return node


def mutate(service, seed, max_n, jobs, sample_seed):
    if sys.version_info < (3, 9):
        raise SystemExit("harness.mutate needs Python 3.9+ (ast.unparse)")
    t_all = time.time()
    meta, policies = C.load_inputs(seed)
    oracle = C.load_oracle(seed)
    mod = C.import_service(service)
    base_rows = K.run_service(mod.quote, policies)
    base_mism = K.compare(oracle, base_rows)
    copy_src, name, root = source_layout(service)
    files = target_files(root)
    sites = enumerate_sites(files, root)
    chosen = sample_sites(sites, max_n, sample_seed)
    labels = C.read_json(LABELS) if os.path.exists(LABELS) else {}
    tmp = tempfile.mkdtemp(prefix="sheetshift_mut_")
    try:
        bpath = os.path.join(tmp, "baseline.json")
        C.write_json(bpath, sorted([i, n] for i, mm in base_mism.items() for n in mm))
        tasks = []
        for k, s in enumerate(chosen, 1):
            s["id"] = "M%02d" % k
            src = mutated_source(s["path"], Mutator(target=(s["op"], s["k"])))
            d = prepare_variant(copy_src, name, root, tmp, s["id"], {s["path"]: src})
            tasks.append((s, {"id": s["id"], "path": d, "service": service, "seed": seed, "baseline": bpath}))
        naive = naive_variants(files)
        for op, (edits, applied, extra) in naive.items():
            if applied:
                d = prepare_variant(copy_src, name, root, tmp, op, edits)
                spec = {"id": op, "path": d, "service": service, "seed": seed, "baseline": bpath}
                spec.update(extra)
                tasks.append(({"id": op, "naive": True, "applied": applied}, spec))
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(lambda t: run_worker(t[1], tmp), tasks))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    mutants, naive_out, survivors = [], {}, []
    n_all = len(policies)
    union = set()
    for (s, _), r in zip(tasks, results):
        if s.get("naive"):
            flagged = r.pop("flagged", []) or []
            union |= set(flagged)
            naive_out[s["id"]] = {"method": NAIVE_METHOD[s["id"]], "sites": s["applied"],
                                  "rows_affected": r.get("rows_flagged"), "cells_affected": r.get("changed_cells"),
                                  "boundary_rows": r.get("boundary_rows_flagged"),
                                  "random_rows": r.get("random_rows_flagged"), "roots": r.get("roots"),
                                  "crashed": r.get("crashed"), "error": r.get("error")}
            continue
        r.pop("flagged", None)
        killed = bool(r.get("crashed")) or bool(r.get("rows_flagged"))
        fp = fingerprint(s)
        entry = {"id": s["id"], "op": s["op"], "file": s["file"], "line": s["line"],
                 "function": s["function"], "covers": s["covers"], "change": s["change"],
                 "fingerprint": fp, "killed": killed, "crashed": bool(r.get("crashed")),
                 "error": r.get("error"), "rows_flagged": r.get("rows_flagged"),
                 "boundary_rows_flagged": r.get("boundary_rows_flagged"),
                 "random_rows_flagged": r.get("random_rows_flagged"), "roots": r.get("roots"),
                 "root_matches_covered_cell": _root_match(s["covers"], r.get("roots")),
                 "seconds": r.get("seconds")}
        mutants.append(entry)
        if not killed:
            lab = labels.get(fp, {})
            survivors.append({"id": s["id"], "op": s["op"], "file": s["file"], "line": s["line"],
                              "function": s["function"], "change": s["change"], "fingerprint": fp,
                              "label": lab.get("label", "unlabeled"), "labelled_by": lab.get("by")})
    for op in NAIVE_METHOD:
        naive_out.setdefault(op, {"method": NAIVE_METHOD[op], "sites": [], "rows_affected": None,
                                  "status": "not_applicable: no matching code site"})
    killed = [m for m in mutants if m["killed"]]
    by_b = [m["id"] for m in killed if (m["boundary_rows_flagged"] or 0) > 0]
    by_r = [m["id"] for m in killed if (m["random_rows_flagged"] or 0) > 0]
    op_counts = {}
    for s in sites:
        op_counts[s["op"]] = op_counts.get(s["op"], 0) + 1
    report = {
        "_about": "Mutation self-test of the service (harness/mutate.py). Survivors are listed, "
                  "never hidden; people label them in reports/mutation_labels.json.",
        "service": service, "service_tree_sha256": C.tree_sha256(root), "seed": seed,
        "sample_seed": sample_seed, "policies": n_all, "fixed_rows": meta.get("fixed_rows"),
        "files": [os.path.relpath(f, root).replace("\\", "/") for f in files],
        "sites_found": dict(sorted(op_counts.items())), "max_mutants": max_n,
        "total": len(mutants), "killed": len(killed),
        "killed_by_crash": sum(1 for m in killed if m["crashed"]),
        "catch_rate": round(len(killed) / float(len(mutants)), 4) if mutants else None,
        "caught_using_boundary_rows": len(by_b), "caught_using_random_rows": len(by_r),
        "caught_only_by_boundary_rows": sorted(set(by_b) - set(by_r) - {m["id"] for m in killed if m["crashed"]}),
        "caught_only_by_random_rows": sorted(set(by_r) - set(by_b)),
        "survivors": survivors,
        "naive_baseline": dict(sorted(naive_out.items()), any_rows=len(union)),
        "mutants": mutants, "seconds": round(time.time() - t_all, 2),
    }
    return report


NAIVE_METHOD = {
    "naive_round": "AST: Excel-rounding helper body -> Python round()",
    "bisect_left_band": "AST: bisect_right -> bisect_left; <=/>= -> </> inside band helpers",
    "case_sensitive_text": "AST: all .casefold()/.lower()/.upper() calls removed",
    "min_blank_as_zero": "input-level: blank inputs of MIN() columns passed as 0",
}


def _root_match(cell, roots):
    if not cell or not roots:
        return None
    name = {c["cell"]: c["output_name"] for c in C.graph()["columns"]}.get(cell)
    return name in roots if name else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mutation self-test")
    ap.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--service", default=C.DEFAULT_SERVICE)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--sample-seed", type=int, default=C.DEFAULT_SEED)
    ap.add_argument("--out", default=os.path.join(C.REPORTS, "mutation_report.json"))
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.worker:
        return worker(a.worker)
    try:
        rep = mutate(a.service, a.seed, a.max, a.jobs, a.sample_seed)
    except C.ServiceMissing as e:
        print("mutate: pending (%s)" % e)
        return 0
    C.write_json(a.out, rep)
    print("mutation: %d/%d killed (%d by crash); boundary %d, random %d; only-boundary %s; survivors %s; %.1fs" % (
        rep["killed"], rep["total"], rep["killed_by_crash"], rep["caught_using_boundary_rows"],
        rep["caught_using_random_rows"], rep["caught_only_by_boundary_rows"],
        [s["id"] for s in rep["survivors"]], rep["seconds"]))
    for op, v in rep["naive_baseline"].items():
        if op != "any_rows":
            print("  naive %-20s rows %s" % (op, v.get("rows_affected")))
    print("  naive any: %d rows" % rep["naive_baseline"]["any_rows"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
