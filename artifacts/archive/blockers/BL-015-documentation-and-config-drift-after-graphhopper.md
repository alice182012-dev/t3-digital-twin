---
date_open: 2026-09-30
date_closed: 2026-09-30
type: blocker
status: resolved
severity: P3
subsystem: docs, config
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, docs, config, drift]
related: ["[[graphhopper-backend]]", "[[3di-simulation-orchestration]]", "[[EP-07-carried-over-backlog|carried-over-backlog]]"]
last_updated: 2026-09-30
---

# Documentation and config drift after the move to GraphHopper

## Description

The README rewrite of 2026-09-30 compared every claim with the code and found older files that no longer
match it. Each was checked in the repository.

- **`.env.example`.** It sets `VALHALLA_PORT` and `FLOODMAP_FRONTEND_PORT`, and nothing in `compose.yml` or
  the code reads either. It sets `POSTGRES_HOST_PORT=5433`, while `compose.yml` defaults to 5432
  (`"127.0.0.1:${POSTGRES_HOST_PORT:-5432}:5432"`). It has no `THREEDI_API_PERSONAL_API_TOKEN`, which
  `compose.yml` passes on and `scripts/threedi_client.py` needs.
- **A dead link name.** `artifacts/Home.md` and four concept pages link `[[SW Architecture]]`
  (`graphhopper-backend`, `routing-depth-threshold-model`, `minio-flood-extent-pipeline`,
  `3di-simulation-orchestration`). The file is `artifacts/raw/T3-Digital-Twin_Architecture.md`. Code comments
  such as the docstring of `floodmap/graphhopper-flood-road/backend/server.py` name the old file too.
- **A concept page that contradicts itself.** `artifacts/docs/concepts/3di-simulation-orchestration.md` line 56
  says the DAG uses `VNContinuousTimetable` with `max_active_runs=1`. Line 61 and `dags/flood_mapping_dag.py`
  say cron `*/15 * * * *` with `catchup=False` and `max_active_runs=2`. The code is right.
- **`floodmap/graphhopper-maps/PINNED_COMMIT.md`.** It lists `TimeSlider.tsx` and its stylesheet, which
  `src/floodmap/` no longer has.
- **The raw architecture doc.** `artifacts/raw/T3-Digital-Twin_Architecture.md` is older than the code in six
  places: the rain source, the backend framework, two endpoints marked not built, TimescaleDB marked not built,
  a `flood-results-full` bucket, and the 30-minute GeoJSON pipeline. It is the user's read-only material, so it
  is not edited. The README and the concept pages carry the current picture.

## Why this matters

A new teammate who copies `.env.example` gets a stack that fails to start for a missing token, and follows
two dead links. The contradicting concept page says the DAG cannot overlap runs, while the DAG allows two.
Nothing here changes what runs.

## Blocks further build?

No. Rule 11 of `.claude/CLAUDE.md` applies: the README states the correct values, and no Sprint 4 story reads
any of these files. A subagent fixes it while work continues.

## Approaches tried

None yet.

## Candidate approaches

1. **Fix each file to match the code.** Docs and config only, no behavior change. Do not edit
   `artifacts/raw/`. Report anything that needs the user, such as the raw architecture doc and any mention in
   `.claude/CLAUDE.md`. Small.

## Decision and explanation

Pending. Approach 1 goes to a subagent under rule 11.

## Related topics

- [[graphhopper-backend]]
- [[3di-simulation-orchestration]]

## Status history

- **2026-09-30, open.** Found by the README rewrite. Facts checked in the repository. Rule 11 case: does not
  block further build, so a subagent fixes it.
- **2026-09-30, open.** The subagent's fix landed as `1792d37`. The blocker stays `open` until the acceptance check of `US-038` passes.
- **2026-09-30, resolved.** `us-038-drift-check.sh` passes all four checks (see `us-038-drift-check-output.png`).
