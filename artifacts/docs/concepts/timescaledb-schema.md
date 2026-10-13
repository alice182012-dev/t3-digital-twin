---
date: 2026-09-23
type: concept
status: parked
tags: [timescaledb, schema, histogram, sprint-1]
related: ["[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[T3-Digital-Twin_Architecture]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
last_updated: 2026-10-13
---

# TimescaleDB schema for histograms, forecast series, and depth history

TimescaleDB holds three kinds of data that `storage-postgres` doesn't: institution histograms,
the `background_cycle` forecast series, and depth history. The architecture doc lists these three
in its data-store table (section 5) and specifies the histogram split in section 4.9.
`scripts/database/create_timescale_tables.py` creates the schema. No DAG runs that script yet.

The pipeline does not run a `background_cycle` (D-009 in [[decision-log]], 2026-10-01). The `background_cycle`
enum value, the `background_forecast_depth` table, and bars 7 to 24 below stay in the schema and stay
unused. All three tables are empty, and no story loads them.

The route histogram is not stored. Section 4.9 says the route controller computes it at query time
from PostGIS per-segment forecast depths, so it has no table here.

## Tables

The script creates one enum type and three hypertables.

| Table | Time column | Primary key | One row is |
| --- | --- | --- | --- |
| `institution_histogram_bar` | `issued_at` | `institution_id, cycle, issued_at, bar_index` | One hourly bar of one institution's histogram, from one simulation run |
| `background_forecast_depth` | `issued_at` | `segment_id, issued_at, valid_time` | One road segment's forecast depth at one hour, from one `background_cycle` run |
| `depth_history` | `valid_time` | `edge_key, valid_time` | The depth kept on record for one wet graph edge at one moment |

`simulation_cycle` is an enum with the values `constant_cycle` and `background_cycle`. The
`cycle` column in `institution_histogram_bar` and `depth_history` uses it, so a typo or a third
cycle name fails on insert.

`issued_at` is the start time of the simulation run that produced the row, in UTC. For a
`constant_cycle` run, it matches the `timestamp` column in `flood_road_values`. `valid_time` is
the moment a depth applies to. Every time column is `TIMESTAMPTZ`, unlike the naive `TIMESTAMP`
columns in `storage-postgres`, because the depth files are named in Vietnam local time (UTC+7) and
a naive column leaves the zone to convention.

## The histogram split lives in a CHECK

Section 4.9 gives each institution histogram 24 hourly bars. Bars 1-6 come from `constant_cycle`,
which refreshes every 30 minutes. Bars 7-24 come from `background_cycle`, which refreshes every
3-6 hours. The `bar_index_matches_cycle` constraint encodes that rule.

```sql
CHECK (
	(cycle = 'constant_cycle' AND bar_index BETWEEN 1 AND 6)
	OR (cycle = 'background_cycle' AND bar_index BETWEEN 7 AND 24)
)
```

Each cycle writes only its own bars, under its own `issued_at`. A `constant_cycle` refresh adds six
rows and never rewrites the 18 `background_cycle` rows. To serve a histogram, read bars 1-6 from the
latest `constant_cycle` `issued_at` for that institution, and bars 7-24 from the latest
`background_cycle` `issued_at`. The primary key starts with `institution_id, cycle, issued_at`, so
both lookups use the key's index.

A generated `cycle` column, derived from `bar_index`, would also make a mismatch impossible. It
would do so by relabeling the row, though. If a `constant_cycle` loader wrote bar 7 by mistake, a
generated column would file that bar under `background_cycle` without an error. The CHECK rejects
the write instead, and the loader bug shows up on the first run.

Each bar also stores `valid_time`, the start of the clock hour it covers. `bar_index` and
`issued_at` alone don't fix that hour, because a 30-minute cadence starts runs at half past the
hour. The `valid_time_on_the_hour` constraint rejects any `valid_time` that isn't on a whole UTC
hour. Vietnam's offset is a whole number of hours, so a whole UTC hour is also a whole local hour.

The bar value is `max_depth_m`, the highest depth during that hour. A `constant_cycle` run writes
four 15-minute timesteps per hour, so each bar needs one aggregate. The maximum is the safe choice
for a question like "is the clinic reachable at 14:00".

## Forecast series and depth history

`background_forecast_depth` holds only `background_cycle` output. The per-segment series from
`constant_cycle` is already in `flood_road_values`, and the scope PRD adds TimescaleDB only for data
those tables don't hold. A CHECK rejects a `valid_time` earlier than `issued_at`.

`depth_history` keeps one depth per segment per moment, with `valid_time` as its time column,
because history queries ask "what was the depth on this road over the last week". The
`cycle` and `issued_at` columns record which run supplied the value. The primary key allows one row
per segment and moment, so the run with the later `issued_at` wins a moment ([[decision-log|D-032]]).

`history_moment` has one row per moment a run covered, wet or not (`valid_time` as primary key, with `issued_at`).
A moment listed there with no `depth_history` row for an edge means the edge was dry (0 m). A moment missing there is unknown, for example a slot that the rain gate skipped. Both tables are hypertables with 7-day chunks.
`depth_history` is compressed per chunk once the chunk closes (segment by `edge_key`, order by `valid_time`), and both tables drop data older than 365 days.

The DAG `flood_history` (`dags/flood_history_dag.py`) runs on the asset `FLOOD_ROAD_VALUES`, which `flood_on_roads` of `routing_adapter` emits.
`scripts/flood_history/load_run.py` reads the run's moments from `edge_depth_run.valid_times` and its rows from `edge_depth`, which holds the wet edges only ([[US-122-point-depth-history-at-the-edge-table|US-122]], [[decision-log|D-038]]).
Both are naive UTC, and `depth_m` is `depth_cm / 100`.
It writes in one transaction under a table-wide advisory lock.
For each moment it skips the moment when `history_moment` holds a later `issued_at`. Otherwise it deletes the moment's `depth_history` rows, inserts the run's rows, and upserts the moment.
An edge that an earlier run wet and the winning run did not wet therefore has no row. Loading a run again gives the same rows.
A run that `edge_depth_run` does not list is an error. Task `9c` writes the registry row and has no ordering against `flood_on_roads`, so a load that runs first fails and the DAG retries once.

`depth_history.edge_key` is `graph_edge.edge_key` (`<osm_way_id>:<position>`). `create_timescale_tables.py` renames the column `segment_id` of an older table to `edge_key`, which keeps the compressed chunks.
Rows loaded before the move held piece ids (`<way>#<index>`), which cannot be mapped to edges, because the pieces and the edges split a way at different points.
They came from test rain, so the owner decided on 2026-10-12 to delete them.
The rename step deletes every row of `depth_history` and `history_moment` once, so no moment reads as dry for an edge key without a run behind it.
Rebuild the history from runs in `edge_depth` ([[US-113-backfill-per-segment-depth-history|US-113]]).
The migration ran on the server on 2026-10-13, and both tables held no row after it.
Loading run `20261010T223000` twice gave 20,989 rows over 2,874 edges and 8 moments each time.

## Open items

- `edge_key` is `TEXT`. The metric extractor keys on it too (see [[flood-metric-extractor]]). `flood_history` writes `depth_history` and `history_moment`. No loader writes the other tables, since `US-021` was dropped.
- Institutions have no table yet. `institution_id` is `TEXT` for the same reason, and it can't be a
  foreign key because the planned institutions table lives in `storage-postgres`, a different
  database.
- The compression ratio is 1.7 on one chunk that holds one run (3,022,848 to 1,761,280 bytes, 2026-10-12), against the 11.4 expected. One run is too little data to judge. Measure again after [[US-113-backfill-per-segment-depth-history|US-113]] or a day of runs.
- The script ran against a plain PostgreSQL 16 server with the TimescaleDB calls stubbed out. That
  run checked the tables, the enum, every CHECK, and idempotency. The `create_hypertable` calls have
  not run against a real TimescaleDB server yet.
