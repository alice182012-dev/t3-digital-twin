---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: architecture-backend
source_ideas: []
related: ["[[t3-digital-twin-architecture-gaps]]", "[[sprint-plan]]", "[[graphhopper-backend]]"]
tags: [user-story, epic, backend, sprint-1, sprint-2]
---

# Epic: point-depth lookup backend

Builds `GET /flood/points`, the endpoint [[t3-digital-twin-architecture-gaps]] scopes narrowly for
raster-backed point-depth lookup. Rows carry Priority, Estimate, and Sprint in addition to the
standard Epic fields, per this vault's user-story sprint-delegation convention (see
`.claude/CLAUDE.md`, "User stories and sprint planning").

- **Story 1 (done): Regression-harden `floodmap-backend` before adding new load.**
  As an engineer, I want `server.py` and `flood_areas.py` covered by a regression or test pass, so
  I can add a new endpoint without debugging two unknowns (new code, an unproven backend) at once.
  Given the architecture doc's §11 flags `floodmap-backend` as untested since the
  Valhalla-to-GraphHopper rewrite, when a regression or test pass runs against its existing routing
  and flood-grading behavior, then a real request and response confirms both still work before any
  new endpoint work starts.
  `backend/test_flood_areas.py` and `backend/test_server.py` cover `derive_areas()`,
  `build_custom_model()`, and `server.py`'s full HTTP surface (`/health`, `/flood/areas`,
  `POST /route` graded and ungraded) against a real PostGIS and a stub GraphHopper. Both ran clean
  against `postgis/postgis:15-3.4`. `artifacts/TODOS.md`'s broader hardening item (a soak period, a
  side-by-side comparison against the old Valhalla backend) is still open; this story covered only
  the regression-test half of that item.
  Priority: P0. Status: Done. Estimate: M. Sprint: 1. Dependencies: None.
  Evidence: ![[harden-floodmap-backend-tests.png|420]]
  Details: What: regression tests for `server.py` and `flood_areas.py`. How: `test_flood_areas.py` and `test_server.py` run against a real PostGIS and a stub GraphHopper. Why: `GET /flood/points` would otherwise land on an unproven backend. Effect: unblocks the point-depth stories. The soak period and the Valhalla comparison stay open in `TODOS.md`.

- **Story 2 (done): Load `depth.tif` into PostGIS as a raster.**
  As the point-depth lookup endpoint, I want each timestep's `depth.tif` available as a PostGIS
  raster, so I can answer an arbitrary-point depth query without reading the file from disk per
  request.
  Given a completed run and the `postgis_raster` extension enabled on `storage-postgres`, when the
  raster-load step runs for that run's `depth.tif`, then querying the raster table for that
  `valid_time` returns a non-null raster whose extent matches the source file.
  `scripts/flood_extent/raster_load.py` reprojects each `depth_*.tif` from EPSG:3405 to EPSG:4326
  with `gdal.Warp`, then loads it into `flood_depth_raster` (`run_ts`, `valid_time_utc`, `rast`)
  with `ST_FromGDALRaster`. `scripts/database/create_flood_depth_raster_tables.py` creates the
  table, and `dags/flood_mapping_dag.py`'s `9b_load_depth_raster` task runs beside
  `9_build_flood_tiles`. The loader sets `postgis.gdal_enabled_drivers = 'GTiff'` per session,
  because PostGIS disables every GDAL driver by default. `ST_Value` at one spot-checked point
  matched the source pixel of a real 9901x5656 `depth.tif` to float32 precision. Shipped in commit
  `118e04a`.
  Priority: P0. Status: Done. Estimate: M. Sprint: 1. Dependencies: None.
  Evidence: ![[depth-raster-postgis-load.png|420]]
  Details: What: each timestep's `depth.tif` becomes a row in `flood_depth_raster`. How: `raster_load.py` reprojects EPSG:3405 to EPSG:4326 and loads it with `ST_FromGDALRaster`, in DAG task `9b_load_depth_raster`. Why: a point lookup needs the exact pixel. Effect: unblocks `GET /flood/points`. On the server, the row for run `20260924T153638` matches the source file's size and corner. The DAG task has not run there yet.

- **Story 3: Build `GET /flood/points`.**
  As a frontend developer, I want an endpoint that returns the exact depth at an arbitrary lat/lon
  and timestep, so I can source the place-depth popup and per-point depth figures from a single
  source of truth instead of a road-segment or banded-polygon approximation.
  Given a completed run with `depth.tif` loaded for at least one `valid_time`, when
  `GET /flood/points?lat=&lon=&valid_time=` is called for a point inside the flooded extent, then
  the response's depth value matches the value read directly from `depth.tif` at that pixel with
  `gdallocationinfo`, for one spot-checked point.
  Priority: P0. Status: Done. Estimate: M. Sprint: 2. Dependencies: Story 1, Story 2.
  Evidence: ![[flood-points-endpoint.png|420]]
  Details: What: `GET /flood/points` returns the depth at a lat/lon and timestep. How: `flood_points.py` reads `flood_depth_raster` with `ST_Value`. A pixel of 0 reads `dry`, and a point outside the raster reads `no_data`. Why: the popup and badges need the exact pixel, not a band. Effect: unblocks the latency check and the three Sprint 3 point stories. Without `run=`, it returns 404 when the newest run has no raster. On a real `depth.tif`, it matched `gdallocationinfo` at three points.

- **Story 4: Validate `GET /flood/points`'s latency under concurrent taps.**
  As an engineer, I want to know whether a live `ST_Value` query holds up under concurrent popup
  taps, so I can decide before Sprint 3 whether the frontend can call this endpoint directly or
  needs a pre-computed lookup grid instead.
  Given the raster table loaded, when concurrent `ST_Value` queries run at a rate matching expected
  popup-tap traffic, then response times land within the same interactive latency budget the
  existing `GET /flood/areas` call already meets.
  Priority: P0. Status: Not started. Estimate: S. Sprint: 2. Dependencies: Story 3.

## Status history

- **2026-09-23, draft.** Drafted from [[t3-digital-twin-architecture-gaps]]'s Goals, Dependencies
  and assumptions, and Definition of done sections.
- **2026-09-23, draft.** Story 1 done: added `backend/test_flood_areas.py` and
  `backend/test_server.py`, both passing against a real PostGIS and a stub GraphHopper. Story 2
  (raster load) is next.
- **2026-09-23, draft.** Story 2 done in commit `118e04a`: the `flood_depth_raster` table and the
  `9b_load_depth_raster` task. Story 3 (`GET /flood/points`) is next.
- **2026-09-23, draft.** Story 3 built and reviewed on branch `worktree-agent-af5d6b004a774583a`
  (commits `80c6843` and `e3a0a95`). `GET /flood/points` returns `wet`, `dry`, or `no_data`. Its
  tests pass against a local PostGIS, and the wet case matches `gdallocationinfo` on a synthetic
  `depth.tif` to float32 precision. Status is `Reviewed`, not `Done`, because the acceptance check
  names a real `depth.tif`, and none has run against the real `storage-postgres`.
- **2026-09-24, draft.** Story 3 done. On the remote host, `GET /flood/points` matched
  `gdallocationinfo` on a real `depth.tif` (`depth_20260924_170639.tif`, run `20260924T153638`) at
  three points: 6.812467575073242 against 6.81246757507324, 0.17372192442417145 against
  0.173721924424171, and 0.0 against 0. A point outside the raster returned `no_data`, an unknown
  `valid_time` returned 404, and a latitude of 95 returned 400. `storage-postgres` runs in
  `Etc/UTC`, so the timestamp handling holds. Story 4 (latency) is next.
