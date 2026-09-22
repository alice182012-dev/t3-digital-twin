---
date: 2026-09-22
type: concept
status: active
tags: [graphhopper, routing, flood-depth]
related: ["[[graphhopper-backend]]", "[[SW Architecture]]"]
last_updated: 2026-09-22
---

# Routing depth-threshold model

This is how a flood depth in `flood_road_values` becomes a GraphHopper routing cost. It is the
model [[graphhopper-backend]]'s `flood_areas.derive_areas` and `build_custom_model` run at request
time.

## Vehicle thresholds

`floodmap/graphhopper-flood-road/scripts/flood_utils.py`'s `VEHICLE_PROFILES` sets, per vehicle,
the depth at which a segment becomes impassable:

| Vehicle | Threshold |
|---|---|
| motorbike | 20 cm |
| car | 30 cm |
| truck | 35 cm |
| foot | 40 cm |

`foot` has no GraphHopper profile wired up yet; see [[graphhopper-backend]]'s section on the pinned
image blocker. Its threshold is otherwise complete and unused.

## Bands are relative to the vehicle, not absolute

`DEPTH_BANDS` expresses each band as a fraction of the vehicle's own threshold, not an absolute
depth:

| Band | Fraction of threshold | Cost multiplier |
|---|---|---|
| b2 | 50% to 75% | ×0.2 |
| b3 | 75% to 100% | ×0.05 |
| b4 | 100% and above | ×0.0 (impassable) |

A depth below 50% of the threshold gets no band at all, so no extra cost. `depth_bands_m()`
converts these fractions to absolute meters for one vehicle by multiplying against
`vehicle_threshold_cm(vehicle_type) / 100.0`. This is a separate scale from
`graphhopper-maps/src/floodmap/depthScale.ts`'s `DISPLAY_DEPTH_BANDS`, which are absolute depths
for the map legend a human reads; the two are meant to drift independently; a display band change
does not imply a routing band change and vice versa.

## From PostGIS rows to a custom_model

`flood_areas.derive_areas(conn, valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)`
runs one SQL query per band (deepest first: b4, then b3, then b2), each pulling
`flood_road_values` rows in that band's depth range for the given `(forecast_time, timestamp)`
pair, then buffers, unions, and simplifies them (`ST_Buffer`, `ST_Union`, `ST_SimplifyPreserveTopology`)
into polygons, dropping anything under `min_area_m2` (default 400 m²). Two SQL templates exist:
`_WINNER_SEG_SQL` picks the latest `timestamp` for the requested `forecast_time` when `run` is
`"latest"`; `_PINNED_RUN_SEG_SQL` pins to an exact `(timestamp, forecast_time)` pair when a specific
`run` is requested. `buffer_m` (default 22 m) and `simplify_m` (default 3 m) match the values a
prior D2 parameter sweep validated.

Each returned GeoJSON feature carries `band` and `multiply_by` in its properties, so
`build_custom_model()` can turn the feature collection straight into GraphHopper's
`custom_model.priority` list without re-deriving anything. It emits one `if`/`else_if` clause per
feature, ordered deepest-band-first: an edge inside two overlapping buffers from different bands
only ever takes the first (deepest) match, so overlapping penalties never multiply together. This
ordering is required, not incidental: independent `if` rules would double-penalize any edge in an
overlap.

`GET /flood/areas` and `POST /route` both call `derive_areas` for the same inputs, cached for 30
seconds (`FLOOD_AREAS_CACHE_TTL_SECONDS`) keyed on
`(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)`, so the map overlay a citizen
sees and the areas GraphHopper actually routes around are always the same derivation, never two
independent calculations that could disagree.

## A second, unused threshold function

`flood_utils.py` also defines `factor_from_depth_m(depth_m, vehicle_type)`, a five-tier step
function (factors 1, 2, 8, 25, 60, 100) at 15%, 25%, 50%, 75%, and 100% of the vehicle's threshold.
Its docstring says it is kept for parity with Phase 1 and D2 scripts and tests; `flood_areas.py`
uses `DEPTH_BANDS` and `depth_bands_m()` instead, not this function, for the routing cost that
actually ships.

## Design rationale not yet in code

`artifacts/raw/SW Architecture.md`, section 9, describes a pre-closure threshold: proactively closing a
segment when its depth forecast 1 hour ahead reaches the vehicle's hard block threshold, even if
the current depth is still passable, as a safety buffer distinct from the hard block itself. That
document is FloodNav's broader target architecture, not a record of what is currently implemented;
no pre-closure or forecast-ahead logic was found in `flood_areas.py` or `flood_utils.py` as read on
2026-09-22. The three `DEPTH_BANDS` above, all keyed to the current depth at `valid_time`, are what
actually ships today.

## Open items

- Confirm whether pre-closure (the T+1h forecast rule above) is planned as a `flood_areas.py`
  change or expected to live elsewhere before treating it as scoped work.
- `factor_from_depth_m` and `DEPTH_BANDS` express similar ideas on different scales (5 tiers vs. 3
  bands, different fractions). Confirm whether the unused function should be deleted now that
  `DEPTH_BANDS` is the shipped model, or is still needed by the Phase 1/D2 tests its docstring
  mentions.
