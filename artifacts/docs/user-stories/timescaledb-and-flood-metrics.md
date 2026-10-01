---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-018", "US-019", "US-020", "US-021", "US-060"]
status: done
subsystem: architecture-backend
source_ideas: []
related: ["[[t3-digital-twin-architecture-gaps]]", "[[sprint-plan]]", "[[minio-flood-extent-pipeline]]", "[[airflow-cannot-import-flood-utils]]"]
tags: [user-story, epic, backend, sprint-1, sprint-2]
---

# Epic: TimescaleDB and flood metrics

Builds the flood metric extractor and TimescaleDB, the two goals
[[t3-digital-twin-architecture-gaps]] keeps in scope after descoping the fast-track trigger, Redis,
and the citizen and council dashboard endpoints. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- **Story 1 (US-018): Design TimescaleDB's histogram and forecast-series schema.**
  As an engineer, I want a settled schema for institution histograms, `background_cycle` forecast
  series, and depth history, so I can populate real data instead of guessing a shape mid-build.
  Given the architecture doc's §4.9 describes the histogram split this schema must support, when the
  schema design is reviewed against that section, then it accounts for both `constant_cycle` and
  `background_cycle` data sources without needing a later migration.
  Priority: P1. Status: Done. Estimate: S. Sprint: 1. Dependencies: None.
  Evidence: ![[timescaledb-schema.png|420]]
  Details:
  1. What: three hypertables and a `simulation_cycle` enum.
  2. How: `create_timescale_tables.py`, with a `CHECK` that ties bars 1 to 6 to `constant_cycle` and bars 7 to 24 to `background_cycle`.
  3. Why: no migration when `background_cycle` data arrives.
  4. Effect: Story 4 loads into these tables, and must first choose a segment key, since road segments have no stable ID.

- **Story 2 (US-019): Stand up the TimescaleDB service.**
  As an engineer, I want TimescaleDB running as its own Docker service, distinct from
  `storage-postgres`, so the metric extractor and population job have somewhere to write.
  Given the schema design from Story 1, when the service is added to `compose.yml` and deployed on
  the remote host, then it starts cleanly and accepts the designed schema's tables.
  Priority: P1. Status: Done. Estimate: S. Sprint: 1. Dependencies: Story 1 (schema informs what the service needs
  to support, though standing up the service itself has no hard technical blocker).
  Evidence: ![[timescaledb-service.png|420]]
  Details:
  1. What: a `timescaledb` container apart from `storage-postgres`.
  2. How: `compose.yml`, image `timescale/timescaledb:2.30.1-pg17`, bound to `127.0.0.1:5434`.
  3. Why: the extractor's output needs a time-series store.
  4. Effect: `compose.yml` requires `TIMESCALE_PASSWORD`, so every compose command fails without it. The image comes from Docker Hub.

- **Story 3 (US-020): Build the flood metric extractor.**
  As a downstream consumer (internal reporting, or a future endpoint), I want time-to-peak,
  recession onset, per-vehicle passability restoration time, T+1h and T+2h forecast depth, and
  pre-closure time computed per road segment per vehicle type, so real flood-impact metrics exist
  instead of raw depth rasters alone.
  Given a completed `constant_cycle` run with at least 2 depth timesteps in `flood_road_values`,
  when the metric extractor runs against that run's `run_ts`, then querying its output table
  returns a row per road segment per vehicle type with a non-null time-to-peak, pre-closure time,
  and T+1h forecast depth, matching the values computable by hand from the same run's raw depth
  rasters for one spot-checked segment.
  Priority: P1. Status: Done. Estimate: L. Sprint: 4 (re-cut 2026-09-29). Dependencies: None (reads `calculate_depth.py`'s output
  directly, independent of TimescaleDB).
  Evidence: ![[us-060-extractor-check-output.png|700]]
  Details:
  1. What: the flood metric extractor, covered by 19 unit tests. It computes time to peak, recession onset, passability restoration, T+1h and T+2h depth, and pre-closure time per road segment and vehicle type.
  2. How: `metrics.py` computes one segment's metrics from its depth series, and `extract_run.py` reads a run from `flood_road_values` and writes `flood_segment_metrics`. It ran in the Airflow worker on the 2026-09-30 02:00:00 run (Story 5).
  3. Why: real flood-impact metrics instead of raw depth rasters alone.
  4. Effect: the loader and writer SQL work on real data. 46,648 rows became 23,324 metric rows in about 4 seconds. The row key is still `md5(ST_AsEWKB(geom_4326))`. `flood_road_values.segment_id` is filled for every row of the run and maps 1 to 1 to the geometry (5,831 each), so Story 4 can switch the key to `segment_id` without changing the segment count. No DAG task runs the extractor yet.

- **Story 4 (US-021): Populate TimescaleDB from the extractor's output.**
  As a downstream consumer, I want the metric extractor's output loaded into TimescaleDB's
  histogram tables, so a day's worth of `constant_cycle` and `background_cycle` data is queryable
  as a time series.
  Given TimescaleDB populated with at least one full day of `constant_cycle` and `background_cycle`
  output for an institution, when its histogram table is queried directly for that institution's 24
  hourly bars, then bars 1 through 6 return `constant_cycle` data and bars 7 through 24 return
  `background_cycle` data, per the architecture doc's §4.9 split. No serving endpoint exists yet.
  this checks the stored data directly.
  Priority: P1. Status: Dropped (2026-10-01, D-009 in [[decision-log]]). Estimate: M. Sprint: 4 (re-cut 2026-09-29). Dependencies: Story 2, Story 3, [[raster-first-pipeline-stories]] Story 1 (the `segment_id`), and
  [[airflow-cannot-import-flood-utils]].

- **Story 5 (US-060): Run the flood metric extractor on a retained run.**
  As the owner of Sprint 4's goal, I want the extractor (Story 3, `US-020`) run against a real run, so the
  metrics are proven on real depth series before Story 4 loads them on a schedule.
  Given a retained run in `flood_road_values` on the server, for example `timestamp` 2026-09-30 02:00:00 (46,648
  rows, forecast times 02:00 to 03:45), when `scripts/flood_metrics/extract_run.py` runs with that run's
  timestamp, then `flood_segment_metrics` holds one row per segment and vehicle type for that run, the segment
  count equals the number of distinct `geom_4326` values of the run, and for three segments chosen by hand the
  stored `peak_depth_m` equals the largest `depth` of the segment in `flood_road_values`.
  On 2026-09-30 the server held retained runs from 2026-09-29 15:00 to 16:30 and 2026-09-30 01:30 to 02:00, so the
  data exists today. `flood_mapping_full` is paused, so no new run arrives until it is unpaused. This story needs
  none. Story 4's scheduled load does need the DAG unpaused, and that stays with Story 4.
  Priority: P1. Status: Done. Estimate: XS. Sprint: 4 (added 2026-09-30). Dependencies: Story 3 (built, `Reviewed`),
  Story 2 (`US-019`, the TimescaleDB service). Story 3 moves to `Done` with this story's evidence.
  Test points: no coordinate is involved.
  Evidence: ![[us-060-extractor-check-output.png|700]]
  Details:
  1. What: the extractor ran on the retained run 2026-09-30 02:00:00 (46,648 rows).
  2. How: `extract_run.py 20260930T020000` inside `airflow_new-airflow-worker-1`, then `evidence/us-060-extractor-check.sh` compared the stored rows with `flood_road_values`.
  3. Why: to prove the metrics on a real depth series before Story 4 loads them on a schedule.
  4. Effect: 5,831 segments stored, equal to the run's 5,831 distinct `geom_4326` values, with 4 vehicle types and 23,324 rows. `peak_depth_m` equals the largest `depth` for three hand-picked segments (7.147252 m on `way/952973245`, 0.199990 m on Ngõ 153 Phố Phú Đô, 0.000016 m on Đại lộ Thăng Long) and for all 5,831. Story 3 is `Done` with this evidence. Story 4's scheduled load still needs `flood_mapping_full` unpaused. The output was captured from the Mac (`gods-macbook.local`) against the server's containers at 100.67.84.55.

## Status history

- **2026-09-23, draft.** Drafted from [[t3-digital-twin-architecture-gaps]]'s Goals and Definition
  of done sections, after the fast-track trigger, Redis, and citizen and dashboard endpoint goals
  were descoped from that PRD.
- **2026-09-23, draft.** Stories 1 and 2 built and reviewed, pushed in commits `f663dba` and
  `d7a2d78`. Status is `Reviewed`, not `Done`, because the schema has not yet applied against a real
  TimescaleDB container on the remote host. That check is the acceptance criterion for both stories.
- **2026-09-23, draft.** Story 3 built and reviewed on branch `worktree-agent-a77ab581261ff0349`
  (commits `4d81d59`, `cdada59`, `b229926`). The pure extractor passes 19 tests. On the real
  `flood_road` sample, one segment matches a hand computation. Status is `Reviewed`, not `Done`,
  because the loader and writer SQL has never run against Postgres, and the check from raster to
  segment has not run.
- **2026-09-23, draft.** The extractor cannot run inside Airflow until `flood_utils.py` is
  importable there. Tracked as [[airflow-cannot-import-flood-utils]]. It blocks Story 4's DAG
  wiring, not Story 3's own status.
- **2026-09-24, draft.** Stories 1 and 2 done. On the remote host, the `timescaledb` container is
  healthy on TimescaleDB 2.30.1, the schema script's SQL ran twice with no errors and left three
  hypertables and three tables, and `bar_index_matches_cycle` rejected bar 7 for `constant_cycle`.
  Story 3 stays `Reviewed`: the extractor's loader and writer have not run against a real run, and
  [[airflow-cannot-import-flood-utils]] blocks running it in Airflow.
- **2026-09-24, draft.** The extractor's row key will change from `md5(ST_AsEWKB(geom_4326))` to the
  `segment_id` of the `road_segment` table ([[raster-first-pipeline-stories]] Story 1). Story 3 is
  `Reviewed` with the old key, and its `flood_segment_metrics` rows on the server must be rebuilt after
  the change. Story 4 waits for the new key and for [[airflow-cannot-import-flood-utils]].
- **2026-09-29, draft.** Stories 3 and 4 moved from Sprint 2 to Sprint 4 in [[sprint-plan]]: no frontend story waits on them, so the point-depth work goes first.
- **2026-09-30, draft.** Story 5 (`US-060`) added to Sprint 4: run the extractor on a retained run. Story 3 (`US-020`) had never run on real data, and the sprint goal needs it. Retained runs exist on the server.
- **2026-10-01, draft.** Stories 5 and 3 (`US-060`, `US-020`) are `Done`: the extractor ran on the 2026-09-30 02:00:00 run in the Airflow worker, and all 5,831 segments match `flood_road_values`. Output rendered as `us-060-extractor-check-output.png`. Story 4 (`US-021`) can switch the row key to `segment_id`, which maps 1 to 1 to the geometry for this run.
- **2026-10-01, draft.** Story 4 (`US-021`) is `Blocked`. Its acceptance check needs `background_cycle` output and an institution, and neither exists: no DAG runs a `background_cycle` forecast, and no institutions table or list exists. The extractor's rows are per-segment summaries, not hourly bars. Options and a recommendation (load per-segment `depth_history` from `flood_road_values` first) are in [[timescaledb-load-has-no-source-for-histogram-bars]]. The user decides the scope.
- **2026-10-01, done.** Story 4 (`US-021`) is `Dropped`: the user said the pipeline no longer runs `background_cycle`, and the story's acceptance check needs it (D-009 in [[decision-log]]). The ID is not reused. Story 1 (`US-018`) stays `Done`, since the schema was built. Its `background_cycle` enum value, `background_forecast_depth` table, and bars 7 to 24 CHECK stay in the database and stay unused. Every other story of this epic is `Done`, so the epic is `done`.
