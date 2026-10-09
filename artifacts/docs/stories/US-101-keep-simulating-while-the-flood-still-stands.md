---
date_drafted: 2026-10-10
type: user-story
us_id: "US-101"
story_label: "3"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: M
sprint: 12
subsystem: flood-pipeline
related: ["[[EP-12-core-output-hygiene]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]]", "[[3di-simulation-orchestration]]", "[[US-092-test-how-the-vehicle-limits-change-the]]", "[[US-093-measure-how-often-the-sticky-rule-gives]]"]
title: "Keep simulating while the flood still stands after the rain stops"
---

# US-101 Keep simulating while the flood still stands after the rain stops

As the owner of the flood-routing product, I want `flood_mapping_full` to keep simulating and publishing depths for as long as the flood stands on the roads, so the routing engine and the frontend never show a stale or too-dry flood after the rain eases.
Given a storm whose forecast rain falls below the gate (5 mm/h) while roads still hold water, when `flood_mapping_full` runs for each later 15-minute slot, then every slot produces depth tiles, a flood extent, and an edge depth table until the newest 5 runs are under 5 cm and no rain is forecast, and the first run after a quiet stretch hotstarts from the saved state of the last run instead of starting cold.
The mechanism and the evidence are in [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]].
In the second replay of 2026-10-09, four runs (19:30 to 20:15 +07) were skipped at forecast maxima of 3.57 to 4.52 mm/h, the next run started cold, and the table after the gap held about 70 percent fewer wet edges than the forecast of the table before it.
Dependencies: none open.
The user chose the rule on 2026-10-10: the gate applies only from a dry state, and the simulation runs until the newest 5 runs of `flood_road_values` are under 5 cm and the forecast rain is 0.
The test of the fix needs a replay with a rain gap inside a storm, which the storm file `hanoi_20260916_storm.csv` already has.
Acceptance check: replay the same storm with the fix.
No run between the first and the last simulating run is skipped while the previous table still has edges at or above the depth floor.
The first run after any quiet stretch logs a hotstart, not "No saved state".
The tables of the gap exist, and the table after the gap has a wet-edge count close to the forecast of the table before it.
Evidence: None yet.
A story reaches `Done` only with a screenshot of the replay output that shows the gap tables and the hotstart line, plus the numbered details list (rule 8).
Blocker tracking: [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]].

## Status history

- **2026-10-10, not started.** Written from the user's instruction to log the four skipped runs as a P0 blocker.
  The gate stops the simulation while the flood stands, and the next run starts cold.
  The fix waits for the user's choice among the three options in the blocker.
  The final runs of `US-092` and `US-093` wait for this story.
- **2026-10-10, reviewed.** Built locally on `modular`, not committed and not on the server.
  `scripts/standing_flood.py` holds the rule, `task_check_forecast_rain` calls it when the forecast is under the threshold, and `FLOOD_DRY_DEPTH_M` (default 0.05 m) sets the depth floor.
  12 unit tests and 3 gate tests pass, and the same 6 tests in `test/test_flood_rain_gate.py` fail as before the change.
  The story reaches `Done` after a replay of the storm with the fix, with the evidence named in the acceptance check.
  See the concerns in [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]].
- **2026-10-10, done.** Saved as `Done` at the user's request.
  The acceptance check names a replay of the storm with the fix, and that replay has not run, so the evidence here is the test output.
  `BL-028` stays `monitoring` until the replay.

## Evidence and details

**Evidence:** rendered output of `evidence/us-101-gate-check.sh`, captured at 01:29:28 +07 on 2026-10-10 on the Mac (not the server), commit `5f115f4`.

![[us-101-gate-check-output.png|900]]

**Details:**

1. Built: a rule that keeps `flood_mapping_full` simulating while the flood stands.
   `scripts/standing_flood.py` holds the rule and the query, and `task_check_forecast_rain` in `dags/flood_mapping_dag.py` calls it when the forecast is under 5 mm/h.
   `FLOOD_DRY_DEPTH_M` (default 0.05 m) sets the depth floor.
2. How: from a dry state the 5 mm/h gate still decides.
   Once runs exist, the simulation runs every slot until the newest 5 runs of `flood_road_values` are all under 5 cm and the forecast rain is 0.
   A run counts as in progress while the newest is under 45 minutes old and runs are 30 minutes apart or less.
   12 unit tests and 3 gate tests pass.
   6 tests in `test/test_flood_rain_gate.py` fail, and they failed the same way before the change.
3. Why: in the second replay the gate skipped 4 runs (19:30 to 20:15 +07, forecast 3.57 to 4.52 mm/h) while roads held up to 6.5 m of water, no tables were made, and the next run cold-started with 70 percent fewer wet edges (see [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]]).
4. What it changes: the final runs of `US-092` and `US-093` and the replay with the fix wait for the pull on the server.
   The merge with the `US-095` branch is clean.
   The simulation can stay on while the model keeps water above 5 cm, which the user accepted as a model issue.
   The core DAG now reads `flood_road_values`, written by `routing_adapter`.
