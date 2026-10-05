---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-5, sprint-6, us-068, us-034, us-037, us-049]
related: ["[[sprint-plan-2]]", "[[carried-over-backlog]]", "[[sprint-5-baselines-reference-format-and-soak]]", "[[sprint-6-java-toolchain-and-edge-export]]", "[[us-037-narrow-the-per-run-critical-path]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[2026-10-05]]"]
---

# Plan: 2026-10-05, build US-068 and settle what still blocks Sprint 6

## Context

Sprint 5 started on 2026-10-01. Nine of its eleven rows are `Done`. The open ones are `US-034` and the new `US-068`, and a Sprint 4 carry-over, `US-037`, also gates Sprint 6.

- `US-034` (the 48-hour soak) is `In progress`. Its window was 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07. The replay behind it ([[us-063-realistic-rain-replay-for-us-037-and-us-034]]) stopped at 137 of 192 runs, and the last run began at 2026-10-03 19:00 UTC. The disk-full incident of 2026-10-04 cut the rest ([[docker-data-vhdx-fills-c-drive-again]], now `resolved`). No record shows that the end check of `run_soak.sh` ran.
- `US-037` (the per-run critical path, a Sprint 4 carry-over) is `Active` in the Backlog. Its own pass check, `scripts/pipeline_margins/report.py`, has not run over the window. `9_build_flood_tiles` grew 4.8 times over the 48 hours, and the unverified lead is `flood_extent_polygon`, which had no retention until `US-067` landed today.

`flood_mapping_full` is paused, and unpausing it is the user's decision. [[sprint-6-java-toolchain-and-edge-export]] says Sprint 6 starts when `US-034`, `US-037`, and `US-063` are `Done`, so these two items gate it. No blocker stops Sprint 6 build ([[routing-not-time-aware]] is the problem Sprints 6 to 10 solve).

`US-068` (the `rain_ingested` XCom of `1_trigger_simulation`) is new today, in Sprint 5, size S, with no dependency.

## Order of work

Items 1 to 3 need no server and can start now. Item 4 needs the user.

1. **Build `US-068`.** Tests first, with a pure summary function over the `[offset_seconds, m/s]` list that `build_rain_values` returns. Then add the push to `task_run_simulation` in `dags/flood_mapping_dag.py`, and the source label in `get_rain_forecast`. Done when the tests pass and the story has a screenshot of a real XCom (needs one run on the server, so the story stays `Reviewed` until then).
2. **Check the `US-037` lead from code.** Read `task_build_flood_tiles` and the tile query it calls. If it reads `flood_extent_polygon`, the 4.8 times growth is explained, and the retest after `US-067` is the check. If it does not, the lead is dead and the growth needs another cause. Record the answer in [[us-037-narrow-the-per-run-critical-path]].
3. **Start `US-049` on the Mac.** Write the Java module files, the `Dockerfile`, and `.github/workflows/java-module.yml` with no build, as [[sprint-6-java-toolchain-and-edge-export]] describes for the days before Sprint 6 starts. The first CI run needs the user's approval to push.
4. **Ask the user to choose how to close `US-034` and `US-037`.** The choice is below.

## Decision for the user

The 137-run window is not the 192 runs the stories were written against. Pick one.

- **Re-run the replay.** Unpause `flood_mapping_full` with the retention fixes in place, run the full 48 hours, then run `run_soak.sh` and `report.py`. This costs two more days and keeps both stories honest. Sprint 6 then starts about 2026-10-08.
- **Accept 137 runs.** Run `report.py` and the end check over the window that exists, and close both stories with the shortfall written into their Details. Sprint 6 starts as soon as the checks pass. `US-063` was already closed this way, as a flagged judgment call.

My recommendation is to re-run, because `US-037` is judged on a growth trend (the tile task over time), and a window cut short by an incident cannot show whether the trend was the missing retention or something else. A re-run also exercises `US-066` and `US-067` under real load, which nothing has done yet.

## Not today

- No `TODOS.md` edit. `US-068` is already there. Sprint 6 rows enter `TODOS.md` only when Sprint 6 starts (rule 9).
- No item for [[place-name-slow-after-map-tap]] (`US-061` has no sprint) or the open frontend blockers.

## Status history

- **2026-10-05, active.** Written after `/refresh-artifacts`. Waiting on the user's choice between a re-run and accepting the 137-run window.
