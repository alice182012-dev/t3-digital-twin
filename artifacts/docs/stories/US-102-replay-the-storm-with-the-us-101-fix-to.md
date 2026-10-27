---
date_drafted: 2026-10-10
type: user-story
us_id: "US-102"
title: "Replay the storm with the US-101 fix to close BL-028"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
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

Given the storm file `hanoi_20260916_storm.csv` and the `US-101` rule, when the replay runs on the server for about 13.5 hours, then no run between the first and the last simulating run is skipped while the previous table has edges at or above the depth floor, the first run after any quiet stretch logs a hotstart and not "No saved state", and the table after the quiet stretch holds a wet-edge count close to the forecast of the table before it.

Dependencies: none open.
The product owner gives the go before the replay starts, because it holds the server for about 13.5 hours.
The steps: run `replay.ps1 stop`, raise `FLOOD_EXTENT_KEEP_RUNS` (about 60) so `US-091` can use the same replay, start the replay again, and unpause `flood_mapping_full`.
`US-089` is the story that owns `replay.ps1`.

## Status history

- **2026-10-10, ready.** Written at the Scrum adoption ([[decision-log|D-024]]), because `US-101` reached `Done` without the replay its acceptance check names, and `BL-028` stays `monitoring` until the replay.
  Moves the open step "next action 2" of the old `TODOS.md` into a story.
- **2026-10-10, estimate M to S.** Compared with US-063 and US-069 (S each: run a replay, read the result).
  The effort is small and the wait is long.
  The extra check of the gap tables and the hotstart line does not change the size.
- **2026-10-10, done.** The product owner gave the go, and the replay ran from 04:45 to about 18:15 +07 on 2026-10-10.
  The replay stopped at 18:49 +07 (see [[US-089-start-and-stop-a-rain-replay-on|US-089]]).
  The details list what the replay showed and the two clauses it did not exercise.

## Evidence and details

**Evidence:** rendered output of `evidence/us-102-replay-check.sh`, a read-only check of the replay, captured 2026-10-10 18:23 to 18:27 +07 from the Mac against the server.

![[us-102-replay-check-output.png|900]]

**Details:**

1. The run was one replay of the 2026-09-16 storm (`hanoi_20260916_storm.csv`) on the server, started with `replay.ps1 start` and a 5 mm/h gate.
   The replay rain started at 04:45 +07.
   It made 55 runs, one per 15-minute slot from 04:45 to 18:15 +07, and all 55 ended `success`.
   No slot was skipped.
2. The procedure differed from the steps above. The replay started without a prior `stop`, as step 4 of SPR-013 required. The server `.env` set `FLOOD_EXTENT_KEEP_RUNS=100`, `EDGE_TABLE_KEEP_RUNS=100`, and `ARCHIVE_HOST_PATH=D:/airflow_new_data/archive`.
3. The flood still stood when the replay stopped. The last gate-passing run was at 16:00 +07, and the 9 runs after it (16:15 to 18:15 +07) simulated because the standing-flood rule of [[US-101-keep-simulating-while-the-flood-still-stands|US-101]] keeps a slot running while the flood stands.
4. The gate alone would have skipped 4 of the 46 slots from 04:45 to 16:00 +07, because 42 of 46 pass the gate (the output of `replay.ps1 start`). All of those slots ran.
5. The trigger logs of 04:15 to 18:15 +07, 57 in all, hold `[Hotstart, exact]`, and no log holds `[Coldstart]`.
   The 04:00 run, the first of the chain, logged neither line, and the chain check forced its cold start. Because no log holds `[Coldstart]`, none holds `[Coldstart] No saved state`.
6. The 7 slots at event offsets 360 to 450 minutes (10:45 to 12:15 +07) are the window of the second replay's gap ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]). All 7 logged `[Hotstart, exact]`.
7. For each of those 7 slots, the wet-edge count (depth of 1 cm or more) at the first step of the run is 0.8 to 1.25 times the previous run's forecast for that time (7 of 7).
   Across the replay, 53 of 53 consecutive tables from 05:15 to 18:15 +07 are inside the same band.
   The band is the one proposed in SPR-013 (open decision 4).
8. Two clauses were not exercised. The Given clause "the first run after any quiet stretch" was not tested, because no slot was skipped, so no quiet stretch occurred. Item 6 is the check that SPR-013 proposed in its place. The stop clause (five dry runs under 5 cm and rain 0) was not exercised, because the flood still stood when the replay stopped.
9. The Given said "about 12 hours", and the replay ran about 13.5 hours. The Dependencies line had the same figure, so both now say 13.5 hours.
10. The raw files are on the Mac in `marie-curie/us-102/` (git-ignored): `evidence/us102_evidence.txt`, `us102_check_final.txt`, `continuity_whole_replay.txt`, and `bl023_samples.log`.
11. The replay closes [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]. It is the data source of the single-timestep stages of [[US-091-measure-how-often-a-single-timestep-route|US-091]], and the demo peak step of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] (D-030).
