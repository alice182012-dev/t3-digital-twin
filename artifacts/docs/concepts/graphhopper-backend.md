---
date: 2026-09-22
type: concept
status: active
tags: [graphhopper, routing]
related: ["[[SW Architecture]]", "[[2026-09-14]]", "[[routing-foot-truck-profiles]]", "[[graphhopper-vehicle-profile-rejection]]"]
last_updated: 2026-09-22
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

## Two flood tables, one intentional split

The backend reads from two separate PostGIS tables, and they are not interchangeable:

- `flood_road_values`, keyed by `(timestamp, forecast_time)`. `flood_areas.py` reads this table to
  build the `custom_model` for routing. Its own ingestion pipeline is separate from the tile
  pipeline below.
- `flood_extent_polygon`, keyed by `(run_ts, valid_time)`. `flood_extent_runs.py` reads this table
  to back `GET /flood/runs` and `GET /flood/timesteps`, the map's timestep picker. See
  [[minio-flood-extent-pipeline]] for how this table gets populated.

Routing and map display run on different cadences and different upstream pipelines on purpose. Do
not point the routing derivation at `flood_extent_polygon`, and do not point the timestep picker at
`flood_road_values`. `artifacts/raw/SW Architecture.md`, section 8, records the decision.

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
   so `graphhopper-maps`' `Api.ts` needs no changes to parse it.

## Endpoints

| Path | Method | Purpose |
|---|---|---|
| `/health` | GET | Backend, GraphHopper, and PostGIS health in one payload. |
| `/info`, `/nearest` | GET | Proxied to GraphHopper unchanged; no flood logic. |
| `/flood/runs` | GET | Distinct `run_ts` values from `flood_extent_polygon`. |
| `/flood/timesteps` | GET | Timesteps for one run, converted back to Vietnam local time. |
| `/flood/areas` | GET | The same flood polygons `POST /route` grades against, for the map overlay. |
| `/route` | POST | Flood-graded route; see the flow above. |
| `/places/search`, `/geocode` | GET | Place search, backed by `place_search.py`. |

## The pinned image and the routing profile blocker

`compose.yml` pins the `graphhopper` service to
`israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`,
a 12.0-SNAPSHOT build, by digest rather than `:latest`. The `ch.disable`-in-body behavior the
routing flow above depends on is undocumented in that build and could change without notice, so the
pin is deliberate: re-pull only after re-running the `ch.disable` smoke test.

That same build rejects any newly declared vehicle encoded value at startup:
`Cannot compile expression: '<name>_access' not available`, thrown from GraphHopper's own
`checkProfilesConsistency()` before any OSM import runs. This was reproduced identically for
`foot_access` (needed for a walking profile) and, as an isolation test, for a synthetic
`bike_access` profile with no dependency on `foot` at all. The failure is specific to this pinned
build, not to pedestrian routing. `graphhopper/config.yml` currently registers only three profiles
(`motorbike`, `car`, `truck`) for this reason. `foot_custom.json` and
`foot_avoid_private_node_custom.json` already exist in that directory, trimmed from GraphHopper's
own bundled `foot.json`, ready for whoever resolves the build issue. See TODOS.md's "Pinned
GraphHopper build rejects any new vehicle profile" item for the four approaches already tried, and
[[routing-foot-truck-profiles]] for why `truck` is also missing from the frontend despite already
working server-side (a config gap, not this same bug).

## Vehicle thresholds

`floodmap/graphhopper-flood-road/scripts/flood_utils.py`'s `VEHICLE_PROFILES` sets the depth a
segment becomes impassable for each vehicle: motorbike 20 cm, car 30 cm, truck 35 cm, foot 40 cm.
`foot`'s entry is already correct and unused, since no GraphHopper profile exists to apply it to
yet.

## Open items

- The routing profile blocker above (P2 in TODOS.md; live status in [[graphhopper-vehicle-profile-rejection]]).
- Backend hardening: `server.py` and `flood_areas.py` postdate a single commit (`6394e27`, the
  Valhalla-to-GraphHopper rewrite), with no regression tests and no soak time yet (P2 in
  TODOS.md).
