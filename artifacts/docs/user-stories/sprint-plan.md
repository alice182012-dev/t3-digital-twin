---
date: 2026-09-23
type: plan
status: active
plan_number: 1
tags: [user-story, sprint-plan]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[t3-digital-twin-architecture-gaps]]", "[[point-depth-lookup-backend]]", "[[timescaledb-and-flood-metrics]]", "[[frontend-polish]]", "[[frontend-depth-features]]", "[[depth-forecast-chart]]", "[[route-forecast-query]]", "[[truck-routing-profile]]", "[[mockup-screen-coverage]]"]
---

# Sprint plan: PRD backlog, 2026-09

Nineteen stories, drawn from [[flood-routing-mockup-frontend-gap]] and
[[t3-digital-twin-architecture-gaps]], sequenced into four sprints with nothing left unscheduled.
No team roster or calendar is connected for this project, so this plan sizes work by dependency
order and relative estimate, not by tracked capacity in hours or points per person. Revise the
per-sprint story count once real velocity is known.

## How many sprints, and why

Four. Three of them come from one hard dependency: four frontend stories
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
- **Sprint 4** shows the truck routing profile in the frontend ([[truck-routing-profile]]). It
  depends on nothing above, and sits last because the user placed it there.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`.
`Reviewed` means the code is built and read through but its acceptance check has not run yet. Each story carries the
same Status in its epic file, as a `Status:` field on its Priority line or a Status section in a
single-story file. Update both together.

## Sprint 1: backend prerequisites and independent frontend wins

**Sprint goal:** every prerequisite the rest of the backlog depends on is in place, and the two
frontend stories with no backend dependency ship.

| Priority | Story                                                       | Estimate | Epic                              | Dependencies                     | Evidence                                    | Details                                                                                                                                                                                                                                                                                                                                                                                                                      | Status |
| -------- | ----------------------------------------------------------- | -------- | --------------------------------- | -------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| P0       | Regression-harden `floodmap-backend` before adding new load | M        | [[point-depth-lookup-backend]]    | None                             | ![[harden-floodmap-backend-tests.png\|120]] | What: regression tests for `server.py` and `flood_areas.py`. How: `test_flood_areas.py` and `test_server.py` run against a real PostGIS and a stub GraphHopper. Why: `GET /flood/points` would otherwise land on an unproven backend. Effect: unblocks the point-depth stories. The soak period and the Valhalla comparison stay open in `TODOS.md`.                                                                         | Done   |
| P0       | Load `depth.tif` into PostGIS as a raster                   | M        | [[point-depth-lookup-backend]]    | None                             | ![[depth-raster-postgis-load.png\|120]]     | What: each timestep's `depth.tif` becomes a row in `flood_depth_raster`. How: `raster_load.py` reprojects EPSG:3405 to EPSG:4326 and loads it with `ST_FromGDALRaster`, in DAG task `9b_load_depth_raster`. Why: a point lookup needs the exact pixel. Effect: unblocks `GET /flood/points`. On the server, the row for run `20260924T153638` matches the source file's size and corner. The DAG task has not run there yet. | Done   |
| P1       | Design TimescaleDB's histogram and forecast-series schema   | S        | [[timescaledb-and-flood-metrics]] | None                             | ![[timescaledb-schema.png\|120]]            | What: three hypertables and a `simulation_cycle` enum. How: `create_timescale_tables.py`, with a `CHECK` that ties bars 1 to 6 to `constant_cycle` and bars 7 to 24 to `background_cycle`. Why: no migration when `background_cycle` data arrives. Effect: Story 4 loads into these tables, and must first choose a segment key, since road segments have no stable ID.                                                      | Done   |
| P1       | Stand up the TimescaleDB service                            | S        | [[timescaledb-and-flood-metrics]] | Schema design story, same sprint | ![[timescaledb-service.png\|120]]           | What: a `timescaledb` container apart from `storage-postgres`. How: `compose.yml`, image `timescale/timescaledb:2.30.1-pg17`, bound to `127.0.0.1:5434`. Why: the extractor's output needs a time-series store. Effect: `compose.yml` requires `TIMESCALE_PASSWORD`, so every compose command fails without it. The image comes from Docker Hub.                                                                             | Done   |
| P2       | Add per-mode travel time under the four mode icons          | M        | [[frontend-polish]]               | None                             | ![[frontend-per-mode-travel-time.png\|120]] | What: a travel time under each mode icon, with the selected mode in bold. How: `useProfileTimes` sends one route request per profile for each query. Why: compare modes without switching. Effect: four requests per query. Truck is missing until Sprint 4, and every mode uses the motorbike flood limit ([[flood-routing-vehicle-type-always-motorbike]]).                                                                | Done   |
| P2       | Add the "Updated `date` `time`" line to the flood legend    | S        | [[frontend-polish]]               | None                             | ![[frontend-legend-updated-line.png\|120]]  | What: an "Updated" line under the legend bands. How: `FloodLegend` formats the selected timestep with `formatTimestepTime`, in the viewer's local time. Why: it shows how current the flood data is. Effect: the legend is one line taller, and the mobile search panel covers it ([[mobile-flood-legend-covered-by-search-panel]]).                                                                                         | Done   |

Logged for traceability, outside the table: switching the search geocoder's default locale to `vi`
(see [[frontend-polish]]). It is `Blocked`, because place search fails on the live UI
([[photon-rejects-vi-locale]]).

## Sprint 2: new backend surface

**Sprint goal:** `GET /flood/points` is live and timing-validated, and the flood metric extractor
is writing real output into TimescaleDB.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ------- | ------ |
| P0 | Build `GET /flood/points` | M | [[point-depth-lookup-backend]] | Sprint 1's harden and raster-load stories | ![[flood-points-endpoint.png\|120]] | What: `GET /flood/points` returns the depth at a lat/lon and timestep. How: `flood_points.py` reads `flood_depth_raster` with `ST_Value`. A pixel of 0 reads `dry`, and a point outside the raster reads `no_data`. Why: the popup and badges need the exact pixel, not a band. Effect: unblocks the latency check and the three Sprint 3 point stories. Without `run=`, it returns 404 when the newest run has no raster. On a real `depth.tif`, it matched `gdallocationinfo` at three points. | Done |
| P0 | Validate `GET /flood/points`'s latency under concurrent taps | S | [[point-depth-lookup-backend]] | This sprint's endpoint story | None yet | - | Not started |
| P1 | Build the route-forecast query against `flood_road_values` | M | [[route-forecast-query]] | Sprint 1's harden-first story | None yet | - | Not started |
| P1 | Build the flood metric extractor | L | [[timescaledb-and-flood-metrics]] | None (reads `calculate_depth.py` output directly) | None yet | Built and covered by 19 unit tests. Not run against a real run. It cannot run in Airflow until [[airflow-cannot-import-flood-utils]] is fixed. | Reviewed |
| P1 | Populate TimescaleDB from the extractor's output | M | [[timescaledb-and-flood-metrics]] | Sprint 1's schema and service stories, this sprint's extractor story | None yet | - | Not started |
| P2 | Verify the first-load, empty-panel, and autofill screens against the mockup | S | [[mockup-screen-coverage]] | None, needs the frontend rebuilt on the remote host | None yet | - | Not started |

## Sprint 3: frontend depth features

**Sprint goal:** the four frontend goals that were blocked on Sprint 2's backend work are live in
the UI, matching the mockup.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ------- | ------ |
| P0 | Place-depth popup on map tap | M | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | None yet | - | Not started |
| P0 | Per-step depth in turn-by-turn instructions | S | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | None yet | - | Not started |
| P0 | Per-point depth badges along the route polyline | M | [[frontend-depth-features]] | Sprint 2's `GET /flood/points` stories | None yet | - | Not started |
| P0 | Depth-versus-time forecast chart | M | [[depth-forecast-chart]] | Sprint 2's route-forecast query story | None yet | - | Not started |
| P1 | Route to a place from the place popup | S | [[mockup-screen-coverage]] | This sprint's place-depth popup story | None yet | - | Not started |

## Sprint 4: truck routing profile

**Sprint goal:** the frontend offers the truck profile, matching the four vehicle modes the
backend already serves.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ------- | ------ |
| P2 | Show the truck routing profile in the frontend | S | [[truck-routing-profile]] | None | None yet | - | Not started |

This sprint holds one story. It has no dependency on Sprints 1 to 3, so it can move earlier if
capacity allows. The user placed it in Sprint 4. See the story's Known risk about the flood depth
limit that a truck route uses.

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| `GET /flood/points`'s latency under concurrent taps (Sprint 2) comes back too slow for a live raster query. | Sprint 3's three stories would need a pre-computed lookup grid instead, a larger change than currently scoped, pushing Sprint 3 out. | Run the latency validation story early in Sprint 2, not last, so a redesign decision has runway before Sprint 3 starts. |
| The flood metric extractor (Sprint 2, estimated L) runs long, since it computes five distinct metrics (time-to-peak, recession onset, per-vehicle passability restoration, T+1h and T+2h forecast depth, pre-closure time) per road segment per vehicle type. | TimescaleDB population slips, which does not block Sprint 3 (frontend work depends on `GET /flood/points`, not on TimescaleDB), but slips [[timescaledb-and-flood-metrics]]'s own definition of done. | Track it as its own story rather than folding it into the TimescaleDB story, so a slip is visible and isolated instead of hiding inside a bundled estimate. |
| No team roster or velocity data is connected to this plan. | Sprint boundaries above are dependency-ordered, not capacity-checked, so a sprint could be over- or under-loaded for the actual team size. | Revise the per-sprint story count once real velocity from Sprint 1 is known, rather than trusting the estimate column blind. |
| The route-forecast query's segment-matching approach (Sprint 2) is unresolved: `flood_road_values` has no stable segment ID. | If neither a GraphHopper path-detail nor a spatial join proves accurate, the forecast chart (Sprint 3) could ship averaging the wrong segments, a wrong-but-plausible number rather than an obvious failure. | Don't start [[depth-forecast-chart]] until [[route-forecast-query]]'s own spot-checked acceptance criteria pass, not just until the query returns something. |

## Definition of done

A story is `Done` only when its row carries evidence and details, and its epic file carries the same.
**Evidence** is a screenshot of that story working, saved under `evidence/` next to this file. A UI
story gets a screenshot of the running UI. A backend story with no UI gets a screenshot of the real
output: the endpoint's response in a browser, or the verbatim command output rendered to an image
whose caption says so and gives the capture time and host. Capture it where the acceptance criteria
name, the server when they say server. **Details** answer what was built, how, why, and what it
changes for dependent stories, in a few sentences. A built story without evidence stays `Reviewed`.

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
- **2026-09-23, active.** Added the `Reviewed` status. Marked the TimescaleDB schema and service
  stories `Reviewed`, pending the remote-host check.
- **2026-09-23, active.** Marked both [[frontend-polish]] stories `Reviewed`, pending a run
  against the live backend.
- **2026-09-23, active.** Added Sprint 4 with [[truck-routing-profile]], at the user's request.
  This extends the plan instead of starting `sprint-plan-2.md`, to keep every story's Status in
  one file.
- **2026-09-23, active.** Marked `GET /flood/points` and the flood metric extractor `Reviewed`,
  pending checks against real data and a real database.
- **2026-09-24, active.** Mapped mockup screens 2a to 2f to stories in [[mockup-screen-coverage]].
  Added two stories: a verification story in Sprint 2 and the popup's route button in Sprint 3.
  No existing story was duplicated.
- **2026-09-24, active.** Marked five stories `Done` after checks on the remote host: both TimescaleDB
  stories, both [[frontend-polish]] stories, and `GET /flood/points`. The flood metric extractor
  stays `Reviewed`.
- **2026-09-24, active.** Added an Evidence column and a Details column to every sprint table, and
  the evidence rule to the definition of done. Backfilled evidence for the seven stories that were
  `Done`. The geocoder locale story in [[frontend-polish]] moved to `Blocked`, because its evidence
  check found that place search fails on the live UI ([[photon-rejects-vi-locale]]).
