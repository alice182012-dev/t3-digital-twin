---
date_open: 2026-09-23
date_closed: 2026-09-28
type: blocker
status: resolved
severity: P2
subsystem: airflow-pipeline
approaches_tried: 1
approaches_remaining: 1
tags: [blocker, airflow, docker, flood-metrics]
related: ["[[timescaledb-and-flood-metrics]]", "[[flood-metric-extractor]]", "[[timescaledb-schema]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-28
---

# Airflow cannot import flood_utils

## Description

The flood metric extractor cannot run inside Airflow, because it imports a file that the Airflow
containers do not mount.

`scripts/flood_metrics/extract_run.py` reads the per-vehicle impassable depths from
`floodmap/graphhopper-flood-road/scripts/flood_utils.py`. It builds the path in `FLOOD_UTILS_DIR`
(line 25), adds it to `sys.path`, and calls `flood_utils.depth_bands_m` and
`flood_utils.vehicle_types` (lines 75 to 81). The Airflow services in `compose.yml` mount `./dags`,
`./config`, `./plugins`, `./scripts`, and `./data` (lines 53 to 58), not `./floodmap`. Inside a
container, the extractor's `impassable_from_m()` therefore raises `ImportError`.

The extractor's tests pass because they run from a checkout where both folders exist. The failure
appears only when a DAG task calls the extractor in a container.

## Why this matters

The extractor is not wired into any DAG yet. This blocks that wiring, and so it blocks
[[timescaledb-and-flood-metrics]]'s Story 4, which loads the extractor's output into TimescaleDB on
a schedule.

## Approaches tried

### Approach 1

Candidate 1 from Decision and explanation: mount `./floodmap/graphhopper-flood-road/scripts` into
the Airflow containers, read-only (`main` at `245fe66`). Checked the concern below first:
`flood_utils.py` imports only `__future__` and `typing`, both stdlib, so the narrow mount needs
nothing else from `floodmap/`. Deployed on the server with no run in flight
(`docker compose up -d --no-deps` on `airflow-worker`, `airflow-scheduler`, `airflow-dag-processor`,
`airflow-apiserver`, since they share the `airflow-common` volume list). Confirmed live: the mount
exists (`/opt/airflow/floodmap/graphhopper-flood-road/scripts/flood_utils.py` present),
`extract_run.FLOOD_UTILS_DIR.exists()` returns `True`, and calling the extractor's own
`impassable_from_m()` inside the `airflow-worker` container returns real values (`{'motorbike':
0.2, 'car': 0.3, 'truck': 0.35, 'foot': 0.4}`) instead of raising `ImportError`. `airflow dags
list-import-errors` reports nothing after the recreate.

## Decision and explanation

Candidate 1, done (see Approaches tried). Two original candidates, for the record:

1. Mount `./floodmap/graphhopper-flood-road/scripts` into the Airflow containers, read-only, and
   point `FLOOD_UTILS_DIR` at the mounted path. One `compose.yml` line and one path change. The
   extractor and `flood_areas.py` keep reading one file, so metrics and routing cannot drift apart.
   The Airflow containers must be recreated for the mount to take effect.
2. Move `flood_utils.py` under `./scripts`, which Airflow already mounts. This is a larger change
   than it looks. `floodmap-backend` builds from the context `./floodmap/graphhopper-flood-road`
   (`compose.yml` line 376), so a file under `./scripts` is outside that build context. The move
   would also need the backend's build context to widen to the repository root, or a second copy of
   the file, which brings back the drift risk that reading one file avoids.

The first candidate was smaller and kept the single source.

## Concerns

The mounted folder holds only `flood_utils.py` and its neighbors (checked: no other import needed).
Nothing else needed to come along.

## Related topics

- [[flood-metric-extractor]], Open items
- [[timescaledb-and-flood-metrics]], Story 4
- [[graphhopper-backend]], Vehicle thresholds

## Status history

- **2026-09-23, open.** Logged at the user's request from the extractor delegate's report.
  Confirmed against `compose.yml` and `extract_run.py`. The second candidate's build-context
  constraint comes from `compose.yml`'s `floodmap-backend` service.
- **2026-09-28, resolved.** Mounted the narrow folder, deployed with no run in flight, and
  confirmed live: `impassable_from_m()` returns real values inside `airflow-worker`, no DAG import
  errors. Unblocks wiring the extractor into a DAG for [[timescaledb-and-flood-metrics]]'s Story 4,
  which is still not done, only unblocked.
