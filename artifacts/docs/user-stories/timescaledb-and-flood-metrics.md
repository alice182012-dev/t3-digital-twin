---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: architecture-backend
source_ideas: []
related: ["[[t3-digital-twin-architecture-gaps]]", "[[sprint-plan]]", "[[minio-flood-extent-pipeline]]"]
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
  Priority: P1. Status: Reviewed. Estimate: S. Sprint: 1. Dependencies: None.

- **Story 2: Stand up the TimescaleDB service.**
  As an engineer, I want TimescaleDB running as its own Docker service, distinct from
  `storage-postgres`, so the metric extractor and population job have somewhere to write.
  Given the schema design from Story 1, when the service is added to `compose.yml` and deployed on
  the remote host, then it starts cleanly and accepts the designed schema's tables.
  Priority: P1. Status: Reviewed. Estimate: S. Sprint: 1. Dependencies: Story 1 (schema informs what the service needs
  to support, though standing up the service itself has no hard technical blocker).

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
  Priority: P1. Status: Not started. Estimate: M. Sprint: 2. Dependencies: Story 2, Story 3.

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
