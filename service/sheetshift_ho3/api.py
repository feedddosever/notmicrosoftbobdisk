"""FastAPI application for SheetShift HO-3.

Endpoints
---------
GET  /api/health   — commit SHA and certificate hash; env_vars count = 0.
POST /api/quote    — 14 policy inputs → 43 outputs; errors as strings like "#N/A".
GET  /api/verify   — sample n≤500 rows from data/verify_sample_2026.json.gz and compare.
GET  /api/trace    — traceability lookup by ?cell= or ?function=.

No environment variables are read. No harness imports.
I/O: reads data/verify_sample_2026.json.gz and reports/certificate.json.
"""

import datetime
import gzip
import json
import math
import pathlib
import random
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from service.sheetshift_ho3 import rater
from service.sheetshift_ho3.xlsem import STEPS, XLError

# ---------------------------------------------------------------------------
# Paths (resolved at module load, no env vars)
# ---------------------------------------------------------------------------

_HERE = pathlib.Path(__file__).resolve().parent
_VERIFY_SAMPLE = _HERE / "data" / "verify_sample_2026.json.gz"
_CERT_PATH = pathlib.Path(__file__).resolve().parents[2] / "reports" / "certificate.json"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="SheetShift HO-3 Rater", version="0.1.0")


# ---------------------------------------------------------------------------
# JSON helpers — encode service output values for API responses
# ---------------------------------------------------------------------------

def _encode_output_value(v: Any) -> Any:
    """Convert a quote() output value to a JSON-serialisable form.

    - XLError / str starting with '#': returned as a string like "#N/A".
    - datetime.date: ISO string "YYYY-MM-DD".
    - Everything else: unchanged (int, float, str, None).
    """
    if isinstance(v, XLError):
        return v.code
    if isinstance(v, str) and v.startswith("#"):
        return v
    if isinstance(v, datetime.date):
        return v.isoformat()
    return v


# ---------------------------------------------------------------------------
# Pydantic input model — 14 policy inputs (docs/CONTRACT.md §1.1)
# ---------------------------------------------------------------------------

class PolicyIn(BaseModel):
    policy_id: Optional[str] = None
    zone: Optional[str] = None
    construction: Optional[str] = None
    protection_class: Optional[int] = None
    year_built: Optional[int] = None
    roof_age: Optional[int] = None
    coverage_a: Optional[int] = None
    deductible: Optional[int] = None
    hurr_ded_pct: Optional[float] = None
    alarm: Optional[str] = None
    wind_mit: Optional[str] = None
    claims_3yr: Optional[int] = None
    effective_date: Optional[str] = None  # accepted as "YYYY-MM-DD"
    term_months: Optional[int] = None

    @field_validator("effective_date", mode="before")
    @classmethod
    def _parse_date(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime.date):
            return v.isoformat()
        # Accept {"date": "YYYY-MM-DD"} encoding
        if isinstance(v, dict) and "date" in v:
            return v["date"]
        return str(v)

    def to_policy_dict(self) -> dict:
        """Return the dict that rater.quote() expects.

        effective_date is converted from "YYYY-MM-DD" string to datetime.date;
        all other blanks remain None.
        """
        d = self.model_dump()
        if d["effective_date"] is not None:
            d["effective_date"] = datetime.date.fromisoformat(d["effective_date"])
        return d


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    """Return commit SHA, certificate hash, and env_vars count (always 0)."""
    cert_data: dict = {}
    if _CERT_PATH.exists():
        try:
            with _CERT_PATH.open(encoding="utf-8") as fh:
                cert_data = json.load(fh)
        except Exception:
            pass

    git_commit = cert_data.get("git_commit") or cert_data.get("hashes", {}).get("git_commit")
    cert_hash = cert_data.get("hashes", {}).get("certificate") or cert_data.get("hashes", {}).get("report")

    return {
        "status": "ok",
        "git_commit": git_commit,
        "certificate_hash": cert_hash,
        "env_vars": 0,
    }


# ---------------------------------------------------------------------------
# POST /api/quote
# ---------------------------------------------------------------------------

@app.post("/api/quote")
def quote_policy(policy_in: PolicyIn):
    """Accept 14 policy inputs; return all 43 outputs.

    Errors are serialised as strings like "#N/A".
    """
    policy = policy_in.to_policy_dict()
    result = rater.quote(policy)
    return {k: _encode_output_value(v) for k, v in result.items()}


# ---------------------------------------------------------------------------
# GET /api/verify
# ---------------------------------------------------------------------------

_TOLERANCE = 1e-6


def _values_match(expected: Any, actual: Any) -> bool:
    """Compare expected (decoded from the sample file) with actual (from quote()).

    - dict {"error": code}: compare by code to XLError or "#…" string.
    - dict {"date": "YYYY-MM-DD"}: compare to datetime.date or ISO string.
    - Number: abs diff <= 1e-6.
    - Text and None: exact equality.
    """
    # Decode expected
    if isinstance(expected, dict) and "error" in expected:
        exp_code = expected["error"]
        if isinstance(actual, XLError):
            return actual.code == exp_code
        if isinstance(actual, str) and actual.startswith("#"):
            return actual == exp_code
        return False
    if isinstance(expected, dict) and "date" in expected:
        exp_date = expected["date"]  # "YYYY-MM-DD"
        if isinstance(actual, datetime.date):
            return actual.isoformat() == exp_date
        if isinstance(actual, str):
            return actual == exp_date
        return False
    if expected is None:
        return actual is None
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(expected, actual, abs_tol=_TOLERANCE, rel_tol=0)
    return expected == actual


@app.get("/api/verify")
def verify(
    n: int = Query(default=200, ge=1, le=500),
    sample_seed: int = Query(default=7),
):
    """Sample n rows from the recorded oracle and compare with the live service."""
    # Load the sample file
    try:
        with gzip.open(_VERIFY_SAMPLE, "rb") as fh:
            sample = json.load(fh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cannot read verify sample: {exc}") from exc

    all_rows = sample["rows"]
    rng = random.Random(sample_seed)
    selected = rng.sample(all_rows, min(n, len(all_rows)))

    cells_compared = 0
    cells_matched = 0
    mismatches: list[dict] = []

    for row in selected:
        policy_raw = row["policy"]
        # Decode the policy: effective_date {"date": "…"} → datetime.date
        policy: dict = {}
        for k, v in policy_raw.items():
            if isinstance(v, dict) and "date" in v:
                policy[k] = datetime.date.fromisoformat(v["date"])
            else:
                policy[k] = v

        result = rater.quote(policy)
        expected: dict = row["expected"]

        for name, exp_val in expected.items():
            act_val = result.get(name)
            cells_compared += 1
            if _values_match(exp_val, act_val):
                cells_matched += 1
            else:
                mismatches.append({
                    "row": row["row"],
                    "policy_id": policy_raw.get("policy_id"),
                    "output_name": name,
                    "expected": exp_val,
                    "service": _encode_output_value(act_val),
                })

    return {
        "rows": len(selected),
        "cells_compared": cells_compared,
        "cells_matched": cells_matched,
        "cells_mismatched": cells_compared - cells_matched,
        "oracle": sample["oracle"],
        "oracle_variant": sample.get("oracle_variant"),
        "tolerance": sample["tolerance"],
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# GET /api/trace
# ---------------------------------------------------------------------------

@app.get("/api/trace")
def trace(
    cell: Optional[str] = Query(default=None),
    function: Optional[str] = Query(default=None),
):
    """Look up traceability by Calc column cell (e.g. "Calc!O") or function name.

    Returns matching STEPS entries from xlsem.STEPS.
    """
    if cell is None and function is None:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of ?cell= or ?function=",
        )

    results = []
    for step in STEPS:
        cell_match = cell is not None and step["cell"].lower() == cell.lower()
        fn_match = function is not None and step["fn"] == function
        if cell_match or fn_match:
            results.append(step)

    if not results and (cell is not None or function is not None):
        # Return empty list with 200, not 404 — caller can check length
        pass

    return {"steps": results, "count": len(results)}
