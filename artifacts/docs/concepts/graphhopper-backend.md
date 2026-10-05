---
date: 2026-09-22
type: concept
status: active
tags: [graphhopper, routing]
related: ["[[T3-Digital-Twin_Architecture]]", "[[2026-09-14]]", "[[graphhopper-vehicle-profile-rejection]]", "[[flood-route-missing-geom-column]]", "[[point-depth-lookup-backend]]", "[[raster-first-flood-pipeline]]", "[[minio-flood-extent-pipeline]]", "[[flood-on-roads]]", "[[decision-log]]"]
last_updated: 2026-10-05
---

# GraphHopper flood-road backend

`floodmap/graphhopper-flood-road/backend/server.py` sits between the frontend and a pinned
GraphHopper instance. It answers flood queries GraphHopper cannot answer on its own, and proxies
the rest of GraphHopper's API unchanged.

## Why a separate backend exists

GraphHopper computes a route from a `custom_model`, a JSON document that grades each road segment's
cost. The frontend cannot build that document itself: the flood polygons for a given timestep and
vehicle type live in PostGIS, not in the browser, and can run to around 1,000 vertices. `server.py`
derives the `custom_model` server-side, from PostGIS, and forwards the graded request to GraphHopper.
Both `GET /flood/areas` (the map overlay) and `POST /route` (routing) call the same derivation
function, `flood_areas.derive_areas`, so the overlay a user sees and the areas GraphHopper actually
routes around can never drift apart.

## Three flood tables, one intentional split

The backend reads from three separate PostGIS tables, and they are not interchangeable:

- `flood_road_values`, keyed by `(timestamp, forecast_time)`. `flood_areas.py` reads this table to
  build the `custom_model` for routing. Its own ingestion pipeline is separate from the tile
  pipeline below.
- `flood_extent_polygon`, keyed by `(run_ts, valid_time)`. `flood_extent_runs.py` reads this table
  to back `GET /flood/runs` and `GET /flood/timesteps`, the map's timestep picker. See
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
fields the vendored frontend fork adds: `valid_time`, `run`, `vehicle_type`. `_handle_route` in
`server.py` does four things:

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
| `/flood/areas` | GET | The same flood polygons `POST /route` grades against, for the map overlay. |
| `/flood/points` | GET | Exact depth at one lat/lon and timestep, from `flood_depth_raster_tile`. |
| `/route` | POST | Flood-graded route; see the flow above. |
| `/places/search`, `/geocode` | GET | Place search, backed by `place_search.py`. |
| `/places/reverse` | GET | The nearest named Vietnamese place to `lat` and `lon` (Photon `/reverse`), as `{"result": {name, address, ...} or null}`. Backs the place-depth popup. |

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

## The pinned image, and why the `foot` profile was blocked

`compose.yml` pins the `graphhopper` service to
`israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`,
a 12.0-SNAPSHOT build, by digest rather than `:latest`. The `ch.disable`-in-body behavior the
routing flow above depends on is undocumented in that build and could change without notice, so the
pin is deliberate: re-pull only after re-running the `ch.disable` smoke test.

Adding any new vehicle profile used to fail at startup with `Cannot compile expression:
'<name>_access' not available`, thrown from GraphHopper's own `checkProfilesConsistency()`. This
was not a broken build. This pinned image's `graphhopper.sh` entrypoint defaults its graph output
directory to `/data/default-gh` and always passes it as a `-Ddw.graphhopper.graph.location` JVM
system property, which overrides `config.yml`'s `graph.location: /data/graph-cache` setting
(Dropwizard system-property overrides win over the YAML file). `compose.yml`'s entrypoint never
passed the `-o` flag that changes that default, so the app always loaded a graph baked into the
image at `/data/default-gh`, imported once with only `car_access`, `hgv`, and the other three
built-in profiles' encoded values, before this repository's history starts. `/data/graph-cache`,
the actual mounted volume, was never used at all, which is why every earlier attempt saw no import
progress and an empty cache directory. Fixed by adding `-o /data/graph-cache` to the `graphhopper`
service's `entrypoint` in `compose.yml`, which makes the app import the mounted OSM extract into
the real, persistent volume using whatever `graph.encoded_values` `config.yml` declares.
`graphhopper/config.yml` now registers a fourth profile, `foot`, backed by `foot_custom.json`
(`foot_priority` stays trimmed out; see that file's own comment for why). See
[[graphhopper-vehicle-profile-rejection]] for the full investigation. `truck` was a separate
config gap: GraphHopper already served it, but `config-local.js.example`'s `profiles` object did
not list it. It does since 2026-09-29 (see [[truck-routing-profile]]).

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
[[flood-routing-vehicle-type-always-motorbike]] (resolved).

## Soak and known-answer check

`scripts/backend_soak/run_soak.sh` gives the verdict of the soak (`US-034`). It reads the state of the three containers, scans their logs since the soak start, and runs `soak_checks.py roads` inside `airflow_new-floodmap-backend-1`. It exits with 0 only if every Docker call answered, no container started inside the window or was OOM killed, no log holds a 5xx response or an error line, and no check failed. A log with no timestamped line fails, because a failed read leaves only error text (`US-064`). `soak_checks.py` also has a `latency` command, which `US-046` used for the baselines in [[routing-not-time-aware]], and tests in `scripts/backend_soak/` (42).

The `roads` check reads one run of `flood_road_values` and picks road pieces in five depth buckets: below every limit, between the motorbike and car limits, between the car and truck limits, between the truck and foot limits, and past every limit. The pick is deterministic (`md5` of the segment id). A piece is a candidate only if its two neighbours on the same way exist and are no deeper than the next limit, and no piece that would block an allowed vehicle lies within about 170 m. For each piece, each profile, and both directions, the check routes from the neighbour before the piece to the neighbour after it. It sends the request once with the flood fields and once without, the dry control. `expected_outcome` takes the promise from the bands of `DEPTH_BANDS`.

| Depth against the vehicle's limit | Band | Promise | Pass when |
| --- | --- | --- | --- |
| At or above the limit | b4, priority 0 | Blocked | No route crosses the piece. |
| From 0.5 times the limit up to the limit | b2 and b3, priority 0.2 and 0.05 | Costly | A route exists. |
| Below 0.5 times the limit | none | Open | A route crosses the piece. |

The check skips a pair when the dry control cannot show the promise. For a blocked or open promise the dry route must cross the piece. For a costly promise the dry route must exist. In those pairs the network (a one-way piece, a dual carriageway, a road closed to foot) and not the flood decides the result.

Run on the 2026-10-02 03:00 run, the check covered 23 roads and 92 pairs of road and profile. It passed 86, skipped 6, and failed none. All 40 blocked promises held.

### What a stricter first version found

A first version with a smaller neighbourhood (about 60 m) failed 3 of 120 pairs. The truck and the foot walker found no route across two roads whose depth (32.5 cm and 33.4 cm) lies below their limits (35 cm and 40 cm). One of them was the overpass `Cầu vượt Phú Đô` (`way/596300521#1`). The dry control found a 137 m route, and no piece of 35 cm or more lies within 136 m of it. Bisecting the 323 b4 polygons of the run found one, `b4_236` (12,485 m²), that touches neither the route nor its endpoints, yet makes the pair unroutable for the motorbike, the car, and the truck when sent alone as a priority 0 area. For the foot walker the same polygon moved the snapped endpoint about 100 m and the route grew to 1,422 m.

The cause fits the way GraphHopper applies an area. It blocks a whole edge when any part of the edge meets the polygon. A GraphHopper edge can be much longer than one road piece, so an edge that holds a shallow piece can also run into a deeper zone. The 22 m buffer of `DEFAULT_BUFFER_M` widens the effect. This is inferred from the behavior, and the edge geometry was not read. The check now avoids such pairs by its neighbourhood rule, and this page records the effect as a property of the design. FYI for `US-040` and `US-043`, which store and read one depth per GraphHopper edge id.

## Log volume

GraphHopper writes the whole custom model of each flood-graded `/route` request on one log line. The longest line seen on 2026-10-02 was 454,252 characters. The container's `json-file` log has no size limit (`LogConfig.Config` is empty). The raw log of `airflow_new-graphhopper-1` reached at least 271 MB in 1,558 lines between 00:45 and about 03:10 +07 on 2026-10-02, nearly all of it from test traffic. The fetch of the raw log stopped at that point, because it did not finish within 280 s. A page load sends 13 route requests ([[carried-over-backlog]] Story 4), so real use can write several megabytes per load. Whether this threatens the disk of the server was not checked. `run_soak.sh` filters the log on the host with `gh_log_filter.ps1` to avoid copying it. Setting the `RouteResource` logger to `WARN` in `config.yml` would remove these lines, and it needs a GraphHopper restart.

## The time-aware module (US-049, skeleton)

`java/time-aware-routing/` is a Maven module built against GraphHopper commit `d7dc1b06` (`12.0-SNAPSHOT`), the commit the stock image's jar came from. It changes no behavior yet.

- `TimeAwareGraphHopper` extends `GraphHopper` and returns a `TimeAwareWeightingFactory`, which today returns the stock weighting.
- `com.graphhopper.http.GraphHopperManaged` is a shadow copy of the stock class. `GraphHopperBundle` calls `new GraphHopperManaged(...)`, and the web server has no setting to pick another class. The image puts the module's jar before `graphhopper-web.jar`, so the JVM loads the copy. The log line `TimeAwareGraphHopper active` proves which class loaded. The copy drops the GTFS branch.
- The stock `graphhopper.sh` runs `java -jar`, which ignores the classpath. The image's entrypoint is `run-time-aware.sh`, which takes the same `-c` and `-o` options and starts `GraphHopperApplication` from a classpath.
- `ExportEdges` writes `edges.csv` and `graph.json` (the graph hash) from the graph cache, opened read-only. At this GraphHopper commit `BaseGraph` opens the `geometry` file for writing when the default `DAType` is a storing one, `DAType.MMAP_RO` included, so the export uses its own non-storing read-only type. Run on the server graph on 2026-10-05: 67,833 edges. `java/time-aware-routing/export-edges.sh` repeats it.
- A weighting that only raises weights keeps the LM lower bounds valid ([[routing-not-time-aware]], 2026-10-05).
- 12.0-SNAPSHOT is not on Maven Central. CI and the `Dockerfile` both build the pinned commit first. CI is `.github/workflows/java-module.yml`.

Checked on 2026-10-05 on the Mac side with the stock jar and the module jar, on a small OSM extract with the repo's four profiles: 20 routes, the same distance and time from both. On the server (2026-10-05) the image started beside the live service with the `TimeAwareGraphHopper active` log line, and 12 routes (4 profiles, 3 pairs inside the model border) matched the live service. `java/time-aware-routing/smoke-test.sh` repeats the check. The image and its test container stay a separate service until a later story switches `compose.yml` to it.

## Open items

- `floodmap/graphhopper-maps/config-local.js.example` lists all four profiles: `motorbike`, `car`,
  `truck`, and `foot`. `foot` was confirmed selectable in the live UI on 2026-09-23 and `truck` on
  2026-09-29, after `flood-routing-frontend` was rebuilt and redeployed.
- Routing through the UI was failing with a safety-framed "No safe route available" error on every
  request, for every vehicle profile, whenever a `valid_time` was attached — which is always,
  since `TimeSlider` supplies one on mount. Root cause was a missing `geom_4326` column on
  `flood_road_values`; fixed 2026-09-23 by running the migration that was supposed to add and
  backfill it. See [[flood-route-missing-geom-column]] for the full investigation. Worth checking
  Airflow's ingestion DAG history for the same period, since its `INSERT`s reference that column
  too and may have been failing silently.
- Backend hardening: `server.py` and `flood_areas.py` postdate a single commit (`6394e27`, the
  Valhalla-to-GraphHopper rewrite). `backend/test_flood_areas.py` and `backend/test_server.py`
  (added 2026-09-23) now cover `derive_areas()`, `build_custom_model()`, and the full HTTP surface
  with a real PostGIS and a stub GraphHopper. The 48-hour soak of `US-034`
  ([[carried-over-backlog]] Story 3, Sprint 5) runs from 2026-10-02 00:45 +07 to 2026-10-04 00:45 +07.
  "Soak and known-answer check" below describes the tooling. The comparison with the old Valhalla
  backend was dropped on 2026-10-01, because the Valhalla model was wrong when it ran.
- GraphHopper's log has no size limit and each flood-graded `/route` request writes one line of up to
  about 450 KB. See "Log volume".
- `GET /flood/points` has no measured latency on the server since it moved to tiles, and none
  under concurrent popup taps. Story 4 of [[point-depth-lookup-backend]] covers that check.
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
