---
date_open: 2026-09-23
date_closed: 
type: blocker
status: open
severity: P2
subsystem: airflow-pipeline
approaches_tried: 0
approaches_remaining: 2
tags: [blocker, airflow, docker, flood-metrics]
related: ["[[timescaledb-and-flood-metrics]]", "[[flood-metric-extractor]]", "[[timescaledb-schema]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-23
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

None yet.

## Decision and explanation

Pending. Two candidate fixes, neither tried.

1. Mount `./floodmap/graphhopper-flood-road/scripts` into the Airflow containers, read-only, and
   point `FLOOD_UTILS_DIR` at the mounted path. One `compose.yml` line and one path change. The
   extractor and `flood_areas.py` keep reading one file, so metrics and routing cannot drift apart.
   The Airflow containers must be recreated for the mount to take effect.
2. Move `flood_utils.py` under `./scripts`, which Airflow already mounts. This is a larger change
   than it looks. `floodmap-backend` builds from the context `./floodmap/graphhopper-flood-road`
   (`compose.yml` line 376), so a file under `./scripts` is outside that build context. The move
   would also need the backend's build context to widen to the repository root, or a second copy of
   the file, which brings back the drift risk that reading one file avoids.

The first candidate is smaller and keeps the single source. Choose it unless a reason to relocate
`flood_utils.py` appears.

## Concerns

The mounted folder holds only `flood_utils.py` and its neighbors. Mount the narrowest folder that
works, so the Airflow containers do not see the rest of `floodmap/`. Check that `flood_utils.py`
imports nothing that is absent in the Airflow image.

Airflow runs on the remote host only. Test the fix there with the extractor's real import, not
only in a local checkout.

## Related topics

- [[flood-metric-extractor]], Open items
- [[timescaledb-and-flood-metrics]], Story 4
- [[graphhopper-backend]], Vehicle thresholds

## Status history

- **2026-09-23, open.** Logged at the user's request from the extractor delegate's report.
  Confirmed against `compose.yml` and `extract_run.py`. The second candidate's build-context
  constraint comes from `compose.yml`'s `floodmap-backend` service.
