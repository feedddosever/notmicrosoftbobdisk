"""Self-check of the equivalence harness on tiny synthetic fixtures (no service needed).

Covers the tolerance table (compare), root-cell grouping, lint joining, every classification
rule (triage), cell accounting, the decision queue, the spot-check formula, the tree hash,
the boundary generator's table-driven cases and the mutation operators.

Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import copy
import datetime as dt
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from harness import _hash_tree  # noqa: E402
from harness import common as C  # noqa: E402
from harness import compare as K  # noqa: E402
from harness import spotcheck as SP  # noqa: E402
from harness import triage as T  # noqa: E402


class Err(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------- compare: tolerance table
@pytest.mark.parametrize("o,s,kind", [
    (1.0, 1.0000009, None), (1.0, 1.000002, "numeric"), (2.0, 2, None),
    (1.0, True, "type"), (1.0, "1", "type"),
    (dt.date(2027, 2, 28), dt.date(2027, 2, 28), None), (dt.date(2027, 2, 28), dt.datetime(2027, 2, 28), None),
    (dt.date(2027, 2, 28), dt.date(2027, 3, 1), "date"),
    ("REFER", "REFER", None), ("REFER", "refer", "text_case"), ("OK", "NO", "text"),
    (C.ErrorValue("#N/A"), Err("#N/A"), None), (C.ErrorValue("#N/A"), "#N/A", None),
    (C.ErrorValue("#N/A"), Err("#NUM!"), "error_code"), (C.ErrorValue("#N/A"), 0.0, "error_vs_value"),
    (3.0, Err("#N/A"), "value_vs_error"),
    (None, None, None), (None, 0, "blank"), (0.0, None, "blank"), (None, "", "blank"),
    (1.0, K.MISSING, "missing"),
])
def test_diff_kind(o, s, kind):
    assert K.diff_kind(o, s) == kind


def test_compare_row_exception_marks_all_cells():
    names = C.outputs()
    m = K.compare_row({n: 1.0 for n in names}, {K.EXCEPTION: "ValueError: x"}, names)
    assert len(m) == 43 and set(m.values()) == {"exception"}


# ---------------------------------------------------------------- triage fixtures
def _fixture(n=40):
    """Policies, oracle rows and an identical service copy (n rows, sheet rows 2..n+1)."""
    policies, oracle = [], []
    for i in range(n):
        policies.append({"policy_id": "HO-%06d" % (i + 1), "zone": "T01", "construction": "Frame",
                         "protection_class": 5, "year_built": 1990, "roof_age": 8, "coverage_a": 300000,
                         "deductible": 1000, "hurr_ded_pct": 0.02, "alarm": "N", "wind_mit": "None",
                         "claims_3yr": 0, "effective_date": dt.date(2027, 3, 1), "term_months": 12})
        row = {}
        for k, name in enumerate(C.outputs()):
            row[name] = float(k + 1)
        row.update(policy_id=policies[-1]["policy_id"], exp_date=dt.date(2028, 3, 1),
                   refer_flag="OK", rate_class="T01-F05")
        oracle.append(row)
    return policies, oracle, copy.deepcopy(oracle)


def _scenario():
    pol, ora, svc = _fixture()
    for i in (3, 7):                      # A1: key reaches the band the short range misses
        pol[i]["deductible"] = 10000
        ora[i]["ded_factor"], svc[i]["ded_factor"] = 0.74, 0.66
        svc[i]["aop_premium"] += 5.0      # downstream of ded_factor
    for i in (5, 9, 11):                  # same column, not explained by A1: a translation bug
        pol[i]["deductible"] = 500
        svc[i]["ded_factor"] += 0.1
    svc[15]["tax"] = 26.52                # A2: row 17 carries a typed value in the workbook
    for i in (20, 21):                    # one cent at a ROUND(..,2) step
        svc[i]["aop_net"] += 0.01
    for i in (22, 25):                    # no clean predicate: needs a person
        svc[i]["term_factor"] += 0.5
    svc[30] = {K.EXCEPTION: "ZeroDivisionError: float division by zero"}
    return pol, ora, svc


def _triage(decisions=None, mode="original"):
    pol, ora, svc = _scenario()
    mism = K.compare(ora, svc)
    groups, acct = T.triage(pol, ora, svc, mism, mode, decisions or {}, fixed_rows=10)
    return {(g["output_name"], g["lint"]): g for g in groups}, acct, groups


def test_groups_and_classes_without_decisions():
    g, acct, groups = _triage()
    assert g[("ded_factor", "A1")]["class"] == "spreadsheet-anomaly"
    assert g[("ded_factor", "A1")]["sheet_rows"] == [5, 9]
    assert g[("ded_factor", "A1")]["cells"] == 4                 # O and the downstream Q, 2 rows
    assert g[("ded_factor", "A1")]["decision"] == "D-001"
    assert g[("ded_factor", None)]["class"] == "translation-bug"  # not masked by the A1 lint
    assert g[("ded_factor", None)]["signature"]["precision"] == 1.0
    assert g[("tax", "A2")]["class"] == "spreadsheet-anomaly"
    assert g[("aop_net", None)]["class"] == "translation-bug-rounding"
    assert g[("term_factor", None)]["class"] == "needs-human"
    assert g[("quote()", None)]["class"] == "translation-bug"
    assert [x["id"] for x in groups] == ["G%02d" % k for k in range(1, len(groups) + 1)]
    assert acct["decided_cells"]["total"] == 0
    assert acct["unexplained_cells"] == sum(len(v) for v in K.compare(*_scenario()[1:]).values())


def test_adopt_manual_decision_makes_group_decided():
    dec = {"D-001": {"id": "D-001", "option": "adopt-manual", "rule": "R-205", "by": "m1"}}
    g, acct, _ = _triage(dec)
    assert g[("ded_factor", "A1")]["class"] == "decided"
    assert acct["decided_cells"] == {"total": 4, "by_decision": {"D-001": 4}}


@pytest.mark.parametrize("option,mode,cls", [
    ("keep-workbook", "original", "translation-bug"),
    ("escalate", "original", "escalated"),
    ("adopt-manual", "patched", "translation-bug"),
])
def test_decision_options(option, mode, cls):
    g, acct, _ = _triage({"D-001": {"id": "D-001", "option": option, "rule": "R-205", "by": "m1"}}, mode)
    assert g[("ded_factor", "A1")]["class"] == cls
    assert acct["decided_cells"]["total"] == 0


def test_decision_queue_statuses_and_static_only():
    _, _, groups = _triage()
    q = T.decision_queue(groups, "run-x", decisions={})
    items = {i["lint"]: i for i in q["items"]}
    assert [i["id"] for i in q["items"]] == ["D-001", "D-002", "D-003"]
    assert items["A1"]["options"] == ["keep-workbook", "adopt-manual", "escalate"]
    assert items["A2"]["options"] == ["adopt-manual", "escalate"]
    assert items["A1"]["runtime"]["rows"] == 2 and not items["A1"]["static_only"]
    assert items["A3"]["static_only"] and items["A3"]["status"] == "PENDING"


def test_roots_and_downstream_attribution():
    cols = T.column_info()
    mm = {"ded_factor": "numeric", "aop_premium": "numeric", "aop_net": "numeric", "tax_rate": "numeric"}
    roots, attr = T.roots_of_row(mm, cols, C.graph()["topo_order"])
    assert roots == {"ded_factor", "tax_rate"}
    assert attr["aop_net"] == {"ded_factor"}


@pytest.mark.parametrize("template,step", [
    ("=ROUND(E2*D2,2)", ("ROUND", 2)), ("=ROUNDUP(AI2,0)", ("ROUNDUP", 0)),
    ("=ROUND(YEARFRAC(Policies!M2,AF2,3),4)", ("ROUND", 4)),
    ("=ROUND(A2,2)*ROUND(B2,2)", None), ("=MIN(W2,CreditCap)", None), (None, None),
])
def test_rounding_step(template, step):
    assert T.rounding_step(template) == step


def test_rounding_delta_rule():
    assert T.is_rounding_delta({"+0.01": 3, "-0.01": 1}, ("ROUND", 2))
    assert T.is_rounding_delta({"+1": 2}, ("ROUNDUP", 0))
    assert not T.is_rounding_delta({"+0.02": 1}, ("ROUND", 2))
    assert not T.is_rounding_delta({"+0.01": 1}, None)


# ---------------------------------------------------------------- other modules
def test_p_detect_20():
    assert SP.p_detect(0, 10000) == 0.0
    assert SP.p_detect(10000, 10000) == 1.0
    assert abs(SP.p_detect(1874, 10000) - (1 - (1 - 0.1874) ** 20)) < 1e-4


def test_tree_hash_is_stable_and_sensitive(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.cpython-311.pyc").write_bytes(b"junk")
    h1 = _hash_tree.tree_sha256(str(tmp_path))
    assert h1 == _hash_tree.tree_sha256(str(tmp_path))
    (tmp_path / "a.py").write_text("x = 2\n")
    assert _hash_tree.tree_sha256(str(tmp_path)) != h1


def test_harness_tree_matches_expected():
    assert _hash_tree.tree_sha256(C.HARNESS) == _hash_tree.expected(), \
        "harness/ changed: a person reviews it, then runs python3 harness/_hash_tree.py --write"


def test_boundary_cases_cover_table_edges():
    from harness import generate as G
    cases = dict(G.boundary_cases(C.read_json(os.path.join(C.BUILD, "rate_tables.json"))["tables"]))
    for tag in ("deductible=9999", "deductible=10000", "coverage_a=999999", "roof_age=blank",
                "zone=T09 (ineligible)", "effective=2028-02-29 term=12", "effective=2026-08-31 term=6",
                "construction=frame", "built_after_effective", "claims_3yr=None"):
        assert tag in cases
    for l in C.lints():
        if l.get("row"):
            assert (l["type"], l["output_name"]) in G.LINT_RECIPES


def test_lint_joining_respects_missing_keys():
    cols = T.column_info()
    cl, col = T.lint_index()
    assert T.lint_for_root("ded_factor", 5, {"deductible": 25000}, cols, cl, col)["id"] == "A1"
    assert T.lint_for_root("ded_factor", 5, {"deductible": 2500}, cols, cl, col) is None
    assert T.lint_for_root("tax", 15, {}, cols, cl, col)["id"] == "A2"
    assert T.lint_for_root("tax", 16, {}, cols, cl, col) is None


@pytest.mark.skipif(sys.version_info < (3, 9), reason="ast.unparse needs Python 3.9+")
def test_mutation_operators():
    import ast
    from harness import mutate as M
    src = ("from decimal import ROUND_HALF_UP\nMODE = ROUND_HALF_UP\n"
           "def band(v, starts):\n    return v <= starts[0]\n"
           "def f(a):\n    try:\n        return min(a.casefold(), 'x')\n    except KeyError:\n        return 0\n")
    m = M.Mutator()
    m.visit(ast.parse(src))
    ops = sorted({s["op"] for s in m.sites})
    assert ops == ["comparison", "constant", "iferror", "min_max", "round_mode", "text_case"]
    out = ast.unparse(M.Mutator(target=("min_max", 0)).visit(ast.parse(src)))
    assert "max(a.casefold()" in out
    t = M.NaiveRound()
    ast.unparse(t.visit(ast.parse("def xround(x, digits=0):\n    return x\n")))
    assert t.applied and t.applied[0]["function"] == "xround"


def test_expand_row_formula_factory():
    pytest.importorskip("openpyxl")
    from harness import expand as E
    f = E.row_formula_factory("=VLOOKUP(Policies!H2,RateTables!$A$31:$B$35,2,TRUE)", "O")
    assert f(4201) == "=VLOOKUP(Policies!H4201,RateTables!$A$31:$B$35,2,TRUE)"
    assert E.row_formula_factory("=MIN(W2,CreditCap)", "X")(99) == "=MIN(W99,CreditCap)"


# ---------------------------------------------------------------- STEPS in Bob's shape (fn is a name)
def test_service_steps_resolves_function_names(tmp_path, monkeypatch):
    """covers() records fn as f.__name__ and file as a root-relative path; the harness must
    still get a callable (for unit smoke) and the name (for the trace)."""
    pkg = tmp_path / "bobpkg_selfcheck" / "sheetshift_ho3"
    (pkg / "units").mkdir(parents=True)
    for d in (pkg.parent, pkg, pkg / "units"):
        (d / "__init__.py").write_text("")
    (pkg / "xlsem.py").write_text(
        "import os\nSTEPS = []\n"
        "def covers(cell, name):\n"
        "    def deco(f):\n"
        "        STEPS.append({'cell': cell, 'name': name, 'fn': f.__name__,\n"
        "                      'file': os.path.abspath(f.__code__.co_filename), 'line': f.__code__.co_firstlineno})\n"
        "        return f\n"
        "    return deco\n")
    (pkg / "units" / "u1_base.py").write_text(
        "from ..xlsem import covers\n\n@covers('Calc!B', 'home_age')\ndef c_B_home_age(p, c):\n    return 7\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib
    importlib.import_module("bobpkg_selfcheck.sheetshift_ho3.units.u1_base")
    xl = importlib.import_module("bobpkg_selfcheck.sheetshift_ho3.xlsem")
    steps = C.service_steps(xl, "bobpkg_selfcheck.sheetshift_ho3.xlsem")
    assert len(steps) == 1 and steps[0]["name_fn"] == "c_B_home_age"
    assert callable(steps[0]["fn"]) and steps[0]["fn"]({}, {}) == 7
    xl.STEPS.append({"cell": "Calc!C", "name": "roof_age_used", "fn": "no_such_fn", "file": None, "line": 1})
    bad = C.service_steps(xl, "bobpkg_selfcheck.sheetshift_ho3.xlsem")[1]
    with pytest.raises(LookupError):
        bad["fn"]({}, {})
