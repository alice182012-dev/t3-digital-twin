---
date_open: 2026-09-25
date_closed: 2026-10-09
type: blocker
status: resolved
severity: P1
subsystem: floodmap-backend
approaches_tried: 0
approaches_remaining: 3
tags: [blocker, routing, forecast, graphhopper, safety]
related: ["[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]", "[[US-017-route-forecast-query|route-forecast-query]]", "[[US-001-depth-forecast-chart|depth-forecast-chart]]", "[[graphhopper-backend]]"]
last_updated: 2026-10-09
---

# Routing checks each road at one moment, not at the time the traveller reaches it

## Description

A route request carries one timestep. The frontend interceptor in `FloodStore.ts`
(`installRoutingInterceptor`) adds the selected `valid_time` and `run` to `POST /route`.
`_handle_route` in `floodmap/graphhopper-flood-road/backend/server.py` builds one `custom_model` from the
flood areas at that timestep (`cached_areas(valid_time, ...)`), and GraphHopper routes with it. Every road
on the route is judged at the same moment.

The user's example: someone leaves now on a 20-minute route. A road reached at minute 15 is dry now but
flooded by minute 15. Today's routing sends them down it.

## Why this matters

This is a safety gap. [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] moves the map to "now", so the forecast has to show up
somewhere. Routing is where it changes what people do.

## Candidate approaches

None tried.

| Option | How | Effort | Cost and risk |
| --- | --- | --- | --- |
| A. Worst case over the trip | Build the `custom_model` from the deepest water on each road across all timesteps from now to now plus a trip-time bound (for example 1 hour). | S to M | Simple and safe. Too cautious on long trips: it avoids a road that floods after the traveller has passed it. |
| B. Check the arrival time, then re-route | Route with now. Compute the arrival time on each road from GraphHopper's time data. Look up the depth at the timestep for each arrival time. If a road on the route is impassable at arrival, block it and route again. Repeat until the route holds. | M to L | Several GraphHopper calls per route. Needs a limit on repeats. |
| C. Time-dependent routing | Edge weights that depend on arrival time, inside the routing engine. | L | A GraphHopper `custom_model` has no time dimension. This needs engine changes or another engine. The 2026-09-29 survey found no engine that does it off the shelf. On GraphHopper it is a small custom Java module, see "Build plan if we keep GraphHopper". |

Timesteps are 30 minutes apart, so any option has to decide how to map an arrival time to a timestep: the
step at or before it, the nearest step, or the worse of the two around it. (Superseded by the
fifteen-minute cycle for tiles and the flood histogram; this blocker's own scope is unaffected, but a
future implementation should use 15-minute steps, not 30.)

## Research and build plan (archived)

The research of 2026-09-28, the Option C engine survey, the Valhalla comparison, and the build plan with its tiers are in [[BL-011-research-archive|the archive]]. The decisions they led to are in [[PRD-004-time-aware-routing-engine|PRD-004]] and [[sticky-routing-reference]].

## Baselines on the server, 2026-10-01

Story R1 (`US-046`) records these numbers. Every row except the latency numbers is independent of load and is final until the graph or the image changes. The latency numbers follow the table, measured on 2026-10-02 after `US-037` closed.

| Baseline | Value | Where it comes from |
| -------- | ----- | ------------------- |
| Edge count of `hanoi-model-area.osm.pbf` | 67,833 edges, 51,328 nodes | The `GraphHopper` startup line of `airflow_new-graphhopper-1`, 2026-09-24 08:39 UTC: `edges: 67,833(3MB), nodes: 51,328(1MB)`. The container has run since then, and `GET /info` gives `import_date` 2026-09-23T09:38:29Z. Edge ids run from 0 to 67,832. |
| Table size at that edge count | About 1.1 MB per run | 67,833 edges times 8 steps times 2 bytes. The estimate in [[PRD-003-edge-depth-table|edge-depth-table]] was 36 MB, from a guess of 2 million edges. |
| Image | `israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`, created 2026-06-18T05:28:33Z | `compose.yml`, and `docker image inspect` on the server. |
| Source revision | GraphHopper commit `d7dc1b069d2d091c7cfdc007d99d1765c82e618d` on `master`, committed 2026-06-17T08:35:01Z, "fix: pin jetty version for mitigating CVE-2026-1605 (#3365)", with no local changes | `com/graphhopper/gitinfo` inside `graphhopper-web-12.0-SNAPSHOT.jar`, copied from the running container. The startup line says `version 12.0|2026-06-18T05:27:29Z`. |
| Step length | 15 minutes | `valid_time_utc` in `flood_depth_raster_tile` for the runs `20260930T014500`, `20260930T020000`, and `20261001T183000`. |
| Step count | 8 per run, 105 minutes from the first step to the last | The same runs. Run `20261001T183000` runs from 11:30 to 13:15 UTC. [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] assumed 9 steps over 2 hours. A trip longer than 105 minutes ends after the last step. |
| p50 and p95 of `POST /route` | See "Latency of POST /route, 2026-10-02" below. Flexible mode with LM, motorbike and car, three trips | `scripts/backend_soak/soak_checks.py latency`, run on the server on 2026-10-02. |

### Latency of POST /route, 2026-10-02

`soak_checks.py latency` ran inside `airflow_new-floodmap-backend-1` from 02:39 to 02:49 +07, after `US-037` closed. Each cell is 30 requests, sent one at a time after 3 warm-up requests. The host has 12 CPUs and the pipeline was running, with a load average of 9.7 before and 10.4 after, so the numbers include the load that the live app sees. The flood run is `20261002T023000` and the valid time is `2026-10-02T02:30:00+07:00`. Every request uses flexible mode (`ch.disable: true`) with landmarks, because `config.yml` lists no contraction hierarchy profile. All 30 requests of every cell returned 200.

The trips lie inside the model border. The short trip runs from 21.0250, 105.7550 to 21.0255, 105.7620 and is 1.9 km by road. The medium trip runs from 20.9902, 105.7712 to 20.9815, 105.7952 and is 5.1 km by road for the motorbike and 4.5 km for the car. The long trip runs from 20.9800, 105.7100 to 21.0250, 105.7900. It is 12.2 km by road with no flood model and 16.1 km under the flood model. Under the 2026-10-02 flood, 6 of 13 random pairs of 2.5 to 5 km and none of 6 hand-picked pairs found a safe route, so the medium pair was chosen from the ones that did. Whether a pair routes can change with each run.

Cells hold p50 / p95 in milliseconds.

| Target | Trip | Motorbike | Car |
| ------ | ---- | --------- | --- |
| A. GraphHopper, no flood model | short | 11.2 / 18.3 | 8.0 / 13.9 |
| A. GraphHopper, no flood model | medium | 16.4 / 35.7 | 12.3 / 24.4 |
| A. GraphHopper, no flood model | long | 21.2 / 37.2 | 15.7 / 32.9 |
| B. GraphHopper, flood model of the run | short | 189.1 / 287.5 | 153.1 / 219.4 |
| B. GraphHopper, flood model of the run | medium | 381.5 / 491.5 | 276.9 / 336.1 |
| B. GraphHopper, flood model of the run | long | 1,683.8 / 1,926.4 | 1,856.7 / 2,279.4 |
| C. `floodmap-backend`, areas cached | short | 136.5 / 157.6 | 125.7 / 161.9 |
| C. `floodmap-backend`, areas cached | medium | 222.4 / 241.7 | 158.6 / 185.6 |
| C. `floodmap-backend`, areas cached | long | 1,892.5 / 2,407.7 | 2,759.2 / 3,720.8 |
| D. `floodmap-backend`, areas not cached | short | 1,146.7 / 1,302.5 | 986.6 / 1,181.1 |
| D. `floodmap-backend`, areas not cached | medium | 883.6 / 1,206.9 | 723.2 / 810.6 |
| D. `floodmap-backend`, areas not cached | long | 1,707.5 / 2,165.8 | 3,461.5 / 3,867.6 |

Target A is GraphHopper's own `/route` with no flood model, the cost of the search itself. Target B sends GraphHopper the custom model that the backend builds for the run, which isolates the search cost of the flood areas. Target C is the app's path, `POST /route` on `floodmap-backend`, where the areas come from the 30-second in-process cache. Target D bypasses that cache, so every request derives the areas from PostGIS first.

What the numbers show:

1. The flood model is the cost. On the long trip, GraphHopper takes 21 ms for the motorbike without the model and 1,684 ms with it, about 80 times as long. On the short trip the factor is about 17.
2. Deriving the areas adds 0.6 to 1.0 s on the short and medium trips when the cache misses (target D against target C). The cache hides this cost for repeated requests within 30 seconds.
3. On the long trip the car is slower than the motorbike under the flood in targets B, C, and D, on the same 16.1 km route. The cause was not investigated.
4. A time-aware engine (`US-050`) is measured against target B, since it replaces the flood model, and against target C for what the user waits for. The user sets the acceptable factor ([[PRD-004-time-aware-routing-engine|time-aware-routing-engine]], open question) from these numbers.

The evidence image is `us-046-baselines-check-output.png`, and the raw JSON is `evidence/us-046-latency-raw.json`.

## Questions

1. Which option, or A first and B later? Research above suggests A′ (a time-windowed worst case, not
   flat) over plain A, and against building B at all.
2. What upper bound on trip time should option A (or A′) use?
3. How should the answer show in the UI? For example, "This road floods at 21:40" on the route.

## Related topics

- [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]
- [[US-017-route-forecast-query|route-forecast-query]] and [[US-001-depth-forecast-chart|depth-forecast-chart]]
- [[graphhopper-backend]]

## Status history

- **2026-09-25, open.** Logged at the user's request while working on [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]].
  Routing should use the time the traveller reaches each road.
- **2026-09-28, open.** Researched how production systems and academic literature handle this before
  any implementation choice. See Research above. Still open: the user's decision on which approach to
  build and the trip-time bound.
- **2026-09-29, open.** Added the Option C engine survey (no engine supports it off the shelf, Valhalla
  is the closest partial fit) and a build plan for staying on GraphHopper: Tier A-prime, a decision gate,
  and Tier C-lite. GraphHopper's `Weighting` and `SPTEntry` carry no arrival time, so Option C needs a
  custom module, not a `custom_model`. No approach tried yet.
- **2026-09-29, open.** Added "Valhalla, 2026-09-29". The reason for the 2026-09-08 switch is not recorded
  (commit `6394e27` gives only "embed flood as a cost factor more effectively"). The likeliest cause is that
  Valhalla has no graded area penalty. Adapting Valhalla is possible but not worthwhile, and it does not
  change the Option C answer. The Valhalla proof of concept was deleted in `5d1a606`, so ADR-002's "left on
  disk" needs correcting in `artifacts/raw/`, which the user owns.
- **2026-09-29, open.** The user chose sticky C-lite as the routing option. The reasoning, cost-benefit, and
  roadmap are in [[sticky-c-lite-routing]]. The decision gate was not run. No code is written.
- **2026-09-29, open.** Turned the decision into two PRDs, [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] and
  [[PRD-003-edge-depth-table|edge-depth-table]], with stories in [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] and [[EP-08-edge-depth-table|edge-depth-table-stories]],
  scheduled in [[SP-02-routing-engine-foundations|sprint-plan-2]] and [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. The blocker stays open until the rollout story has evidence.
- **2026-09-30, open.** Checked against the sprint plans. It blocks no story of Sprint 4, and Sprint 5 (2026-10-19) has no dependency on it. The build runs in [[SP-02-routing-engine-foundations|sprint-plan-2]] (Sprints 5 to 8) and [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] (Sprints 9 to 12). The user still has to answer four gates: the soak length and route set for `US-034` before Sprint 5, the sticky-from-departure wording for `US-050` and the build-time limit for `US-045` before Sprint 8, and the latency factor for `US-055` before Sprint 10. The blocker closes when `US-055` has evidence.
- **2026-10-01, open.** The `US-034` gate is cleared: the user set the soak length to 48 hours, and the route set is no longer needed because the Valhalla comparison was dropped (the Valhalla model was wrong when it ran). Three gates remain: the sticky-from-departure wording for `US-050` and the build-time limit for `US-045` before Sprint 8, and the latency factor for `US-055` before Sprint 10.
- **2026-10-01, open.** `US-046` recorded the edge count (67,833), the image's source revision (commit `d7dc1b06`), and the step length and count (15 minutes, 8 steps) in "Baselines on the server". The latency numbers wait for the `US-037` knob. The real step count of 8 differs from the 9 steps that the PRD assumed, so the reference's scenarios now use 8.
- **2026-10-02, open.** `US-046` recorded the p50 and p95 of `POST /route` in "Latency of POST /route, 2026-10-02". GraphHopper alone answers in 8 to 21 ms at the p50, and the flood model raises that to 153 to 1,857 ms. The 30-second area cache hides 0.6 to 1.0 s of PostGIS work. The user can now set the latency factor of the PRD. The blocker stays open.
- **2026-10-02, open.** The user cleared the three gates. The sticky-from-departure wording is confirmed (`US-050`), the build-time limit is set (`US-045`: the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`), and the latency factor is 2 times the baseline (`US-055`). No gate of the build is open. The blocker stays open until the rollout story has evidence.
- **2026-10-05, open.** `US-049` answered the LM question (assumption 5 of [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]). A weighting that only raises edge weights, or closes edges with an infinite weight, keeps the landmark lower bounds valid, so the time-aware search can run with LM. Source: `LMApproximator` states that all routing weights must be larger than or equal to the preparation weights. Test: `LandmarkLowerBoundTest` in `java/time-aware-routing/`, 10 random graphs, with the landmarks prepared on the stock weighting. No LM estimate exceeds the real weight, and LM A* (`astar` and `astarbi`) finds the Dijkstra weight on every pair tried. A control weighting that lowers weights does break the bounds, so the test can fail. The test uses GraphHopper's own random graphs, not the Hanoi graph.
- **2026-10-09, resolved.** `US-055` is `Done` on the engine proof of 2026-10-07 (9 of 24 routes changed, median detour 0.94, 0 routes cross a road closed on arrival, 6 of 6 latency cells within 2 times the baseline) and the table timing of `US-045` (gap 2.69 to 3.91 minutes over 45 runs). The user closed the blocker on 2026-10-09 while `TIME_AWARE_ROUTING` is `false` at rest, so live routing is still single-timestep until the flag goes on. The flag goes on when the DAG runs on real rain, with `rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`. Evidence: `us-055-rollout-results-check-output.png` in `docs/user-stories/evidence/`.
