---
date: 2026-09-22
type: concept
status: active
tags: [graphhopper, routing]
related: ["[[T3-Digital-Twin_Architecture]]", "[[2026-09-14]]", "[[BL-001-graphhopper-vehicle-profile-rejection|graphhopper-vehicle-profile-rejection]]", "[[BL-004-flood-route-missing-geom-column|flood-route-missing-geom-column]]", "[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[raster-first-flood-pipeline]]", "[[minio-flood-extent-pipeline]]", "[[flood-on-roads]]", "[[decision-log]]"]
last_updated: 2026-10-13
---

# GraphHopper flood-road backend

`floodmap/graphhopper-flood-road/backend/server.py` sits between the frontend and the `graphhopper`
service, which runs the time-aware image `graphhopper-time-aware:local` (see "The pinned stock image,
and why the `foot` profile was blocked"). It answers flood queries GraphHopper cannot answer on its own, and proxies
the rest of GraphHopper's API unchanged.

## Why a separate backend exists

GraphHopper computes a route from a `custom_model`, a JSON document that grades each road segment's
cost. The frontend cannot build that document itself: the flood polygons for a given timestep and
vehicle type live in PostGIS, not in the browser, and can run to around 1,000 vertices. `server.py`
derives the `custom_model` server-side, from PostGIS, and forwards the graded request to GraphHopper.
Both `GET /flood/areas` (the map overlay) and `POST /route` (routing) call the same derivation
function, `flood_areas.derive_areas`, so the overlay a user sees and the areas GraphHopper actually
routes around can never drift apart.

## Flood tables, one intentional split

The backend reads from separate PostGIS tables, and they are not interchangeable:

- `flood_road_values`, keyed by `(timestamp, forecast_time)`. `flood_areas.py` reads this table to
  build the `custom_model` for routing. The task `flood_on_roads` of the DAG `routing_adapter` writes it
  from `flood_depth_raster_tile`, so it has its own writer and its own timing.
- `flood_extent_polygon`, keyed by `(run_ts, valid_time_utc, dn_code)`, and `flood_extent_step`, keyed
  by `(run_ts, valid_time_utc)`. `flood_extent_runs.py` reads the polygon table for `GET /flood/runs`
  and the step table for `GET /flood/timesteps`, the map's timestep picker. See
  [[minio-flood-extent-pipeline]] for how this table gets populated.
- `flood_depth_raster_tile`, keyed by `(run_ts, valid_time_utc, tile_y, tile_x)`, one EPSG:4326
  raster tile per row. `flood_points.py` reads it to back `GET /flood/points`. `scripts/flood_extent/raster_load.py`
  loads it from the same `depth.tif` files as `flood_extent_polygon`, so both tables share run and
  timestep keys.

Routing and map display run on different cadences and different upstream pipelines on purpose. Do
not point the routing derivation at `flood_extent_polygon`, and do not point the timestep picker at
`flood_road_values`. `artifacts/raw/T3-Digital-Twin_Architecture.md`, section 4.2, records the decision.

## Request flow for POST /route

`graphhopper-maps` sends its route request body unchanged; that body already carries three extra
fields the vendored frontend fork adds: `valid_time`, `run`, `vehicle_type`. With `TIME_AWARE_ROUTING`
off, the default in `compose.yml`, `_handle_route` in `server.py` does four things. The flag-on path is
in "The engine in the backend (US-052)".

1. Strips those three fields plus `buffer`, `simplify`, and `min_area` from the body.
2. Calls `flood_areas.derive_areas` (through a 30-second in-process cache, `cached_areas`) to get
   the flood polygons for that timestep and vehicle.
3. If any polygons come back, sets `ch.disable: true` and attaches the derived `custom_model` to
   the body. `ch.disable` is required because contraction hierarchies precompute routes assuming a
   fixed cost graph; a per-request flood-graded model needs flexible mode instead.
4. Forwards the rest of the body to GraphHopper's own `/route` and returns its response unchanged,
   so `graphhopper-maps`' `Api.ts` needs no changes to parse it. A GraphHopper error goes through the
   same way: `route_error_payload()` sends its JSON, with `message` and `hints`, at the original
   status. Any other failure becomes `{"message": text, "error": text}`. Before 2026-09-30 the body
   was `{"error": "<JSON as text>"}`, which left the frontend's error banner empty.

## Endpoints

| Path | Method | Purpose |
|---|---|---|
| `/health` | GET | Backend, GraphHopper, and PostGIS health in one payload. |
| `/info`, `/nearest` | GET | Proxied to GraphHopper unchanged; no flood logic. |
| `/flood/runs` | GET | Distinct `run_ts` values from `flood_extent_polygon`. |
| `/flood/timesteps` | GET | Timesteps for one run, converted back to Vietnam local time. |
| `/flood/mode` | GET | The forecast mode, `LIVE`, `PENDING`, or `DEMO`, with the time of the decision and, in `DEMO`, the pinned run and step (`flood_mode.py`, US-130). |
| `/flood/areas` | GET | The same flood polygons `POST /route` grades against, for the map overlay. |
| `/flood/points` | GET | Exact depth at one lat/lon and timestep, from `flood_depth_raster_tile`. |
| `/route` | POST | Flood-graded route; see the flow above. |
| `/route/departures` | POST | When the usual route first clears, from the edge depth table. See "The departures endpoint (US-053)". |
| `/flood/forecast` | POST | Mean depth, maximum depth, and wet fraction along a route for up to 8 steps of 15 minutes, from `flood_depth_raster_tile` (`flood_forecast.py`). |
| `/flood/profile` | POST | Depth at evenly spaced samples along a route at one `valid_time`, from `flood_depth_raster_tile` (`flood_profile.py`). |
| `/places/search`, `/geocode` | GET | Place search, backed by `place_search.py`. |
| `/places/reverse` | GET | The nearest named Vietnamese place to `lat` and `lon` (Photon `/reverse`), as `{"result": {name, address, ...} or null}`. Backs the place-depth popup. |

## Forecast mode and the demo step (US-130)

`flood_mode.read_mode` reads the newest row of `forecast_mode` and, in `DEMO`, the row of `demo_pin`. A database without the tables, or without a decision, is `LIVE`, which is how the backend behaved before.
In `DEMO` with a pinned step, `GET /flood/areas`, `GET /flood/points`, and `POST /route` replace the `run` and `valid_time` of the request with the pinned ones.
`POST /route` skips the time-aware engine in this case, even with `TIME_AWARE_ROUTING` on, and sends today's request with the flood areas of the pinned run.
The engine reads only the table that `latest` names and floors the departure to the clock, so it cannot judge a stored step.
In `DEMO` with no pinned step, and in `LIVE` and `PENDING`, the three calls read the newest run.
`POST /flood/forecast` and `POST /flood/profile` do not change with the mode.
The point read needs the raster tiles of the pinned step, which [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] rebuilds.
The role `routing_reader` needs `SELECT` on `forecast_mode` and `demo_pin`, so rerun `create_routing_reader_role.py` after the tables exist.

## Point depth lookup

`GET /flood/points?lat=LAT&lon=LON&valid_time=VALID_TIME&run=RUN` returns the depth that
`ST_Value` reads from the run's raster at that point. `run` is optional and defaults to `latest`.
`valid_time` needs a UTC offset, as `GET /flood/timesteps` returns it, for example
`2026-05-22T16:00:00+07:00`. URL-encode it, because a bare `+` in a query string decodes as a space.

The endpoint picks a run with the rule `list_timesteps` uses. An explicit `run` pins that run.
`latest` resolves through `flood_extent_runs.latest_run()`, the newest `run_ts` in
`flood_extent_polygon`. If the newest run has no raster for that `valid_time`, the endpoint returns
404. It never falls back to an older run.

A 200 response has this shape:

```json
{"lat": 21.0398, "lon": 105.8019, "valid_time": "2026-05-22T16:00:00+07:00",
 "run": "20260522T120000", "status": "wet", "depth_m": 12.53}
```

| `status` | `depth_m` | Meaning |
|---|---|---|
| `wet` | the raster value, in meters | The pixel at the point holds a depth greater than 0. |
| `dry` | `0.0` | The point is inside the raster, and its pixel is 0 or NoData. |
| `no_data` | `null` | The point is outside the raster extent. |

`calculate_depth.py` rewrites NoData, negative, and out-of-range pixels to 0, then declares 0 as
NoData. Inside the raster, the source can't tell a dry cell from a cell the model didn't cover, so
both read as `dry`. Only a point outside the raster is detectably `no_data`.

| HTTP status | Cause |
|---|---|
| 400 | `lat` or `lon` is missing, not a number, or out of range. |
| 400 | `valid_time` is missing, not ISO 8601, or has no UTC offset. |
| 404 | No run is loaded, or the chosen run has no raster for `valid_time`. |

### How the lookup reads the tiles

`flood_points.py` runs one query that selects the tiles of `(run, valid_time)` whose
`ST_ConvexHull(rast)` intersects the point, through the GIST index on that expression, and calls
`ST_Value` on each. A point on a shared tile edge intersects up to four tiles. Only the tile that
owns the pixel returns a value, and the others return `NULL`, so the endpoint takes the first
non-null value. If no tile returns a value, a second query checks whether any tile exists for
`(run, valid_time)`. A timestep with tiles means the point is outside the raster (`no_data`). A
timestep without tiles is a 404. The endpoint never infers a 404 from an empty result alone.

On a local PostGIS 3.6.4 with the real `depth_20260924_170639.tif`, the tiled query takes 0.2 ms
with the tile in memory and 0.9 ms with it evicted from `shared_buffers`. The whole-raster query it
replaced took 69 ms and 94 ms on the same machine. `server.py` opens a new connection for every
request, and the first raster function call in a new PostgreSQL backend loads the PostGIS raster
library, which took 56 ms locally. A full request is therefore about 58 ms locally, down from about
150 ms. The server's own latency has not been measured after this change.

## The pinned stock image, and why the `foot` profile was blocked

`compose.yml` builds the `graphhopper` service from `java/time-aware-routing` as
`graphhopper-time-aware:local`. The `Dockerfile` of that folder starts from the stock image
`israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`
(`ARG STOCK_IMAGE`), a 12.0-SNAPSHOT build pinned by digest rather than `:latest`. A comment in
`compose.yml` keeps the same digest as the rollback line. The `ch.disable`-in-body behavior the
routing flow above depends on is undocumented in that build and could change without notice, so the
pin is deliberate: re-pull only after re-running the `ch.disable` smoke test.

Adding any new vehicle profile used to fail at startup with `Cannot compile expression:
'<name>_access' not available`, thrown from GraphHopper's own `checkProfilesConsistency()`. This
was not a broken build. The stock image's `graphhopper.sh` entrypoint defaults its graph output
directory to `/data/default-gh` and always passes it as a `-Ddw.graphhopper.graph.location` JVM
system property, which overrides `config.yml`'s `graph.location: /data/graph-cache` setting
(Dropwizard system-property overrides win over the YAML file). `compose.yml` never
passed the `-o` flag that changes that default, so the app always loaded a graph baked into the
image at `/data/default-gh`, imported once with only `car_access`, `hgv`, and the other three
built-in profiles' encoded values, before this repository's history starts. `/data/graph-cache`,
the actual mounted volume, was never used at all, which is why every earlier attempt saw no import
progress and an empty cache directory. Fixed by adding `-o /data/graph-cache` to the `graphhopper`
service's `command` in `compose.yml` (`run-time-aware.sh` takes the same `-c` and `-o` options), which makes the app import the mounted OSM extract into
the real, persistent volume using whatever `graph.encoded_values` `config.yml` declares.
`graphhopper/config.yml` now registers a fourth profile, `foot`, backed by `foot_custom.json`
(`foot_priority` stays trimmed out; see that file's own comment for why). See
[[BL-001-graphhopper-vehicle-profile-rejection|graphhopper-vehicle-profile-rejection]] for the full investigation. `truck` was a separate
config gap: GraphHopper already served it, but `config-local.js.example`'s `profiles` object did
not list it. It does since 2026-09-29 (see [[US-022-truck-routing-profile|truck-routing-profile]]).

## Flood areas grade each road piece on its deepest stretch

`flood_areas.derive_areas` sorts the road pieces of one run and timestep into three bands, each a
fraction of the vehicle's limit. Band `b4`, at the limit or deeper, is impassable.
[[routing-depth-threshold-model]] lists the bands and their costs.

The bands compare `depth` from `flood_road_values`. On rows that
`scripts/flood_roads/flood_on_roads.py` writes, `depth` is the deepest 1 m sample along the piece. A
road piece that is too deep on one short stretch can't be passed, so the maximum is the right test.
The user chose the maximum for every reader in D-006 of [[decision-log]], and [[flood-on-roads]] has
the comparison behind it. Rows from the old GeoJSON chain carry one pixel of a 20 m cell in `depth`,
and the bands grade them the same way. Routing doesn't read `segment_id`.

`backend/test_flood_areas.py` builds its table from `scripts/database/create_flood_road_tables.py`'s
`SQL`, the DDL the server runs. For each vehicle, with the limit read from `flood_utils.py`, it checks
that a piece at 1.1 times the limit is in `b4` and a piece at 0.9 times the limit is not. It also
checks one run that mixes old-chain rows and `flood_on_roads.py` rows.

## Vehicle thresholds

`floodmap/graphhopper-flood-road/scripts/flood_utils.py`'s `VEHICLE_PROFILES` sets the depth at which
a road piece becomes impassable for each vehicle: motorbike 20 cm, car 30 cm, truck 35 cm, foot
40 cm. The backend compares that limit with the piece's `depth`.
All four limits apply, because a GraphHopper `foot` profile exists to use the `foot` entry.
`FloodStore` no longer sends `vehicle_type` (`18d1c42`, 2026-09-28), so `server.py` uses each
request's own `profile` and each vehicle gets its own limit. See
[[BL-005-flood-routing-vehicle-type-always-motorbike|flood-routing-vehicle-type-always-motorbike]] (resolved).

## Soak and known-answer check

`scripts/backend_soak/run_soak.sh` gives the verdict of the soak (`US-034`). It reads the state of the three containers, scans their logs since the soak start, and runs `soak_checks.py roads` inside `airflow_new-floodmap-backend-1`. It exits with 0 only if every Docker call answered, no container started inside the window or was OOM killed, no log holds a 5xx response or an error line, and no check failed. A log with no timestamped line fails, because a failed read leaves only error text (`US-064`). `soak_checks.py` also has a `latency` command, which `US-046` used for the baselines in [[BL-011-routing-not-time-aware|routing-not-time-aware]], and tests in `scripts/backend_soak/` (42).

The `roads` check reads one run and step of `edge_depth` and picks road pieces (edges of `graph_edge`) in five depth buckets: below every limit, between the motorbike and car limits, between the car and truck limits, between the truck and foot limits, and past every limit. The pick is deterministic (`md5` of the segment id). A piece is a candidate only if its two neighbours on the same way exist and are no deeper than the next limit, and no piece that would block an allowed vehicle lies within about 170 m. For each piece, each profile, and both directions, the check routes from the neighbour before the piece to the neighbour after it. It sends the request once with the flood fields and once without, the dry control. `expected_outcome` takes the promise from the bands of `DEPTH_BANDS`.

| Depth against the vehicle's limit | Band | Promise | Pass when |
| --- | --- | --- | --- |
| At or above the limit | b4, priority 0 | Blocked | No route crosses the piece. |
| From 0.5 times the limit up to the limit | b2 and b3, priority 0.2 and 0.05 | Costly | A route exists. |
| Below 0.5 times the limit | none | Open | A route crosses the piece. |

The check skips a pair when the dry control cannot show the promise. For a blocked or open promise the dry route must cross the piece. For a costly promise the dry route must exist. In those pairs the network (a one-way piece, a dual carriageway, a road closed to foot) and not the flood decides the result.

Run on the 2026-10-02 03:00 run, the check covered 23 roads and 92 pairs of road and profile. It passed 86, skipped 6, and failed none. All 40 blocked promises held.

With `TIME_AWARE_ROUTING` on, the engine ignores the `run` and `valid_time` of a request. It departs at the later of `valid_time` and the clock, floors that to a step of the newest table, and reports `td.run` and `td.departure` in the hints. Without `--run` and `--valid-time`, the `roads` check therefore sends one probe route, reads those hints, and picks edges at that step (`engine_cell` in `soak_checks.py`). A replayed run is judged at its last step. In `DEMO` mode every route uses the pinned step and the probe finds no `td.run`, so run the check in `LIVE` mode.

On 2026-10-13 the check covered 26 roads and 104 pairs at run `20261011T001500`, 19:00 UTC. It passed 42, skipped 62, and failed none. All 51 blocked pairs were skipped, because the dry control route did not cross the piece, so that run shows no kept blocked promise ([[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]]).

### What a stricter first version found

A first version with a smaller neighbourhood (about 60 m) failed 3 of 120 pairs. The truck and the foot walker found no route across two roads whose depth (32.5 cm and 33.4 cm) lies below their limits (35 cm and 40 cm). One of them was the overpass `Cầu vượt Phú Đô` (`way/596300521#1`). The dry control found a 137 m route, and no piece of 35 cm or more lies within 136 m of it. Bisecting the 323 b4 polygons of the run found one, `b4_236` (12,485 m²), that touches neither the route nor its endpoints, yet makes the pair unroutable for the motorbike, the car, and the truck when sent alone as a priority 0 area. For the foot walker the same polygon moved the snapped endpoint about 100 m and the route grew to 1,422 m.

The cause fits the way GraphHopper applies an area. It blocks a whole edge when any part of the edge meets the polygon. A GraphHopper edge can be much longer than one road piece, so an edge that holds a shallow piece can also run into a deeper zone. The 22 m buffer of `DEFAULT_BUFFER_M` widens the effect. This is inferred from the behavior, and the edge geometry was not read. The check now avoids such pairs by its neighbourhood rule, and this page records the effect as a property of the design. FYI for `US-040` and `US-043`, which store and read one depth per GraphHopper edge id.

## Log volume

GraphHopper writes the whole custom model of each flood-graded `/route` request on one log line. The longest line seen on 2026-10-02 was 454,252 characters. The container's `json-file` log has no size limit (`LogConfig.Config` is empty). The raw log of `airflow_new-graphhopper-1` reached at least 271 MB in 1,558 lines between 00:45 and about 03:10 +07 on 2026-10-02, nearly all of it from test traffic. The fetch of the raw log stopped at that point, because it did not finish within 280 s. A page load sends 13 route requests ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 4), so real use can write several megabytes per load. Whether this threatens the disk of the server was not checked. `run_soak.sh` filters the log on the host with `gh_log_filter.ps1` to avoid copying it. Setting the `RouteResource` logger to `WARN` in `config.yml` would remove these lines, and it needs a GraphHopper restart.

## The time-aware module (US-049, skeleton)

`java/time-aware-routing/` is a Maven module built against GraphHopper commit `d7dc1b06` (`12.0-SNAPSHOT`), the commit the stock image's jar came from. The skeleton changes no weighting. The later sections add the search and the backend integration.

- `TimeAwareGraphHopper` extends `GraphHopper` and returns a `TimeAwareWeightingFactory`, which today returns the stock weighting.
- `com.graphhopper.http.GraphHopperManaged` is a shadow copy of the stock class. `GraphHopperBundle` calls `new GraphHopperManaged(...)`, and the web server has no setting to pick another class. The image puts the module's jar before `graphhopper-web.jar`, so the JVM loads the copy. The log line `TimeAwareGraphHopper active` proves which class loaded. The copy drops the GTFS branch.
- The stock `graphhopper.sh` runs `java -jar`, which ignores the classpath. The image's entrypoint is `run-time-aware.sh`, which takes the same `-c` and `-o` options and starts `GraphHopperApplication` from a classpath.
- `ExportEdges` writes `edges.csv` and `graph.json` (the graph hash) from the graph cache, opened read-only. At this GraphHopper commit `BaseGraph` opens the `geometry` file for writing when the default `DAType` is a storing one, `DAType.MMAP_RO` included, so the export uses its own non-storing read-only type. Run on the server graph on 2026-10-05: 67,833 edges. Since format version 2 (2026-10-09) `edges.csv` also has `base_node` and `adj_node`, with 51,328 nodes. `export-edges.sh` accepts `SKIP_BUILD=1` and `IMAGE=<name>` to use an image already on the server. `java/time-aware-routing/export-edges.sh` repeats it.
- A weighting that only raises weights keeps the LM lower bounds valid ([[BL-011-routing-not-time-aware|routing-not-time-aware]], 2026-10-05).
- 12.0-SNAPSHOT is not on Maven Central. CI and the `Dockerfile` both build the pinned commit first. CI is `.github/workflows/java-module.yml`.

Checked on 2026-10-05 on the Mac side with the stock jar and the module jar, on a small OSM extract with the repo's four profiles: 20 routes, the same distance and time from both. On the server (2026-10-05) the image started beside the live service with the `TimeAwareGraphHopper active` log line, and 12 routes (4 profiles, 3 pairs inside the model border) matched the live service. `java/time-aware-routing/smoke-test.sh` repeats the check. Since `US-052`, `compose.yml` builds the `graphhopper` service from this image.

## The time-aware search (US-050)

`TimeAwareGraphHopper.doCreateRouter` returns a `TimeAwareRouter`. Read from the pinned source (commit `d7dc1b06`): `Weighting.calcEdgeWeight` has no time argument, so a weighting alone cannot know the arrival time, and the search has to carry it. `Router.createSolver` and `createFlexSolver` are protected, so a subclass can run its own `RoutingAlgorithmFactory` without changing the shadowed `GraphHopperManaged`.

- A request with the hint `td_departure` (epoch seconds), on a profile with the hint `td_limit_cm` (the vehicle's limit in cm), is routed by `TimeAwareDijkstra` through a flexible solver. Landmarks and contraction hierarchies are skipped, because their bounds and shortcuts do not know the time. Every other request goes the stock way.
- The depth table comes from the `TableProvider` that `TimeAwareGraphHopper.setTableProvider` sets. `importOrLoad` sets it to a `LatestTableSource` when `time_aware.table_dir` is configured (`US-052`). With no table the request is routed as before.
- A label holds the weight and the time spent. A node can hold several labels, and a label is dropped only when another one at that node is no heavier and no later. A test fails without that rule (a light but slow way hides a heavier way that arrives before the road closes).
- A snap in the middle of a road gives virtual edges with ids past the graph's. `VirtualEdgeIterator` is not a `VirtualEdgeIteratorState`, so the search detaches the edge to read `getOriginalEdgeKey()`. A test fails without that mapping.
- In the tests, `SpeedWeighting` takes millis as distance over speed times 1000 and weighs a minute as 600, so test roads get their length from that.

Checks on 2026-10-05 in the cloud session: 98 module tests, and the 16 runs of `ScenarioReport` (4 scenarios, motorbike and car, with and without a detour) all match the sticky column of [[BL-011-routing-not-time-aware|routing-not-time-aware]] with no crossing. The plain shortest route crosses the closed road in the 8 blocked runs. On the server (2026-10-05) `java/time-aware-routing/scenario-check.sh` gave the same 16 of 16. On the server on 2026-10-07 (`US-055`, from `artifacts/TODOS.md`), `latency` stayed within 2 times the `US-046` baseline in all 6 cells, `compare` on 24 real pairs changed 37.5% of routes with a median detour ratio of 0.94, `crossings` found 0, and `scenario-check.sh` matched 32 of 32. `US-055` and `US-045` are `Done`.

## The engine in the backend (US-052)

Plan: [[time-aware-backend-integration]]. The flag is `TIME_AWARE_ROUTING` on `floodmap-backend` (default `false`). The engine was deployed and tested on the server on 2026-10-07 (`US-055`). `scripts/routing_proof/rollout.ps1` turns the flag on for the proof and puts it back off unless run with `-LeaveOn`. At rest on 2026-10-08 the backend reads `TIME_AWARE_ROUTING=false`, so ordinary live routing is still single-timestep. Whether `-LeaveOn` was used on 2026-10-07 is unconfirmed.
On 2026-10-10 the three live readings of `US-091` turned `TIME_AWARE_ROUTING` on for `floodmap-backend` for one reading each, and the script turned it off again after each reading. `US-045` (live timing of task 9c) is still open.

- **Flag off:** `POST /route` is today's request. The client's `td_*` fields are removed either way.
- **Flag on:** the backend sends `td_departure`, the later of `valid_time` and the server clock, and no flood `custom_model`. GraphHopper answers with `td.status` (`applied`, `unknown`, or `fallback`), `td.run`, `td.departure`, `td.last_step`, and `td.reason` for a fallback. On `fallback`, or on an answer with no `td.status` (a GraphHopper without the module), the backend sends today's request with the flood custom_model and keeps `td.status: fallback` and the reason in the response. An error passes through, so a route closed by the table gives "Connection between locations not found".
- **In the engine:** `TimeAwareRouter` decides once per request, so one table serves every leg. The departure is floored to the forecast step that contains it, because the step that describes the roads now must count in the closure rule. A trip is `unknown` when it ends after the last step. A profile with no `td_limit_cm` is a fallback.
- **Table folder:** `time_aware.table_dir` in `config.yml` (the volume `edge-depth-tables`, read-only at `/tables`). `TimeAwareGraphHopper` hashes the loaded graph after the import and follows `latest`. A table for another graph is refused, and the response names both hashes.
- **Compose:** the `graphhopper` service builds from `java/time-aware-routing` (`graphhopper-time-aware:local`) and starts through `run-time-aware.sh`. Roll back by restoring the stock image line (kept as a comment) and setting the flag to `false`.
- **All four vehicles (US-051):** `td_limit_cm` is 20 for `motorbike`, 30 for `car`, 35 for `truck`, and 40 for `foot` in `config.yml`. A test in Java and one in Python keep them equal to `threshold_cm` in `flood_utils.py` and to the limits of `ScenarioReport`. The report runs 32 cases for the four vehicles.
- **On the server:** the image was built and deployed on 2026-10-07 (host `ADMIN`, `rollout.ps1`), after a graph re-import for the `US-051` profile change. The flag stayed `false` at the end of that run (log of 2026-10-07). The hash of the live graph equal to the table's was not checked on its own. The `departures` check returned answers for 3 of 3 trips, and a table for another graph gives `status: unavailable`, so the hashes matched at that time.

## The departures endpoint (US-053)

Plan: [[route-departures-endpoint]]. `POST /route/departures` takes `points` and `profile` and returns when the usual route first clears. The client sends no clock, margin, or limit, and the server drops them.

- **The usual route** is requested with no flood model and no time-aware search, with the `edge_id` and `time` details and the hint `td_info`. The two details must line up one to one. If they do not, the endpoint answers with an error and does not guess.
- **The table** is read by the backend's own reader (`edge_depth_reader.py`) from `EDGE_TABLE_DIR` (`/tables`, the volume `edge-depth-tables`, read-only). The table's graph hash must equal `td.graph_hash` from GraphHopper. A table that is missing, damaged, or for another graph gives `status: unavailable` and a `reason`, with HTTP 200, so the client can show "timing check unavailable".
- **The rule** is the closure rule of `US-050`, with the margin of 600 s and the limit of the profile from `flood_utils.py`. A candidate is `blocked`, `unknown` (the trip ends after the last step), or `clear`. Candidates run from the step that contains now to the last step. The answer holds `run`, `run_age_s` (now minus the first step of the table), `candidates` (each with `departure`, `leave_at`, `arrival`, `status`), and `earliest_clear`.
- **On the server:** `departures` answered 3 of 3 real trips on 2026-10-07 (`artifacts/TODOS.md`, `US-055`).

## Open items

- `floodmap/graphhopper-maps/config-local.js.example` lists all four profiles: `motorbike`, `car`,
  `truck`, and `foot`. `foot` was confirmed selectable in the live UI on 2026-09-23 and `truck` on
  2026-09-29, after `flood-routing-frontend` was rebuilt and redeployed.
- Routing through the UI was failing with a safety-framed "No safe route available" error on every
  request, for every vehicle profile, whenever a `valid_time` was attached. That is always the case,
  since `TimeSlider` supplies one on mount. Root cause was a missing `geom_4326` column on
  `flood_road_values`; fixed 2026-09-23 by running the migration that was supposed to add and
  backfill it. See [[BL-004-flood-route-missing-geom-column|flood-route-missing-geom-column]] for the full investigation. The GeoJSON
  ingestion chain that also wrote that column left `flood_mapping_full` on 2026-09-24, and
  `flood_on_roads` in `routing_adapter` now writes `flood_road_values`.
- Backend hardening: `server.py` and `flood_areas.py` postdate a single commit (`6394e27`, the
  Valhalla-to-GraphHopper rewrite). `backend/test_flood_areas.py` and `backend/test_server.py`
  (added 2026-09-23) now cover `derive_areas()`, `build_custom_model()`, and the full HTTP surface
  with a real PostGIS and a stub GraphHopper. The soak of `US-034`
  ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 3) closed on 2026-10-05 on the 137 runs of the replay that ran
  (2026-10-02 to 2026-10-04), not on 48 hours. The user waived the evidence screenshot, and the end
  check of `run_soak.sh` over the window was not run (`sprint-plan-2`).
  "Soak and known-answer check" below describes the tooling. The comparison with the old Valhalla
  backend was dropped on 2026-10-01, because the Valhalla model was wrong when it ran.
- GraphHopper's log has no size limit and each flood-graded `/route` request writes one line of up to
  about 450 KB. See "Log volume".
- `GET /flood/points` has no measured latency on the server since it moved to tiles, and none
  under concurrent popup taps. Story 4 of [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] covers that check.
  `backend/test_server.py` checks its depth against `gdallocationinfo` on a synthetic `depth.tif`.
  The real `depth_20260924_170639.tif` matched `gdallocationinfo` at three points on a local
  PostGIS, not on the server.
- Most of a local `GET /flood/points` request (about 56 ms of 58 ms) is the PostGIS raster library
  load in the new backend that `server.py` connects for each request. Reusing connections, for
  example with `psycopg2.pool`, would remove that cost. No change is planned yet.
- `raster_load.load_raster` and `publish.py` insert a timezone-aware UTC `datetime` into
  `TIMESTAMP` columns. PostgreSQL converts it with the session `TimeZone`, so the stored value is
  UTC only when `storage-postgres` runs in UTC. `list_timesteps` and `GET /flood/points` both read
  the column as UTC.
