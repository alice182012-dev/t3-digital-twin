---
date_drafted: 2026-10-13
type: user-story
us_id: "US-142"
title: "Stop the standing-flood chain when the depths stop changing"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P2
estimate: S
sprint: 15
subsystem: airflow-pipeline, 3di-orchestration
source_ideas: []
related: ["[[BL-030-the-standing-flood-rule-never-ends-with-permanent-water|BL-030]]", "[[US-101-keep-simulating-while-the-flood-still-stands|US-101]]", "[[decision-log|D-037]]"]
tags: [user-story]
---

# US-142 Stop the standing-flood chain when the depths stop changing

As the owner of the pipeline, I want the standing-flood chain to stop when the road depths stop changing, so it does not start a real 3Di simulation every slot with no rain.

The rule in `scripts/standing_flood.py` runs while any edge in the newest runs reads 5 cm or more.
The model holds permanent water, so about 157 edges read 5 cm or more in every run, and the chain started on 2026-10-13 at 09:45 UTC did not end ([[BL-030-the-standing-flood-rule-never-ends-with-permanent-water|BL-030]]).
The owner accepts the model's depths and does not want them corrected.
The story changes the stop test to a steady state: the chain stops when no edge changed by more than 1 cm between consecutive runs for 5 runs in a row and no rain is forecast.

Given runs whose depths do not change and a forecast of 0 mm/h, then the gate stops the chain after 5 such runs.
Given a flood that still recedes, then the gate keeps the chain running.
Given the tests, then `python3 -m pytest -q test/` passes.

Dependencies: None. `flood_mapping_full` stays paused until this is deployed or the owner unpauses it for real rain.

## Status history

- **2026-10-13, Ready.** Raised from [[BL-030-the-standing-flood-rule-never-ends-with-permanent-water|BL-030]] when the owner ruled it not a blocker. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]]. The owner decides the unpause of `flood_mapping_full` after it is `Done`.
- **2026-10-14, In progress.** Started with no other story in progress, within the limit of two.
- **2026-10-14, Reviewed.** Built and tested in throwaway containers. It waits for the owner's deploy and the owner's acceptance. The server was not touched.
- **2026-10-14, owner answer.** The rule is kept as built (5 runs with 4 comparisons). Code cannot end the standing flood, because the cause is the initial water of the model. The owner cuts that water out in an experiment in `marie-curie/`, and the work continues later. `flood_mapping_full` stays paused.
- **2026-10-14, superseded.** The owner chose the 5 cm depth test again ([[decision-log|D-053]]) and the steady-state commit was reverted. Items 1 to 4 and 6 below describe code that no longer exists.

## Evidence and details

1. What: `scripts/standing_flood.py` stops the chain when the newest 5 runs are steady and the forecast is 0 (reason `steady_and_no_rain`). It keeps the chain running when depths still change (`depths_changing`), when rain is forecast with 5 steady runs (`rain_forecast`), and when fewer than 5 runs exist. `no_run` and `chain_ended` are unchanged.
2. How: `RunDepth(timestamp, depths_cm, age)` is the typed history, and the pure function `assess(runs_newest_first, max_rain_mm_hr)` decides. `read_standing_flood` reads the newest 5 runs in one query with the deepest depth of each edge per run. Two runs are steady when no edge differs by more than `STEADY_CHANGE_CM` (1.0 cm, and exactly 1.0 is steady). An edge missing from a run counts as 0 cm, and a gap over 30 minutes between runs breaks the count. No edge is filtered, so the permanent-water edges are steady. `dags/flood_mapping_dag.py` lost `DRY_DEPTH_M` and the `FLOOD_DRY_DEPTH_M` variable, which had no other user.
3. Reading of "5 runs in a row": the rule counts 5 runs with 4 comparisons between neighbours, which is the story's own test (5 flat runs stop, 4 flat runs keep going). Reading it as 5 steady comparisons needs 6 runs and is a one-constant change. The owner decides.
4. Tests: `python3 -m pytest -q test/ scripts/` in a GDAL container gave 721 passed, 132 skipped, and 1 failed. The failure is `scripts/test_depth_inputs.py::LocalizeInputTests::test_unwritable_cache_dir_returns_the_source`, because root in a container ignores `chmod`, and it was not run before this change. With a throwaway Postgres 16 and `EDGE_DEPTH_TEST_DSN`, `scripts/test_standing_flood.py` gave 21 passed, including the 4 database tests. The fixture of 157 permanent-water edges is synthetic.
5. Not checked: a run on the server and the real `edge_depth` values. The first check after the deploy is that `flood_mapping_full` ends after 5 runs with `steady_and_no_rain` in its log, and that the 157 permanent-water edges stay within 1 cm between runs.
6. Concept page: [[3di-simulation-orchestration]] describes the new rule, and `last_updated` is 2026-10-14. `FLOOD_DRY_DEPTH_M` is still named in the history of [[US-101-keep-simulating-while-the-flood-still-stands|US-101]] and in `raw/T3-Digital-Twin_Architecture.md`, which stays read-only.
7. Left for `Done`: the owner's deploy on the server and a screenshot of the log or the run list that shows the chain ending.
