---
date_drafted: 2026-09-23
type: user-story
status: draft
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

- **Story 1: Design TimescaleDB's histogram and forecast-series schema.**
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

- **Story 2: Stand up the TimescaleDB service.**
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

- **Story 3: Build the flood metric extractor.**
  As a downstream consumer (internal reporting, or a future endpoint), I want time-to-peak,
  recession onset, per-vehicle passability restoration time, T+1h and T+2h forecast depth, and
  pre-closure time computed per road segment per vehicle type, so real flood-impact metrics exist
  instead of raw depth rasters alone.
  Given a completed `constant_cycle` run with at least 2 depth timesteps in `flood_road_values`,
  when the metric extractor runs against that run's `run_ts`, then querying its output table
  returns a row per road segment per vehicle type with a non-null time-to-peak, pre-closure time,
  and T+1h forecast depth, matching the values computable by hand from the same run's raw depth
  rasters for one spot-checked segment.
  Priority: P1. Status: Reviewed. Estimate: L. Sprint: 2. Dependencies: None (reads `calculate_depth.py`'s output
  directly, independent of TimescaleDB).

- **Story 4: Populate TimescaleDB from the extractor's output.**
  As a downstream consumer, I want the metric extractor's output loaded into TimescaleDB's
  histogram tables, so a day's worth of `constant_cycle` and `background_cycle` data is queryable
  as a time series.
  Given TimescaleDB populated with at least one full day of `constant_cycle` and `background_cycle`
  output for an institution, when its histogram table is queried directly for that institution's 24
  hourly bars, then bars 1 through 6 return `constant_cycle` data and bars 7 through 24 return
  `background_cycle` data, per the architecture doc's §4.9 split. No serving endpoint exists yet.
  this checks the stored data directly.
  Priority: P1. Status: Not started. Estimate: M. Sprint: 2. Dependencies: Story 2, Story 3, [[raster-first-pipeline-stories]] Story 1 (the `segment_id`), and
  [[airflow-cannot-import-flood-utils]].

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

