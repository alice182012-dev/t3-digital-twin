---
date_open: 2026-10-01
date_closed: 2026-10-01
type: blocker
status: wont-fix
severity: P2
subsystem: architecture-backend
approaches_tried: 0
approaches_remaining: 0
tags: [blocker, timescaledb, histogram, institutions, background-cycle]
related: ["[[timescaledb-and-flood-metrics]]", "[[t3-digital-twin-architecture-gaps]]", "[[timescaledb-schema]]", "[[flood-metric-extractor]]", "[[sprint-plan]]", "[[verify-decisions-resolve-the-stated-question]]"]
last_updated: 2026-10-01
---

# The TimescaleDB load has no source for the histogram bars

## Description

`US-021` ([[timescaledb-and-flood-metrics]] Story 4) says: with a full day of `constant_cycle` and `background_cycle` output for an institution loaded, a query for that institution's 24 hourly bars returns bars 1 to 6 from `constant_cycle` and bars 7 to 24 from `background_cycle`. The acceptance check cannot pass, because two of its inputs do not exist. Checked on 2026-10-01.

1. **No `background_cycle` producer.** The word appears only in `scripts/database/create_timescale_tables.py`. The DAGs in `dags/` run one cycle, the 15-minute `flood_mapping_full`. Nothing runs a forecast every 3 to 6 hours.
2. **No institutions.** No code, table, or file outside `artifacts/` mentions an institution. The architecture doc lists the institutions table as "Designed, not built", and `institution_id` in `institution_histogram_bar` has nothing to point at.
3. **The extractor does not produce bars.** A bar is the highest depth during one clock hour at one institution. `flood_segment_metrics` holds one row per road segment and vehicle type for a run (peak, time to peak, and similar). It has no hourly depth and no institution.

The three TimescaleDB hypertables exist and are empty (`institution_histogram_bar`, `background_forecast_depth`, `depth_history`). The architecture doc says the histogram types are "query-pattern-dependent on data the built pipeline does not yet produce".

## Why this matters

`US-021` is a P1 row in Sprint 4. It stays `Blocked` until the user decides what it should load. It blocks no later build: no story in [[sprint-plan-2]] or [[sprint-plan-3]] reads TimescaleDB. Under rule 11 of `.claude/CLAUDE.md` that is the "does not block further build" case, but a subagent cannot fix it, because the fix is a scope decision.

The PRD ([[t3-digital-twin-architecture-gaps]]) says the point of this goal is that per-segment and per-institution flood history can be queried without raw rasters. This blocker is about which part of that can be built from data that exists.

## Approaches tried

None. This page records the options.

## Candidate approaches

| Option | What it loads | Needs | Cost |
| ------ | ------------- | ----- | ---- |
| A. Per-segment history only | `depth_history`: one depth per `segment_id` and `valid_time` from `flood_road_values`, loaded after each run, later run wins | Nothing new. `segment_id` is filled on every row and maps 1 to 1 to the geometry (checked on the 2026-09-30 02:00:00 run) | M. Acceptance becomes "a day of one segment's depth is queryable by time". The extractor is not needed. |
| B. Option A, plus institution bars 1 to 6 | The `constant_cycle` bars for institutions | An institutions list (which places, from where) in `storage-postgres`, and a lookup of the depth at each institution point for each hour | L. Bars 7 to 24 stay empty. |
| C. Option B, plus bars 7 to 24 | `background_cycle` runs and their bars | A new 3Di forecast run every 3 to 6 hours with its own rain input | XL. A separate epic. |

Recommendation: A now, with B and C written as new stories after the user chooses which institutions to model. A is the only option whose input exists today, and it still serves the PRD's reason for TimescaleDB.

## Decision and explanation

The user decided on 2026-10-01 that the pipeline does not run `background_cycle` and dropped every story that needs it (D-009 in [[decision-log]]). `US-021` is `Dropped`, so nothing is blocked. Options B and C are closed. Option A (per-segment `depth_history` from `flood_road_values`) has no story. It stays available if a consumer for per-segment history appears.

## Related topics

- [[timescaledb-and-flood-metrics]], Story 4
- [[timescaledb-schema]]
- [[flood-metric-extractor]]
- [[verify-decisions-resolve-the-stated-question]]: Story 4 was written from the PRD's goal without checking that its inputs exist.

## Status history

- **2026-10-01, open.** Found while planning `US-021` after `US-060` closed. Facts checked in `dags/`, the repo, the TimescaleDB container (all three hypertables empty), and the architecture doc. `US-021` set to `Blocked`.
- **2026-10-01, wont-fix.** The user said `background_cycle` is not run anymore. `US-021` is `Dropped` (D-009 in [[decision-log]]), so the blocker has no work left.
