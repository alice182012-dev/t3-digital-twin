# TODOS

## Current sprint: Sprints 9 to 12, 2026-10-05 to 2026-12-13

## Next action:
1. Read the final runs of `US-092` and `US-093` (started 01:49 +07 on 2026-10-10, 45 tables). Each result must name the one-hour gap (19:30 to 20:15 +07) and the cold start at 20:30 +07.
2. **P0, `BL-028`:** replay the storm with the `US-101` fix (about 12 hours). Run `replay.ps1 stop`, raise `FLOOD_EXTENT_KEEP_RUNS` (about 60) so `US-091` can use the same replay, start again, and unpause `flood_mapping_full`. It needs your go.
3. Decide what to do about the growth of `9c` within a chain ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]], 46 s to 96 s, cause unknown), or leave the blocker at `monitoring`.
4. `US-094` waits for a real Tomorrow.io forecast above 5 mm/h. Recreate the Airflow containers on the server first, so the archive mount exists.
5. Decide whether `TIME_AWARE_ROUTING` goes on for good (`rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in `.env`), best with the DAG running on real rain. The flag is off now.
6. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]]: answer the cost limit and pair count (proposal: 30 pairs, 2 hours). The exact-enough bar is 97 percent per vehicle.

### Active - US-094 Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain

**Story:** [[US-094-archive-results-3di-nc-and-a-run|US-094]], P1, Sprint 10 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
**Status:** `Reviewed`. The task is deployed with the DAG (tests pass). The proof needs a real forecast above 5 mm/h, and the archive mount needs the Airflow containers recreated.
**Next:** next action 4.

### Active - US-089 Start and stop a rain replay on the server with one command each

**Story:** [[US-089-start-and-stop-a-rain-replay-on|US-089]], P1, Sprint 12 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
**Status:** `Reviewed`. `start` ran twice (2026-10-08 and 2026-10-09). `stop` has not run.
**Next:** run `replay.ps1 stop` after the replay of next action 2, then take the screenshot.

### Active - US-091 Measure how often a single-timestep route meets a closed road on arrival

**Story:** [[US-091-measure-how-often-a-single-timestep-route|US-091]], P1, Sprint 12 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
**Status:** `In progress`. The harness is built. A preliminary run on the last 8 runs of the second replay is done (8.0 percent of single-timestep routes meet a closed road on arrival, late storm only).
**Next:** the cold-start, one-hour, and three-hour stages and the sticky engine check need the replay of next action 2.

### Active - US-092 Test how the vehicle limits change the result

**Story:** [[US-092-test-how-the-vehicle-limits-change-the|US-092]], P2, Sprint 12 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
**Blocker tracking:** [[BL-024-edge-export-has-no-node-ids|BL-024]] and [[BL-025-engine-has-no-depth-band-cost|BL-025]], both `resolved`.
**Status:** `In progress`. The final run on the 45 tables of the second replay started at 01:49 +07 on 2026-10-10.
**Next:** next action 1.

### Active - US-093 Measure how often the sticky rule gives no route or a longer route than an arrival-only reference

**Story:** [[US-093-measure-how-often-the-sticky-rule-gives|US-093]], P2, Sprint 12 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
**Blocker tracking:** [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]].
**Status:** `In progress`. The final run on the 45 tables started at 01:49 +07 on 2026-10-10. The bar is 97 percent of searches exact per vehicle.
**Next:** next action 1.

### Done - US-070 Stop a slow sampling step from holding the database

**Story:** [[US-070-stop-a-slow-sampling-step-from-holding|US-070]]. **Blocker tracking:** [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]], `monitoring`.
**Result:** no run of 92 reached the 120 s cancel.

### Done - US-086 Prune old rows of `flood_road_values`

**Story:** [[US-086-prune-old-rows-of-flood-road-values|US-086]].
**Result:** the prune ran 45 times inside Airflow and the table holds 24 hours.

### Done - US-100 Decide between option A closure and sticky closure for a vehicle already on the route

**Story:** [[US-100-decide-between-option-a-and-sticky-closure|US-100]]. **Blocker tracking:** [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]].
**Result:** the engine keeps sticky closure ([[decision-log|D-023]]).

## Backlog

No unfinished item is carried over from Sprint 8.

## Blockers for the next sprint

The next sprint is Sprint 13, planned for 2026-12-14 to 2026-12-20 in [[SP-04-frontend-recheck|sprint-plan-4]]. Its rows enter this file when the sprint starts, not before (rule 9).

Any blocker stops Sprint 13: None known. Sprint 13 is the frontend recheck, which reads no open blocker below except [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]] and [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]], both monitoring.

The unresolved blockers are:

1. [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]], monitoring.
2. [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]], monitoring.
3. [[BL-011-routing-not-time-aware|routing-not-time-aware]], which `US-055` resolves.
4. [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]], monitoring, fixed in code by `US-070`. It blocks no build.
5. [[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]], which blocks no build. Its story `US-061` has no sprint.
6. [[BL-026-sticky-closure-clock-anchored-at-floored-departure|sticky-closure-clock-anchored-at-floored-departure]], monitoring, fixed in code by `US-096`. It resolves after the next rollout rebuilds the `graphhopper` image. It blocks no build.
7. [[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]], `resolved` by D-021 on 2026-10-09.
8. [[BL-024-edge-export-has-no-node-ids|edge-export-has-no-node-ids]], `resolved` on 2026-10-09. The second replay is over, and the real-graph run of `US-092` and `US-093` waits for your choice in next action 1.
9. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], open. It blocks only `US-093` and blocks no build in Sprint 13. The fix waits for your decision on the definition of the reference.
10. [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|rain-gate-stops-simulation-while-the-flood-still-stands]], P0, monitoring, fixed in code by `US-101` and deployed on the server. It resolves after a replay of the storm with the fix. It blocks no build in Sprint 13.
