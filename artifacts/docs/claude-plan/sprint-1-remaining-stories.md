---
date: 2026-09-23
type: plan
status: active
tags: [plan, sprint-1, timescaledb, frontend]
related: ["[[SP-01-prd-and-backlog|sprint-plan]]", "[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]"]
---

# Sprint 1: remaining stories

Four Sprint 1 stories were not started when this plan was written (see [[SP-01-prd-and-backlog|sprint-plan]]). This plan
finishes them in two independent workstreams.

## Workstreams

| Workstream | Stories | Files touched | Verification |
| ---------- | ------- | ------------- | ------------ |
| TimescaleDB | [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Story 1 (schema design) and Story 2 (service) | `compose.yml`, `scripts/database/`, a schema design note under `artifacts/docs/` | Schema applies cleanly to a real TimescaleDB container on the remote host |
| Frontend polish | [[EP-02-frontend-polish|frontend-polish]] Story 1 (per-mode travel time) and Story 2 ("Updated" line on the flood legend) | `floodmap/graphhopper-maps/src/` | The built frontend renders both changes |

The workstreams share no files, so they run in parallel, each in its own worktree.

## Decisions

- The TimescaleDB stories are one owner's work, since the service must accept the schema that Story 1
  designs.
- The schema enforces the architecture doc's section 4.9 split in the database. A `CHECK` ties
  `bar_index` 1 to 6 to `constant_cycle` and 7 to 24 to `background_cycle`, so no later migration
  is needed.
- Delegates do not deploy. Docker runs on the remote host only, so the lead pushes and verifies
  there.

## Status

- **2026-09-23.** Plan written, delegates not yet started.
- **2026-09-23.** TimescaleDB stories pushed as `f663dba` and `d7a2d78`, marked `Reviewed`,
  pending the remote-host check. Frontend delegate still running.

## Next wave: stories with no TimescaleDB dependency

| Workstream | Story | Files touched | Why parallel |
| ---------- | ----- | ------------- | ------------ |
| Point depth | [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 3, `GET /flood/points` | `floodmap/` backend `server.py` and its tests | Owns `server.py` |
| Metric extractor | [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Story 3, flood metric extractor | new files under `scripts/` | Reads `flood_road_values`, writes its own output, no shared files |

Held back: [[US-017-route-forecast-query|route-forecast-query]] also edits `server.py`, so it waits for `GET /flood/points` to
land. [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 4 (latency) needs Story 3. [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]
Story 4 needs the TimescaleDB check and the extractor.
