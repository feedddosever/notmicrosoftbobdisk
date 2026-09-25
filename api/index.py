"""Vercel entry point for the SheetShift API.

Serves IBM Bob's FastAPI app (service/sheetshift_ho3/api.py) once it exists. Until then it
serves a stub: GET /api/health answers {"status": "stub", "env_vars": 0} and every other
/api route answers 503. Only a *missing* api module selects the stub; if Bob's api.py exists
but fails to import, the error is raised so a broken deploy is never hidden behind the stub.

No environment variables are read here (tests/test_no_env.py enforces this).
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_MISSING_OK = {"service", "service.sheetshift_ho3", "service.sheetshift_ho3.api"}


def _stub_app():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    stub = FastAPI(title="SheetShift API (stub)", version="0",
                   description="Placeholder until IBM Bob's service/sheetshift_ho3/api.py lands (task T04).")

    @stub.get("/api/health")
    def health():
        return {"status": "stub", "env_vars": 0,
                "detail": "IBM Bob's API (service/sheetshift_ho3/api.py) is not deployed yet."}

    @stub.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def not_yet(rest: str):
        return JSONResponse(status_code=503, content={
            "status": "stub", "error": "not available yet", "path": "/api/" + rest})

    return stub


try:
    from service.sheetshift_ho3.api import app  # noqa: F401  (IBM Bob's app, task T04)
except ModuleNotFoundError as e:
    if e.name not in _MISSING_OK:
        raise
    app = _stub_app()
