---
date_open: 2026-10-10
date_closed: 
type: blocker
status: monitoring
severity: P0
subsystem: flood-pipeline
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, rain-gate, hotstart, flood-mapping-full, replay, us-101]
related: ["[[US-101-keep-simulating-while-the-flood-still-stands]]", "[[EP-12-core-output-hygiene|core-output-hygiene-stories]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[3di-simulation-orchestration]]", "[[2026-10-10]]", "[[US-092-test-how-the-vehicle-limits-change-the]]", "[[US-093-measure-how-often-the-sticky-rule-gives]]", "[[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]"]
last_updated: 2026-10-10
---

# rain-gate-stops-simulation-while-the-flood-still-stands

## Description

`flood_mapping_full` stops simulating when the rain forecast drops below the gate, even while the flood from the earlier rain is still on the roads. A storm does not end when the rain does. The water stays for hours, and the routing engine and the frontend need depths for all of that time.

The mechanism, with the code that does it:

1. `task_check_forecast_rain` (`dags/flood_mapping_dag.py:96`) calls `evaluate_rain_gate` (`scripts/create_simulation.py:178`). The gate returns `should_run` only when the highest forecast intensity in the lookahead window, counted from the run's slot, is at least `FLOOD_RAIN_THRESHOLD_MM_HR` (5 mm/h). The gate reads forecast rain and nothing else. It does not read the water that is already on the roads.
2. When `should_run` is false, the branch returns `None`. Every later task (`1_trigger_simulation`, `2_download_results`, `3_calculate_depth`, `9b_load_depth_raster`, `9_build_flood_tiles`) is `skipped`, and the DAG run ends as `success`. No depth tiles, no flood extent, and no edge depth table are made for that slot.
3. `routing_adapter` triggers on the new tiles, so it does not run either. `latest` in the edge depth folder keeps pointing at the last table made before the skip. The routing engine and the frontend serve that table while the flood goes on.
4. The model state is lost. The first run after a skip calls `1_trigger_simulation`, and its chain check counts the skipped run as `success`, so it prints "hotstart allowed". The saved-state search then finds no state within 30 minutes and starts cold from a dry model.

What happened in the second replay on 2026-10-09:

- The four runs at 12:30, 12:45, 13:00, and 13:15 Z (19:30 to 20:15 +07) logged forecast maxima of 4.52, 4.52, 3.57, and 3.57 mm/h, under the 5 mm/h gate. Each run took about 4 seconds, and all of its tasks after `0_check_forecast_rain` were `skipped`. The tables `20261009T194500`, `20261009T200000`, `20261009T201500`, and `20261009T203000` were never made.
- The run at 13:30 Z logged "Chain check: hotstart allowed, 1 success or running run(s) at previous slot 2026-10-09T13:15:00Z" and then "No saved state within 0:30:00 before 2026-10-09T13:30:00Z", so it started cold.
- The last table before the gap, `20261009T193000`, forecast 3,939 road edges with water, 1,614 edges at 20 cm or more, and a maximum of 656 cm at 13:45 Z. The first table after the gap, `20261009T204500`, shows 1,185 edges with water, 254 at 20 cm or more, and a maximum of 310 cm for the same time, 13:45 Z. The cold start lost about 70 percent of the wet edges and 84 percent of the edges at 20 cm or more. The data is in `marie-curie/edge_tables_replay2_final_2026-10-10/`, and the query is in [[2026-10-10]].

The size of the loss is not proven. A continuous run would also drain some of this water over 75 minutes, and no continuous run exists to compare with. The numbers show the size of the step at the gap, not the exact error.

## Plain-language explanation

**The picture.** It rains hard over a city for hours. The streets fill with water. Then the rain eases off, but the water stays on the streets for a long time, because it drains slowly.

**What the program does.** Every 15 minutes the program asks the weather service, "will it rain hard in the next while?". If the answer is no, the program stops working out where the water is. It does not ask "is there still water on the streets?".

**Why that is wrong.** The traveller needs to know where the water is, not where the rain is. For the hours when the rain is light and the streets are still wet, the program shows the old picture, and then it throws away what it knew about the water. When it starts again, it believes the streets are dry and has to fill them up again, so the picture is too dry for a long time.

## Why this matters

This is P0 because the routing product advises people during a flood.

- During a real storm, the app would show a stale flood picture for every slot after the rain falls under the gate, and then a too-dry one after the gate opens again. A route could cross a road that is still under water.
- It breaks the time-aware routing built in Sprints 9 to 11. The engine reads the edge depth table, and the table is missing for these slots.
- In the second replay, the storm stages of `US-091`, `US-092`, and `US-093` read these tables. The second chain starts from a dry model at 20:30 +07, and the 4 tables are missing from the sample. A result for the whole storm is not valid until the question of the cold start is settled.
- The earlier decision to leave the gate unchanged ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], Risks) was about waiting for real rain to prove `US-094`. It did not cover the question of stopping in the middle of a storm, so it does not apply here.

Under the blocker rules in `.claude/CLAUDE.md` (rule 11), the case is as follows. The fix does not change code that Sprint 13 ([[SP-04-frontend-recheck|sprint-plan-4]], the frontend recheck) builds on, so a subagent in its own worktree could fix it while Sprint 13 continues. Because the severity is P0 and the final runs of `US-092` and `US-093` read data affected by it, the fix is the first row of Sprint 12 and those final runs wait for it. The user decides whether this reading holds.

## Approaches tried

### Approach 1

The user chose the rule (see the next section) and it is built on `modular` (the commit "Keep simulating while the flood still stands on the roads"): `scripts/standing_flood.py` (the rule and the query), `scripts/test_standing_flood.py` (12 tests), and a change to `task_check_forecast_rain` in `dags/flood_mapping_dag.py`, with 3 gate tests in `test/test_flood_mapping_dag_graph.py`. Results:

- All 12 tests in `scripts/test_standing_flood.py` pass, and the 3 gate tests pass. 6 tests in `test/test_flood_rain_gate.py` fail, and they failed the same way before the change (`git stash` comparison).
- The query ran against the real tables of the second replay (read-only). At the first skipped slot (12:30 Z, forecast 4.52 mm/h) the newest runs hold a deepest value of about 6.5 m, so the rule says continue. The later skipped slots cannot be replayed from history, because the skipped runs never wrote the runs that keep the chain alive.
- Not run on the server. The DAG file and the new module need a pull there, and the check is a replay with a rain gap inside the storm.

## Decision and explanation

Decided by the user on 2026-10-10. The 5 mm/h rain gate decides only from a dry state. Once runs exist, `flood_mapping_full` simulates every slot, whatever the forecast, until two things hold together: the newest 5 runs of `flood_road_values` all have a deepest value under 5 cm, and the forecast rain is 0. A run counts as in progress while the newest run is under 45 minutes old and consecutive runs are 30 minutes apart or less. This is option A (gate on standing water) with a depth floor of 5 cm (`FLOOD_DRY_DEPTH_M`, in metres) and a hold-down of 5 dry runs, which is 75 minutes.

Options B (a fixed hold-down time) and C (a lower rain threshold while the flood stands) were not chosen. Option A reads the actual water, so it follows the real storm instead of a guessed number of hours.

## Concerns

- `flood_road_values` is written by `routing_adapter`, not by `flood_mapping_full`. If `routing_adapter` stops for more than 45 minutes in a storm, the newest run is too old and the gate ends the chain. The user accepted this on 2026-10-10: the check must read the flood on the roads only, and `flood_road_values` is that table. The tables that `flood_mapping_full` writes itself (`flood_extent_polygon`, `flood_depth_raster_tile`) cover every area, not only roads. A run of `routing_adapter` takes about 3 to 4 minutes after `9b`, so a normal slot is well inside the limit.
- The deepest value over all roads is a strict measure, and a slow-draining pond keeps the simulation on past 5 cm. The user accepted this on 2026-10-10: a model that never drains is a model issue, not a backend issue, so the rule stays as it is.
- `scripts/rain_replay.py` (line 153) predicts which slots the gate lets through, with the forecast test only. It does not know about standing flood, so its prediction of skipped slots is out of date.
- The chain check in `task_run_simulation` still counts a skipped run as `success`. After this fix a skip happens only in a dry state, where a cold start is correct, but its "hotstart allowed" message can still mislead.
- The sample for the paper experiments has a one-hour gap and a cold start. Any rate computed from it must name both, until a repeated replay replaces it.
- The replay uses its own rain file (`FLOOD_TEST_RAIN_CSV`). A fix that reads the standing water must work on replay data and on Tomorrow.io data.
- Simulating longer costs disk and time (`3_calculate_depth` and `9c` both grow with the number of runs). Read the storage numbers of `US-069` again after the fix.

### Why not read the extent or raster tables

The tables that `flood_mapping_full` writes itself (`flood_extent_polygon`, `flood_depth_raster_tile`) hold depth over the whole model area, so a stop rule on them would mean "no flood anywhere". It would stop later than "no flood on the road", because water stays in fields and ponds after the roads are dry. A road-only reading needs the overlay of depth on road segments, which is `flood_on_roads` and fills `flood_road_values`. So `flood_road_values` stays the source of the stop rule. A run-in-progress check (is the newest run under 45 minutes old) could read a core table instead, but the user accepted the dependency and no change was made.

## Related topics

- [[US-101-keep-simulating-while-the-flood-still-stands]]
- [[3di-simulation-orchestration]]
- [[2026-10-10]]

## Status history

- **2026-10-10, monitoring.** The user decided the rule: the gate applies only from a dry state, and the simulation then runs until the newest 5 runs of `flood_road_values` are under 5 cm and the forecast rain is 0. Built locally (approach 1), tests pass, not yet run on the server. The blocker becomes `resolved` after a replay with a rain gap inside a storm shows no skipped slot and a hotstart after the gap.
- **2026-10-10, open.** Logged at the user's request, as P0, after the second replay. First read as a gate working as designed ("not a fault", [[2026-10-10]]). The user corrected this: a storm still floods after the rain stops, so a gate that stops the simulation is the fault. The mechanism is in the Description, from `dags/flood_mapping_dag.py`, `scripts/create_simulation.py`, `scripts/hotstart_policy.py`, and the Airflow task logs of 2026-10-09. Story: [[US-101-keep-simulating-while-the-flood-still-stands]], Sprint 12.
- **2026-10-10, monitoring.** The user accepted the two concerns: the simulation may stay on while the model keeps water above 5 cm (a model issue), and the check reads `flood_road_values` because it must look at roads only. No change to the code.
- **2026-10-10, monitoring.** `US-101` is `Done` on test evidence, and `flood_mapping_full` was paused at 01:29 +07. The blocker stays `monitoring` until a replay with a rain gap inside a storm shows no skipped slot and a hotstart after the gap.
- **2026-10-10, monitoring.** The Scope A replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] ran on the server from 04:02 to 18:17 +07, with a forecast gap at 10:45 to 11:30 +07.
  At 10:45 +07 the gate read 4.52 mm/h, and the standing-flood rule let the run go ahead.
  No slot from 10:45 to 12:15 +07 was skipped, and each logged a hotstart.
  The wet-edge ratio is 1.00 for all 53 consecutive pairs of tables in the run, against 0.30 in replay 2.
  The numbers and the image are in US-102.
  The proposed band of 0.8 to 1.25 is not decided by the owner.
  The stop clause (five dry runs under 5 cm and no rain) was not exercised, because at hour 11.5 the newest table still forecast 3,680 edges at 5 cm or more.
  The blocker stays `monitoring`, and it can move to `resolved` when the owner accepts the replay at the review.
