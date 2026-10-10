---
date_drafted: 2026-10-10
type: user-story
us_id: "US-102"
title: "Replay the storm with the US-101 fix to close BL-028"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P0
estimate: S
sprint: 
subsystem: flood-pipeline
source_ideas: []
related: ["[[US-101-keep-simulating-while-the-flood-still-stands]]", "[[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]]", "[[US-089-start-and-stop-a-rain-replay-on]]", "[[US-091-measure-how-often-a-single-timestep-route]]"]
tags: [user-story, replay, p0]
---

# US-102 Replay the storm with the US-101 fix to close BL-028

As the owner of the flood-routing product, I want a full replay of the 2026-09-16 storm with the `US-101` rule, so I know the pipeline keeps simulating while the flood stands and `BL-028` can close.

Given the storm file `hanoi_20260916_storm.csv` and the `US-101` rule, when the replay runs on the server for about 12 hours, then no run between the first and the last simulating run is skipped while the previous table has edges at or above the depth floor, the first run after any quiet stretch logs a hotstart and not "No saved state", and the table after the quiet stretch holds a wet-edge count close to the forecast of the table before it.

Dependencies: none open.
The product owner gives the go before the replay starts, because it holds the server for about 12 hours.
The steps: run `replay.ps1 stop`, raise `FLOOD_EXTENT_KEEP_RUNS` (about 60) so `US-091` can use the same replay, start the replay again, and unpause `flood_mapping_full`.
`US-089` is the story that owns `replay.ps1`.

## Status history

- **2026-10-10, ready.** Written at the Scrum adoption ([[decision-log|D-024]]), because `US-101` reached `Done` without the replay its acceptance check names, and `BL-028` stays `monitoring` until the replay.
  Moves the open step "next action 2" of the old `TODOS.md` into a story.
- **2026-10-10, estimate M to S.** Compared with US-063 and US-069 (S each: run a replay, read the result).
  The effort is small and the wait is long.
  The extra check of the gap tables and the hotstart line does not change the size.

- **2026-10-10, reviewed.** The Scope A replay ran on the server, and the story is built and measured, not accepted.
  The owner accepts at the review.
  The full storm, `scripts/rain_events/hanoi_20260916_storm.csv`, ran with the gate at 5 mm/h from the replay start slot 04:45 +07 (2026-10-09T21:45:00Z).
  `flood_mapping_full` was unpaused at 04:02 +07 and paused at 18:17 +07, which is hour 13.5 of the replay, as the owner planned.
- **2026-10-10, reviewed.** The acceptance text says "about 12 hours", and that is wrong, because the flood outlasts the rain.
  The owner decides whether to change the wording.
  The stop clause (five dry runs under 5 cm and no rain) was not exercised, see the details below.
- **2026-10-10, reviewed.** The run used `FLOOD_EXTENT_KEEP_RUNS=100`, where the story text says about 60.
  The server `.env` held `EDGE_TABLE_KEEP_RUNS=100` and `ARCHIVE_HOST_PATH=D:/airflow_new_data/archive`.
  Two code changes were needed during the run, and the first is that `compose.yml` reads `EDGE_TABLE_KEEP_RUNS` from `.env` (default 60).
  The second is in the harness of [[US-091-measure-how-often-a-single-timestep-route]].
- **2026-10-10, reviewed.** The gap slots, 10:45 to 11:30 +07, had a forecast maximum under 5 mm/h.
  At 10:45 +07 the gate read 4.52 mm/h, and the run went ahead because of standing flood.
  No slot from 10:45 to 12:15 +07 was skipped, and each logged a hotstart.
  Replay 2 skipped four slots at 19:30 to 20:15 +07 and cold-started after them, see [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]].
- **2026-10-10, reviewed.** Across the run, 55 triggers succeeded after the replay start, none was skipped, and no task failed.
  `routing_adapter` was never more than 15 minutes behind, and C: free space never fell below 99.3 GiB.

## Evidence and details

The image is rendered output, not a live screenshot.

![[us-102-replay-check-output.png|900]]

Rendered output of `us-102-replay-check.sh` and two read-only checks, captured 2026-10-10 18:23 to 18:27 +07 on gods-macbook.local (the Mac), against the server 100.67.84.55.

Still missing for `Done`: the owner's acceptance, the owner's decision on the proposed band of 0.8 to 1.25, and a check of the stop clause, which this replay did not reach.
The image was made on the Mac and reads the server, so the owner decides whether it meets the acceptance check, which names the server.

1. What was built: the check `artifacts/docs/stories/evidence/us-102-replay-check.sh`, and `scripts/edge_depth/gap_continuity.py` with 6 tests, which computes the wet-edge ratio.
2. How: a wet edge is an edge with a depth of 1 cm or more.
   The ratio compares the first step of each run with the forecast of the previous run for the same step.
   The check also reads the trigger log of every run for a hotstart or a cold start line.
3. Why: replay 2 gave a ratio of 0.30, with 1,185 wet edges against 3,939 before the gap, so the ratio shows the size of the loss at a gap.
4. Result: the ratio is 1.00 for all 53 consecutive pairs of tables from 20261010T050000 to 20261010T181500.
   The tables from 20261010T104500 to 20261010T121500 hold 4,054, 4,067, 4,052, 4,037, 3,998, 3,950, and 3,912 wet edges, and each has a ratio of 1.00.
   Of 58 trigger logs, 57 show a hotstart, none shows a cold start, and one is the forced cold start of the first run (simulation 451782).
   At hour 11.5 the newest table forecast 3,680 edges at 5 cm or more, with a maximum of 670 cm, so the flood still stood.
5. What it changes: BL-028 can resolve when the owner accepts this replay.
   The band of 0.8 to 1.25 is proposed, and the owner has not decided it.
   US-091 depends on this replay, because its storm stages read these tables.
