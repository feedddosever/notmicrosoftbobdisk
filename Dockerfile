# SheetShift API container: the IBM Code Engine route (documented, not deployed).
# Serves api/index.py, which imports IBM Bob's service/sheetshift_ho3/api.py (or the stub).
# No secrets, no environment variables read by the app; runs as a non-root user.
# Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
#
#   docker build -t sheetshift .
#   docker run --rm -p 8080:8080 sheetshift
#   curl -fsS localhost:8080/api/health

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime dependencies are permissive (fastapi MIT, pydantic MIT); uvicorn (BSD-3-Clause) is
# the container's server only, so it is pinned here rather than in requirements.txt.
COPY requirements.txt ./
RUN pip install -r requirements.txt "uvicorn>=0.30,<1"

# Only what the API needs at runtime (api/, service/, reports/, sheetshift.json): .dockerignore
# excludes everything else, and this works before service/ or reports/ exist (the stub API).
COPY . .

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
