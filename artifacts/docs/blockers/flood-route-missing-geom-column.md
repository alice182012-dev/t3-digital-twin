---
date_open: 2026-09-23
date_closed:
type: blocker
status: open
severity: P1
subsystem: flood-routing-backend
approaches_tried: 0
approaches_remaining: 1
tags: [blocker, postgis, routing]
related: ["[[graphhopper-vehicle-profile-rejection]]", "[[graphhopper-backend]]", "[[2026-09-23]]"]
last_updated: 2026-09-23
---

# Every route in the UI shows "No safe route available", flood or no flood

## Description

`floodmap-backend`'s `POST /route` returns the app's safety-framed empty-route message for every
route request made through the UI, regardless of vehicle profile (`motorbike`, `car`, `truck`, and
now `foot`) and regardless of whether the "Flood" tile layer is toggled on or off. Calling the
backend directly with the same two points and no `valid_time` in the body returns a real route
(200, one path); adding a `valid_time` (which `TimeSlider.tsx` always supplies on mount, so every
real UI request carries one) makes the backend return a hard error:

```
{'error': 'column v.geom_4326 does not exist\nLINE 3:     SELECT ST_Transform(v.geom_4326, 3405) AS g, v.depth\n                                ^\n'}
```

The frontend presents that 400 as "No safe route available. Please consider getting to the safest
location or stay where you are." (the app's intentional safety-framed empty state, per
[[graphhopper-backend]]'s history), which reads identically to a genuine "the flood actually
blocks every path" result. It isn't one: the query never runs to completion.

## Why this matters

Routing is the product's core feature. This makes every route request fail in the deployed UI,
for every vehicle, all the time, not only during an active flood. It was found while verifying the
`foot`-profile fix in [[graphhopper-vehicle-profile-rejection]], but is not caused by or related to
that fix: reproduces identically for `car` and `motorbike`, which have worked, or appeared to work,
since before this session.

## Approaches tried

None yet; root cause found directly by reading `flood_areas.py`'s SQL against the live schema, no
trial fixes attempted.

## Root cause

`flood_areas.py`'s `_WINNER_SEG_SQL` and `_PINNED_RUN_SEG_SQL` both read `v.geom_4326`, a PostGIS
`geometry(Geometry,4326)` column that's supposed to hold every flood segment's location, derived
from the raw `geom` column (`jsonb`, storing each segment as a GeoJSON `LineString`, e.g.
`{"type": "LineString", "coordinates": [[105.76026, 21.02149], ...]}`).

That derived column doesn't exist on the live `flood_road_values` table:

```
$ SELECT column_name FROM information_schema.columns WHERE table_name = 'flood_road_values';
 id | file_id | timestamp | road_name | forecast_time | depth | geom | created_at
```

`scripts/database/create_geojson_tables.py` is the script that's supposed to add it
(`ALTER TABLE flood_road_values ADD COLUMN IF NOT EXISTS geom_4326 geometry(Geometry,4326)`) and
backfill it for existing rows (`UPDATE ... SET geom_4326 = ST_SetSRID(ST_GeomFromGeoJSON(geom::text), 4326)
WHERE geom_4326 IS NULL`). It was never run against this deployment's database. The live ingestion
pipeline, `scripts/database/geojson_to_pg.py`, already writes `geom_4326` correctly on every new
row it inserts (`ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)` in its `INSERT`), so this isn't a code
bug in the write path either — it's a migration that was written but never applied, on a table that
now holds 1,303,752 rows (406 MB), all with a non-null `geom` and therefore all backfillable.

## Decision and explanation

Pending. One untried direction: run `scripts/database/create_geojson_tables.py` against the live
database. It's additive only (`ADD COLUMN IF NOT EXISTS`, `UPDATE ... WHERE geom_4326 IS NULL`),
touches no other column or table, and at 406 MB / 1.3M rows should complete in well under a minute.

## Concerns

If the Airflow ingestion DAG that calls `geojson_to_pg.py` has been running against this same
database all along, every one of its `INSERT`s referencing `geom_4326` should have failed outright
with the same "column does not exist" error — worth checking DAG run history once this is fixed,
in case ingestion itself has been silently broken rather than merely the read path.

## Related topics

- [[graphhopper-vehicle-profile-rejection]]. Unrelated root cause and subsystem; only connected
  because this was found while verifying that blocker's fix in the live UI.
- [[graphhopper-backend]]. Documents the `POST /route` flow this bug breaks.

## Status history

- **2026-09-23, open.** Root cause found directly (missing `geom_4326` column, migration never
  run), no attempts made yet.
