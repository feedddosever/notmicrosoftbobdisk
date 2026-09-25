# Provenance

How and when the work in this repository was produced. All times are UTC. Nothing here
is backdated: commit timestamps are the times the work was committed.

The dates embedded in the generated documents (the workbooks' `docProps/core.xml`, 2026-01-01,
and the manual PDF's creation date, 2026-10-01) are fixed placeholders chosen so that the builds
are byte-reproducible. They are not authoring dates.

## Timeline

| When | What | Where |
|---|---|---|
| Before 15:00, Fri 25 Sep 2026 | Ideation and research only: an idea bank, background research and reading the public IBM Bob documentation. No product code. | Outside this repository |
| From 16:03, Fri 25 Sep 2026 | Claude Code (an AI coding agent) ran feasibility spikes in a private sandbox: a prototype workbook generator, dependency-graph extractor, LibreOffice oracle and harness. Spike files are dated 16:03 to 16:49. | Private sandbox, **not** in this repository |
| From the first commit | All repository code, data and documents. | This repository |

## What carried over from the spikes

- The spikes were used to measure feasibility (engine choice, run times, lint rules).
  Tooling in `tools/` and `harness/` was ported from them by Claude Code and is
  attributed in `ATTRIBUTION.md`.
- The spikes' hand-written reference translation of the workbook was **not** copied
  into this repository. The service under `service/` is written by IBM Bob.
- The spikes used a placeholder carrier name that turned out to match a real insurance
  brand. It was replaced everywhere with **Example Mutual Insurance Co. (FICTIONAL)**.
  The old name appears nowhere in this repository; CI checks a hashed denylist.

## Repository renames

None yet. If the repository is renamed, the date and the old and new names are
recorded here.

## Changes to protected constants

Changes to the comparison tolerance or other harness constants are made by a person in
a commit that states the reason here.
