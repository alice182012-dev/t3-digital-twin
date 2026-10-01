---
date_drafted: 2026-09-23
type: prd
status: draft
subsystem: architecture-backend
source_ideas: []
tags: [prd, architecture, backend, infrastructure, postprocessing]
related: ["[[T3-Digital-Twin_Architecture]]", "[[minio-flood-extent-pipeline]]", "[[graphhopper-backend]]", "[[3di-simulation-orchestration]]", "[[storage-backend-django-layer]]", "[[flood-routing-mockup-frontend-gap]]", "[[verify-table-capability-against-write-path-not-summary-or-current-query]]"]
---

# T3 Digital Twin: architecture gaps between the design and the built system

## Problem

`artifacts/raw/T3-Digital-Twin_Architecture.md` (2026-09-23 rewrite) marks each component of the
original FloodNav design as Built or Designed, not built, against `compose.yml`'s actual service
list. A large share of the backend and infrastructure the design calls for does not exist as code
in this repository: no postprocessing workers beyond the two pipelines that read
`calculate_depth.py`'s output, no multi-role Redis, no TimescaleDB, no citizen-facing REST
endpoints beyond routing and map-tile listing, and no fast-track simulation cadence.

This matters because two of the pipeline's outputs have no home. The flood metric extractor's
values (time-to-peak, pre-closure time, forecast depth) and TimescaleDB's time-series storage are
both needed before any consumer, internal or citizen-facing, can query real per-segment or
per-institution flood history instead of raw depth rasters. Building the citizen and dashboard REST
endpoints, the fast-track cadence trigger, and a dedicated Redis instance are explicitly out of
scope for this PRD (see Decisions). This PRD only prepares the data those would eventually read.

Confirmed against the repo: `compose.yml` lists `airflow-redis` (Airflow's own Celery broker only,
per the architecture doc's §3 note) and no other Redis service, no TimescaleDB service, and
`dags/` holds `flood_mapping_dag.py`, `initial_wl_dag.py`, `manholes_dag.py`,
`calculate_depth_manual_test_dag.py`, `flood_forecast_state_test_dag.py`, and
`dummy_initial_wl_dag.py`, none of which implement postprocessing workers, a fast-track trigger,
or citizen-facing endpoints.

## Goals

- Ship a flood metric extractor that reads `calculate_depth.py`'s per-timestep depth rasters and
  writes time-to-peak, recession onset, per-vehicle passability restoration time, T+1h and T+2h
  forecast depth, and pre-closure time per road segment per vehicle type, matching the definitions
  in the architecture doc's §4.4.
- Stand up TimescaleDB with the schema the architecture doc's §4.9 describes. Populating it is not
  scheduled. The `background_cycle` forecast series and the 24-bar institution histogram, whose bars 7
  to 24 need it, were dropped on 2026-10-01 (D-009 in [[decision-log]]). Depth history and
  `constant_cycle` institution bars have no story.
- Load each timestep's `depth.tif` into PostGIS as a raster (the `postgis_raster` extension) and
  build `GET /flood/points`, returning the exact depth at an arbitrary lat/lon and `valid_time` via
  `ST_Value`. This is scoped narrowly to point-depth lookup, not the full citizen-endpoint bundle
  (see Decisions): `flood_road_values` only has depth at road segments, and `flood_extent_polygon`
  only has banded ranges, so neither can answer an arbitrary-point query at the precision the
  mockup shows ("30 cm", not "20-30 cm").
- Build a route-forecast query, scoped narrowly like `GET /flood/points` above (see Decisions), not
  the descoped `GET /flood/forecast` or `GET /flood/route/forecast`. `flood_road_values` already
  holds what this needs: `scripts/database/geojson_to_pg.py`'s `build_rows` writes one row per
  `(road segment, forecast timestep)` pair from each segment's full `timeseries`, so a
  `constant_cycle` run already has a complete per-segment depth series (25 timesteps, 15-minute
  resolution, 6 hours) sitting in the table today. The query joins a route's road segments against
  that series, buckets it into 30-minute windows, and averages, instead of reading from a table
  that doesn't exist yet.

## Non-goals

- The citizen mobile or web app UI and the council dashboard UI. [[flood-routing-mockup-frontend-gap]]
  covers the gap between the approved mockups and the built frontend. This PRD builds `GET
  /flood/points` for its place-depth popup and per-point depth goals, and a route-forecast query
  for its forecast-chart goal (see Goals), but not the `GET /flood/forecast` or
  `GET /flood/route/forecast` endpoints that goal originally assumed. Those two specific endpoint
  names stay out of scope (see Decisions); the need behind them is served a different way.
- The fast-track (15-minute) simulation cadence trigger on `flood_mapping_dag.py`. Marked no need
  (see Decisions). `flood_mapping_dag.py` keeps its fixed schedule.
- A Redis instance distinct from `airflow-redis`. Marked no need (see Decisions). No postprocessing
  work queue, pub/sub bus, or API response cache is added.
- The rest of the citizen-facing REST endpoints the architecture doc's §4.6 lists as unbuilt
  (`POST /community/report`, `POST /user/location`, `GET /flood/alerts`, `GET /places/flood`).
  Marked no need (see Decisions). `GET /flood/points` and the route-forecast query are the two
  exceptions, both built narrowly under Goals against data `flood_road_values` and a new raster
  table already hold, not against the citizen-endpoint bundle's originally assumed scope.
- The council dashboard's backend endpoint set (`/dashboard/preclosure`,
  `/dashboard/institutions/access`, `/dashboard/dispatch`, `/dashboard/districts/summary`,
  `GET /pipeline/status`). Marked no need (see Decisions).
- FCM or APNs push delivery integration. The architecture doc models this as an external system
  that FloodNav calls, not a channel it owns, and it depends on the `/flood/alerts` poller that is
  itself now out of scope.
- The Phase 3 ride-hailing partner API (`POST /partner/flood/points`, MVT tile serving, per-partner
  API keys). The architecture doc's §11 notes this would extend the already-built vector-tile
  pipeline. It has no dependency on this PRD's scope and is a separable follow-on.
- Hardening `floodmap-backend`'s existing routing and map-tile endpoints. That work is already
  tracked as its own backlog item (`artifacts/TODOS.md`, "Backend hardening/validation for the
  GraphHopper flood-road backend", P2) and isn't new scope this PRD needs to restate.
- Rewriting the flood metric extractor's underlying vectorization to avoid the GRASS GIS
  dependency. The architecture doc's §11 explicitly defers that. This PRD builds on top of the
  existing GRASS-based pipeline.

## Dependencies and assumptions

- The metric extractor reads from `flood_road_values` or `flood_extent_polygon` in
  `storage-postgres`, the same tables `floodmap-backend` already reads (architecture doc §4.2, §5).
  Nothing in this PRD's scope introduces a new data store for routing or map data. It adds
  TimescaleDB only for histogram and time-series data that those tables don't hold.
- `GET /flood/points` assumes the `postgis_raster` extension is available on `storage-postgres` (or
  can be enabled) and that each timestep's `depth.tif` is still reachable at the point the pipeline
  writes it, since `scripts/flood_extent/flood_extent.py` already reads the same file to build
  `flood_extent_polygon`. Loading the raster is a new step alongside that existing read, not a
  replacement for it.
- `ST_Value` lookups need to answer within the popup's interactive latency budget (roughly the same
  budget `GET /flood/areas` already meets for routing). This needs a timing check against a loaded
  raster table before committing to per-request `ST_Value` rather than a pre-computed grid.
- The route-forecast query assumes a route's road segments can be matched against
  `flood_road_values`'s rows. That table has no stable segment ID, only `road_name` (which repeats
  across a road's many segments) and `geom_4326`. Confirm whether GraphHopper's route response
  exposes a matching identifier (a `path.details` entry, similar to `road_environment`), or whether
  a spatial join (`ST_DWithin` against the route polyline) is accurate enough instead, before
  committing to either approach.
- Every new Docker service this PRD adds (TimescaleDB) runs on the remote host only, per this
  repository's `compose.yml` convention (`docker context ls`'s `remote-server` context,
  `ssh://tecotec@100.67.84.55`). A local `docker compose up` against this new service will not
  reflect what's actually running.

## Definition of done

- Given a completed `constant_cycle` run with at least 2 depth timesteps in
  `flood_road_values`, when the metric extractor runs against that run's `run_ts`, then querying
  its output table returns a row per road segment per vehicle type with a non-null time-to-peak,
  pre-closure time, and T+1h forecast depth, matching the values computable by hand from the same
  run's raw depth rasters for one spot-checked segment.
- Given the schema script has run on the TimescaleDB service, when the three hypertables are
  listed, then `institution_histogram_bar`, `background_forecast_depth`, and `depth_history` exist.
  (The earlier bullet that checked 24 hourly bars was dropped on 2026-10-01, D-009 in
  [[decision-log]].)
- Given a completed run with `depth.tif` loaded for at least one `valid_time`, when
  `GET /flood/points?lat=&lon=&valid_time=` is called for a point inside the flooded extent, then
  the response's depth value matches the value read directly from `depth.tif` at that pixel with
  `gdallocationinfo`, for one spot-checked point.
- Given a completed `constant_cycle` run and a route whose segments intersect flooded road
  geometry, when the route-forecast query runs for that route, then it returns one average depth
  value per 30-minute bucket spanning the run's forecast window, matching values computable by hand
  from `flood_road_values`'s raw per-segment `timeseries` rows for one spot-checked bucket.

## Risks and open questions

- No blocker page exists yet for any of this scope. If implementation surfaces a hidden dependency
  the way [[graphhopper-vehicle-profile-rejection]] or [[storage-backend-build-context-missing]]
  did, open one under `artifacts/docs/blockers/` rather than letting the fact live only in a log.
- `ST_Value` reading `depth.tif` directly, per request, may not hold up under concurrent popup taps
  once the raster is large. If the timing check in Dependencies and assumptions shows it's too
  slow, this goal may need a pre-computed lookup grid instead of a live raster query, which is a
  larger change than this PRD currently scopes.
- The route-forecast query's segment-matching approach is unresolved (see Dependencies and
  assumptions). If neither a GraphHopper path-detail nor a spatial join proves accurate enough,
  averaging could include the wrong segments' depth, which would show a plausible-looking but wrong
  number on the chart rather than an obvious failure. Verify against a manually checked route
  before trusting this query's output anywhere in the frontend.

## Decisions

| Date | Question | Decision | Why |
| ---- | -------- | -------- | --- |
| 2026-09-23 | Should this PRD build the fast-track cadence trigger, a dedicated Redis instance, the citizen-facing REST endpoints, and the council dashboard's backend endpoints? | No to all four. Descoped. This PRD now covers only the flood metric extractor and TimescaleDB. | Confirmed by the user. No further rationale recorded. |
| 2026-09-23 | Should `floodmap-backend`'s regression risk (untested since the Valhalla-to-GraphHopper rewrite) be addressed before this PRD adds new load to it? | Yes, test first. Sequence a hardening or regression pass before or alongside this PRD's work. | Confirmed by the user. Reduces the risk of debugging two unknowns (new code, unproven backend) at once. |
| 2026-09-23 | Is a schema design needed for TimescaleDB's histogram tables before implementation starts? | Yes, create one. | Confirmed by the user. |
| 2026-09-23 | `flood_road_values` and `flood_extent_polygon` can't serve arbitrary-point depth (segment-only and band-only, respectively). What should back point-depth queries, given `depth.tif` is always the source of truth? | Load `depth.tif` into PostGIS as a raster and build `GET /flood/points` narrowly for point lookup via `ST_Value`, separate from the rest of the citizen-endpoint bundle, which stays descoped. | Confirmed by the user: depth values are always generated from `depth.tif`, and neither existing table has per-pixel precision. |
| 2026-09-23 | Does the forecast chart's "no confirmed data source" conclusion still hold, now that `flood_road_values`'s write path is checked directly? | No. `geojson_to_pg.py`'s `build_rows` already writes a full per-segment `timeseries` (one row per segment per forecast timestep), not a single snapshot. Build a narrow route-forecast query against it instead of leaving the goal blocked or reopening `GET /flood/forecast` or `GET /flood/route/forecast`. | The earlier conclusion was reasoned from the architecture doc's one-line schema summary and `flood_areas.py`'s single-timestep query, not from the table's write path. See [[verify-table-capability-against-write-path-not-summary-or-current-query]]. |
| 2026-10-01 | The pipeline no longer runs `background_cycle`. What happens to the goal that populates TimescaleDB with institution histograms and the `background_cycle` forecast series? | Dropped. Every story that needs `background_cycle` is dropped, and the 24-bar histogram goal with it. TimescaleDB stays stood up and empty. | Confirmed by the user. Bars 7 to 24 of the histogram come from `background_cycle`. See D-009 in [[decision-log]]. |

## Rollback

The new TimescaleDB service, the metric extractor's output tables, and the raster table backing
`GET /flood/points` are additive: none of them change `flood_road_values`, `flood_extent_polygon`,
or any endpoint `floodmap-backend` already serves. Reverting means removing the TimescaleDB service
definition from `compose.yml`, dropping `GET /flood/points`, and dropping the new TimescaleDB,
metric-extractor, and raster tables. None of it requires a migration or backfill of existing data,
since nothing built under this PRD is read by the routing or map-tile paths already in production.

## Status history

- **2026-09-23, draft.** Drafted from a comparison between
  `artifacts/raw/T3-Digital-Twin_Architecture.md`'s Built and Designed-not-built split and the
  actual `compose.yml`, `dags/`, and `scripts/` contents.
- **2026-09-23, draft.** Descoped the fast-track trigger, Redis, citizen endpoints, and council
  dashboard endpoints per Decisions. Scope is now the flood metric extractor and TimescaleDB only.
- **2026-09-23, draft.** Added `GET /flood/points` back into scope, narrowly, as a raster-backed
  point-depth lookup: neither `flood_road_values` nor `flood_extent_polygon` can serve arbitrary-
  point depth, and `depth.tif` is always the source of truth.
- **2026-09-23, draft.** Added a route-forecast query goal, narrowly scoped like `GET /flood/points`
  above. `flood_road_values` already holds a full per-segment forecast time series, reversing the
  earlier "no data source" conclusion for [[flood-routing-mockup-frontend-gap]]'s forecast-chart
  goal. See [[verify-table-capability-against-write-path-not-summary-or-current-query]].
- **2026-10-01, draft.** Dropped the `background_cycle` and 24-bar histogram population goal at the user's request (D-009 in [[decision-log]]). Goal 2 now stands up TimescaleDB only, and its Definition of done bullet checks that the tables exist.
