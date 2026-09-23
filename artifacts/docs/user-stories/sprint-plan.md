---
date: 2026-09-23
type: plan
status: active
plan_number: 1
tags: [user-story, sprint-plan]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[t3-digital-twin-architecture-gaps]]", "[[point-depth-lookup-backend]]", "[[timescaledb-and-flood-metrics]]", "[[frontend-polish]]", "[[frontend-depth-features]]", "[[depth-forecast-chart]]", "[[route-forecast-query]]"]
---

# Sprint plan: PRD backlog, 2026-09

Sixteen stories, drawn from [[flood-routing-mockup-frontend-gap]] and
[[t3-digital-twin-architecture-gaps]], sequenced into three sprints with nothing left unscheduled.
No team roster or calendar is connected for this project, so this plan sizes work by dependency
order and relative estimate, not by tracked capacity in hours or points per person. Revise the
per-sprint story count once real velocity is known.

## How many sprints, and why

Three. The backlog splits along one hard dependency: four frontend stories
([[frontend-depth-features]], [[depth-forecast-chart]]) call an endpoint or query that does not
exist until Sprint 2's backend stories land. That single dependency is what forces a third sprint
rather than two: everything else in the backlog (TimescaleDB, the metric extractor, the two
independent frontend stories) can run in parallel with the endpoint work, but nothing can call an
endpoint or query that is not built yet.

- **Sprint 1** builds the prerequisites the rest of the backlog depends on
  ([[point-depth-lookup-backend]]'s harden-first and raster-load stories, [[timescaledb-and-flood-metrics]]'s
  schema and service setup) alongside two frontend stories with no backend dependency at all
  ([[frontend-polish]]).
- **Sprint 2** builds the three pieces of new backend surface those prerequisites unlock: the
  `GET /flood/points` endpoint, the route-forecast query ([[route-forecast-query]]), and the flood
  metric extractor plus its TimescaleDB population.
- **Sprint 3** builds the four frontend stories that were blocked on Sprint 2's backend work:
  [[frontend-depth-features]]'s three `GET /flood/points`-dependent stories, plus
  [[depth-forecast-chart]], now unblocked (see its Status history).

Each story's Status is `Not started`, `In progress`, `Blocked`, or `Done`. Update it here and in
the story's epic file together.

## Sprint 1: backend prerequisites and independent frontend wins

**Sprint goal:** every prerequisite the rest of the backlog depends on is in place, and the two
frontend stories with no backend dependency ship.

| Priority | Story | Estimate | Epic | Dependencies | Status |
| -------- | ----- | -------- | ---- | ------------ | ------ |
| P0 | Regression-harden `floodmap-backend` before adding new load | M | [[point-depth-lookup-backend]] | None | Done |
| P0 | Load `depth.tif` into PostGIS as a raster | M | [[point-depth-lookup-backend]] | None | Done |
| P1 | Design TimescaleDB's histogram and forecast-series schema | S | [[timescaledb-and-flood-metrics]] | None | Not started |
| P1 | Stand up the TimescaleDB service | S | [[timescaledb-and-flood-metrics]] | Schema design story, same sprint | Not started |
| P2 | Add per-mode travel time under the four mode icons | M | [[frontend-polish]] | None | Not started |
| P2 | Add the "Updated `date` `time`" line to the flood legend | S | [[frontend-polish]] | None | Not started |

Already done, logged for traceability: switching the search geocoder's default locale to `vi` (see
[[frontend-polish]]).

## Sprint 2: new backend surface

**Sprint goal:** `GET /flood/points` is live and timing-validated, and the flood metric extractor
is writing real output into TimescaleDB.

| Priority | Story | Estimate | Epic | Dependencies | Status |
| -------- | ----- | -------- | ---- | ------------ | ------ |
| P0 | Build `GET /flood/points` | M | [[point-depth-lookup-backend]] | Sprint 1's harden and raster-load stories | Not started |
| P0 | Validate `GET /flood/points`'s latency under concurrent taps | S | [[point-depth-lookup-backend]] | This sprint's endpoint story | Not started |
| P1 | Build the route-forecast query against `flood_road_values` | M | [[route-forecast-query]] | Sprint 1's harden-first story | Not started |
| P1 | Build the flood metric extractor | L | [[timescaledb-and-flood-metrics]] | None (reads `calculate_depth.py` output directly) | Not started |
| P1 | Populate TimescaleDB from the extractor's output | M | [[timescaledb-and-flood-metrics]] | Sprint 1's schema and service stories, this sprint's extractor story | Not started |

## Sprint 3: frontend depth features

**Sprint goal:** the four frontend goals that were blocked on Sprint 2's backend work are live in
the UI, matching the mockup.

| Priority | Story | Estimate | Epic | Dependencies | Status |
| -------- | ----- | -------- | ---- | ------------ | ------ |
| P0 | Place-depth popup on map tap | M | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | Not started |
| P0 | Per-step depth in turn-by-turn instructions | S | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | Not started |
| P0 | Per-point depth badges along the route polyline | M | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | Not started |
| P0 | Depth-versus-time forecast chart | M | [[depth-forecast-chart]] | Sprint 2's route-forecast query story | Not started |

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `GET /flood/points`'s latency under concurrent taps (Sprint 2) comes back too slow for a live raster query. | Sprint 3's three stories would need a pre-computed lookup grid instead, a larger change than currently scoped, pushing Sprint 3 out. | Run the latency validation story early in Sprint 2, not last, so a redesign decision has runway before Sprint 3 starts. |
| The flood metric extractor (Sprint 2, estimated L) runs long, since it computes five distinct metrics (time-to-peak, recession onset, per-vehicle passability restoration, T+1h and T+2h forecast depth, pre-closure time) per road segment per vehicle type. | TimescaleDB population slips, which does not block Sprint 3 (frontend work depends on `GET /flood/points`, not on TimescaleDB), but slips [[timescaledb-and-flood-metrics]]'s own definition of done. | Track it as its own story rather than folding it into the TimescaleDB story, so a slip is visible and isolated instead of hiding inside a bundled estimate. |
| No team roster or velocity data is connected to this plan. | Sprint boundaries above are dependency-ordered, not capacity-checked, so a sprint could be over- or under-loaded for the actual team size. | Revise the per-sprint story count once real velocity from Sprint 1 is known, rather than trusting the estimate column blind. |
| The route-forecast query's segment-matching approach (Sprint 2) is unresolved: `flood_road_values` has no stable segment ID. | If neither a GraphHopper path-detail nor a spatial join proves accurate, the forecast chart (Sprint 3) could ship averaging the wrong segments, a wrong-but-plausible number rather than an obvious failure. | Don't start [[depth-forecast-chart]] until [[route-forecast-query]]'s own spot-checked acceptance criteria pass, not just until the query returns something. |

## Definition of done

Per sprint, the same as each story's own acceptance criteria (see each epic file), plus: the
story's `status` frontmatter moves to `done`, and a dated bullet is added to its epic file's
Status history.

## Status history

- **2026-09-23, active.** Drafted from [[flood-routing-mockup-frontend-gap]] and
  [[t3-digital-twin-architecture-gaps]]'s Goals sections.
- **2026-09-23, active.** Moved [[depth-forecast-chart]] out of the backlog into Sprint 3, and
  added [[route-forecast-query]] to Sprint 2: `flood_road_values` already holds the forecast
  chart's data, reversing the earlier "no data source" conclusion. See
  [[verify-table-capability-against-write-path-not-summary-or-current-query]].
- **2026-09-23, active.** Added a Status column to every sprint table. Marked the harden-first
  story and the raster-load story (commit `118e04a`) `Done`. Every other story is `Not started`.
