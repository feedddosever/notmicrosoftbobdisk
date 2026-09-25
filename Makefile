# SheetShift build targets. Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
# Harness module arguments beyond --seed/--n/--service are finalised by the harness owner.

PY      ?= python3
SEED    ?= 2026
N       ?= 10000
SERVICE ?= service.sheetshift_ho3.rater

.PHONY: help workbook manual map oracle patch verify smoke mutate spot certify trace sample site check clean-cache

help:
	@echo "targets: workbook manual map oracle patch verify smoke mutate spot certify trace sample site check"

## Regenerate the synthetic customer workbook + T00 probe (people only; workbook/ is protected)
workbook:
	$(PY) -m tools.gen_workbook --n 40 --seed $(SEED)

## Rebuild the synthetic rating manual PDF from build/rate_tables.json (people only; manual/ is protected)
manual:
	$(PY) -m tools.make_manual

## Map the workbook into build/ (deterministic; CI runs `make map && git diff --exit-code build/`)
map:
	$(PY) -m tools.dump_workbook --expect-lints 3

## Golden inputs and the LibreOffice oracle (CC sandbox / CI only; needs libreoffice-calc)
oracle:
	$(PY) -m harness.generate --seed $(SEED) --n $(N)
	$(PY) -m harness.expand --seed $(SEED)
	$(PY) -m harness.oracle_lo --seed $(SEED)

## Decision-patched workbook and its oracle (reads decisions/decisions.jsonl)
patch:
	$(PY) -m harness.patch_workbook --seed $(SEED)
	$(PY) -m harness.oracle_lo --seed $(SEED) --patched

## Compare the service with the golden oracle and triage the differences
verify:
	$(PY) -m harness.run --golden --seed $(SEED) --service $(SERVICE)

smoke:
	$(PY) -m harness.smoke --n 200 --service $(SERVICE)

mutate:
	$(PY) -m harness.mutate --seed $(SEED) --service $(SERVICE)

spot:
	$(PY) -m harness.spotcheck --seed $(SEED)

trace:
	$(PY) -m harness.trace --service $(SERVICE)

# certify re-runs the comparison and the trace itself; a failing trace gate turns it RED.
certify:
	$(PY) -m harness.certify --seed $(SEED) --service $(SERVICE)

sample:
	$(PY) -m harness.export_sample --seed $(SEED) --service $(SERVICE)

site:
	$(PY) -m tools.build_site_data

check: map
	git diff --exit-code build/
	$(PY) -m pytest -q tests tools/tests
	$(PY) tools/check_modes.py

clean-cache:
	rm -rf build/cache
