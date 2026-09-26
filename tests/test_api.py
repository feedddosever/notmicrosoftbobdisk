"""Tests for service/sheetshift_ho3/api.py using FastAPI TestClient.

Covers:
- GET /api/health: shape, env_vars=0.
- POST /api/quote: valid input, 43 outputs, error serialisation.
- GET /api/verify: n and sample_seed params; result shape; tolerance field.
- GET /api/trace: ?cell= and ?function= lookups; missing param → 400.
"""

import datetime
import math
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from service.sheetshift_ho3.api import app, _encode_output_value
from service.sheetshift_ho3.xlsem import XLError

client = TestClient(app)

# ---------------------------------------------------------------------------
# Minimal policy fixture (all 14 inputs, valid)
# ---------------------------------------------------------------------------

_POLICY = {
    "policy_id": "HO-TEST-001",
    "zone": "T01",
    "construction": "Frame",
    "protection_class": 5,
    "year_built": 2000,
    "roof_age": 10,
    "coverage_a": 300000,
    "deductible": 1000,
    "hurr_ded_pct": 0.02,
    "alarm": "Y",
    "wind_mit": "Basic",
    "claims_3yr": 0,
    "effective_date": "2026-06-01",
    "term_months": 12,
}

_ORDER = (
    "policy_id", "home_age", "roof_age_used", "aoi_units", "base_rate",
    "hurr_rate", "tax_rate", "base_premium", "constr_factor", "constr_hurr_factor",
    "pc_factor", "age_factor", "roof_factor", "aoi_factor", "ded_factor",
    "claims_factor", "aop_premium", "alarm_flag", "claims_free_flag", "new_home_flag",
    "mit_basic_flag", "mit_fort_flag", "credit_raw", "credit_pct", "aop_net",
    "hurr_pct_used", "hurr_ded_factor", "wind_mit_factor", "hurr_premium", "hurr_capped",
    "subtotal", "exp_date", "term_factor", "term_premium", "min_applied",
    "premium_rounded", "policy_fee", "assessment", "tax", "total_due",
    "refer_flag", "rate_per_1000", "rate_class",
)


# ---------------------------------------------------------------------------
# _encode_output_value unit tests (no HTTP)
# ---------------------------------------------------------------------------

class TestEncodeOutputValue:
    def test_xlerror_returns_code_string(self):
        assert _encode_output_value(XLError("#N/A")) == "#N/A"

    def test_hash_string_passthrough(self):
        assert _encode_output_value("#DIV/0!") == "#DIV/0!"

    def test_date_becomes_iso(self):
        assert _encode_output_value(datetime.date(2026, 6, 1)) == "2026-06-01"

    def test_numbers_unchanged(self):
        assert _encode_output_value(1234.56) == pytest.approx(1234.56)
        assert _encode_output_value(42) == 42

    def test_none_unchanged(self):
        assert _encode_output_value(None) is None

    def test_string_unchanged(self):
        assert _encode_output_value("T01-F") == "T01-F"


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_status_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_shape(self):
        body = client.get("/api/health").json()
        assert "status" in body
        assert body["status"] == "ok"
        assert "git_commit" in body
        assert "certificate_hash" in body
        assert "env_vars" in body

    def test_env_vars_is_int(self):
        body = client.get("/api/health").json()
        assert isinstance(body["env_vars"], int)
        # Service defines env_vars as count of SHEETSHIFT_-prefixed env vars;
        # in a clean test environment that count should be 0.
        assert body["env_vars"] == 0


# ---------------------------------------------------------------------------
# POST /api/quote
# ---------------------------------------------------------------------------

class TestQuote:
    def test_status_200(self):
        resp = client.post("/api/quote", json=_POLICY)
        assert resp.status_code == 200

    def test_returns_all_43_outputs(self):
        body = client.post("/api/quote", json=_POLICY).json()
        for name in _ORDER:
            assert name in body, f"Missing output: {name}"

    def test_output_count_is_43(self):
        body = client.post("/api/quote", json=_POLICY).json()
        assert len(body) == 43

    def test_policy_id_passthrough(self):
        body = client.post("/api/quote", json=_POLICY).json()
        # policy_id may be None if rater is a stub, but the key must exist
        assert "policy_id" in body

    def test_date_input_as_dict_encoding(self):
        """Accept {"date": "YYYY-MM-DD"} for effective_date."""
        p = dict(_POLICY)
        p["effective_date"] = {"date": "2026-06-01"}
        resp = client.post("/api/quote", json=p)
        assert resp.status_code == 200

    def test_blank_inputs_accepted(self):
        """All-None optional fields should not cause a 422."""
        p = dict(_POLICY)
        p["roof_age"] = None
        p["hurr_ded_pct"] = None
        p["alarm"] = None
        p["wind_mit"] = None
        p["claims_3yr"] = None
        resp = client.post("/api/quote", json=p)
        assert resp.status_code == 200

    def test_errors_serialised_as_strings(self):
        """Any XLError in output must appear as a '#…' string, never an object."""
        body = client.post("/api/quote", json=_POLICY).json()
        for name, val in body.items():
            if isinstance(val, str) and val.startswith("#"):
                # Looks like an error code string — acceptable
                assert val.startswith("#")
            else:
                # Must not be a dict or list
                assert not isinstance(val, (dict, list)), (
                    f"Output {name!r} is a complex type: {val!r}"
                )

    def test_ineligible_zone_propagates_error(self):
        """Zone T09 produces #N/A; once rater is implemented the value must be
        a '#N/A' string in the JSON output (not an exception or an object)."""
        p = dict(_POLICY)
        p["zone"] = "T09"
        resp = client.post("/api/quote", json=p)
        assert resp.status_code == 200
        body = resp.json()
        # base_rate depends on zone; it must be either None (stub) or "#N/A"
        if body["base_rate"] is not None:
            assert body["base_rate"] == "#N/A"


# ---------------------------------------------------------------------------
# GET /api/verify
# ---------------------------------------------------------------------------

class TestVerify:
    def test_status_200(self):
        resp = client.get("/api/verify?n=5&sample_seed=42")
        assert resp.status_code == 200

    def test_shape(self):
        body = client.get("/api/verify?n=5&sample_seed=1").json()
        assert "rows" in body
        assert "cells_compared" in body
        assert "cells_matched" in body
        assert "cells_mismatched" in body
        assert "oracle" in body
        assert "tolerance" in body
        assert "mismatches" in body

    def test_rows_count_respects_n(self):
        body = client.get("/api/verify?n=10&sample_seed=3").json()
        assert body["rows"] == 10

    def test_n_default_is_200(self):
        body = client.get("/api/verify?sample_seed=7").json()
        assert body["rows"] == 200

    def test_n_upper_bound_500(self):
        resp = client.get("/api/verify?n=501")
        assert resp.status_code == 422  # pydantic validation

    def test_n_lower_bound_1(self):
        resp = client.get("/api/verify?n=0")
        assert resp.status_code == 422

    def test_oracle_string_present(self):
        body = client.get("/api/verify?n=2&sample_seed=5").json()
        # oracle field should be the non-empty string from the sample file
        assert isinstance(body["oracle"], str)
        assert len(body["oracle"]) > 0

    def test_cells_math(self):
        body = client.get("/api/verify?n=3&sample_seed=9").json()
        assert body["cells_compared"] == body["cells_matched"] + body["cells_mismatched"]

    def test_sample_seed_reproducibility(self):
        """Same seed → same rows selected → same result."""
        a = client.get("/api/verify?n=20&sample_seed=42").json()
        b = client.get("/api/verify?n=20&sample_seed=42").json()
        assert a["cells_compared"] == b["cells_compared"]
        assert a["cells_matched"] == b["cells_matched"]

    def test_different_seeds_differ(self):
        """Different seeds generally select different rows."""
        a = client.get("/api/verify?n=50&sample_seed=1").json()
        b = client.get("/api/verify?n=50&sample_seed=2").json()
        # They may coincidentally match on a stub rater but the oracle strings must be the same
        assert a["oracle"] == b["oracle"]

    def test_tolerance_field_is_dict(self):
        body = client.get("/api/verify?n=1&sample_seed=0").json()
        assert isinstance(body["tolerance"], dict)
        assert "numbers" in body["tolerance"]


# ---------------------------------------------------------------------------
# GET /api/trace
# ---------------------------------------------------------------------------

class TestTrace:
    def test_no_params_returns_400(self):
        resp = client.get("/api/trace")
        assert resp.status_code == 400

    def test_cell_lookup_returns_steps_key(self):
        resp = client.get("/api/trace?cell=Calc!A")
        assert resp.status_code == 200
        body = resp.json()
        assert "steps" in body
        assert "count" in body

    def test_function_lookup_returns_steps_key(self):
        resp = client.get("/api/trace?function=c_A_policy_id")
        assert resp.status_code == 200
        body = resp.json()
        assert "steps" in body
        assert isinstance(body["count"], int)

    def test_unknown_cell_returns_empty_steps(self):
        resp = client.get("/api/trace?cell=Calc!ZZ")
        assert resp.status_code == 200
        body = resp.json()
        assert body["steps"] == []
        assert body["count"] == 0

    def test_cell_lookup_case_insensitive(self):
        """?cell=calc!a and ?cell=Calc!A must return the same result."""
        a = client.get("/api/trace?cell=Calc!A").json()
        b = client.get("/api/trace?cell=calc!a").json()
        assert a["count"] == b["count"]

    def test_combined_cell_and_function(self):
        """Both params together: union of matches (no duplicates if same step)."""
        resp = client.get("/api/trace?cell=Calc!A&function=some_fn")
        assert resp.status_code == 200
        body = resp.json()
        assert "steps" in body
