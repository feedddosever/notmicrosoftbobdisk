"""SheetShift HO-3 rater.

ORDER: the 43 canonical output names in topological order (matches build/graph.json topo_order).
quote(policy) -> dict of all 43 outputs.

Unit functions live in service/sheetshift_ho3/units/uN_*.py and are imported here.
Each is decorated @covers("Calc!<col>", "<output_name>") so they self-register in xlsem.STEPS.
"""

# ---------------------------------------------------------------------------
# ORDER — literal tuple; never read from build/ at runtime.
# tests/test_rater_order.py asserts it equals build/graph.json topo_order.
# ---------------------------------------------------------------------------

ORDER = (
    "policy_id",
    "home_age",
    "roof_age_used",
    "aoi_units",
    "base_rate",
    "hurr_rate",
    "tax_rate",
    "base_premium",
    "constr_factor",
    "constr_hurr_factor",
    "pc_factor",
    "age_factor",
    "roof_factor",
    "aoi_factor",
    "ded_factor",
    "claims_factor",
    "aop_premium",
    "alarm_flag",
    "claims_free_flag",
    "new_home_flag",
    "mit_basic_flag",
    "mit_fort_flag",
    "credit_raw",
    "credit_pct",
    "aop_net",
    "hurr_pct_used",
    "hurr_ded_factor",
    "wind_mit_factor",
    "hurr_premium",
    "hurr_capped",
    "subtotal",
    "exp_date",
    "term_factor",
    "term_premium",
    "min_applied",
    "premium_rounded",
    "policy_fee",
    "assessment",
    "tax",
    "total_due",
    "refer_flag",
    "rate_per_1000",
    "rate_class",
)

# ---------------------------------------------------------------------------
# Unit imports — each file registers its @covers functions into xlsem.STEPS.
# ---------------------------------------------------------------------------

from service.sheetshift_ho3.units import u1_base       # noqa: F401, E402
from service.sheetshift_ho3.units import u2_aop        # noqa: F401, E402
from service.sheetshift_ho3.units import u3_hurricane  # noqa: F401, E402
from service.sheetshift_ho3.units import u4_final      # noqa: F401, E402

from service.sheetshift_ho3.xlsem import STEPS as _STEPS  # noqa: E402

# Build the ordered list of column functions from STEPS in ORDER sequence.
_STEP_MAP = {s["name"]: s["fn"] for s in _STEPS}
_FN_MAP: dict = {}
for _mod in (u1_base, u2_aop, u3_hurricane, u4_final):
    for _name in dir(_mod):
        _obj = getattr(_mod, _name)
        if callable(_obj) and _name.startswith("c_"):
            _FN_MAP[_obj.__name__] = _obj

_UNIT_FUNCTIONS = [
    _FN_MAP[_STEP_MAP[name]]
    for name in ORDER
    if name in _STEP_MAP and _STEP_MAP[name] in _FN_MAP
]


def quote(policy: dict) -> dict:
    """Compute all 43 outputs for the given policy dict.

    Parameters
    ----------
    policy : dict
        14 named inputs (docs/CONTRACT.md §1.1). Blanks are None.
        effective_date must be datetime.date.

    Returns
    -------
    dict
        All 43 outputs keyed by canonical output name (ORDER).
        XLError values are returned as-is (never raised).
    """
    c: dict = {}
    for fn in _UNIT_FUNCTIONS:
        out_name = next((s["name"] for s in _STEPS if s["fn"] == fn.__name__), None)
        if out_name is not None:
            c[out_name] = fn(policy, c)

    return {name: c.get(name) for name in ORDER}
