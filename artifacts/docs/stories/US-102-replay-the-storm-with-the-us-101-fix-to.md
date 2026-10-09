---
date_drafted: 2026-10-10
type: user-story
us_id: "US-102"
title: "Replay the storm with the US-101 fix to close BL-028"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Ready
kind: story
priority: P0
estimate: M
sprint: 
subsystem: flood-pipeline
source_ideas: []
related: ["[[US-101-keep-simulating-while-the-flood-still-stands]]", "[[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands]]", "[[US-089-start-and-stop-a-rain-replay-on]]", "[[US-091-measure-how-often-a-single-timestep-route]]"]
tags: [user-story, replay, p0]
---

# US-102 Replay the storm with the US-101 fix to close BL-028

As the owner of the flood-routing product, I want a full replay of the 2026-09-16 storm with the `US-101` rule, so I know the pipeline keeps simulating while the flood stands and `BL-028` can close.

Given the storm file `hanoi_20260916_storm.csv` and the `US-101` rule, when the replay runs on the server for about 12 hours, then no run between the first and the last simulating run is skipped while the previous table has edges at or above the depth floor, the first run after any quiet stretch logs a hotstart and not "No saved state", and the table after the quiet stretch holds a wet-edge count close to the forecast of the table before it.

Dependencies: none open. The product owner gives the go before the replay starts, because it holds the server for about 12 hours. The steps: run `replay.ps1 stop`, raise `FLOOD_EXTENT_KEEP_RUNS` (about 60) so `US-091` can use the same replay, start the replay again, and unpause `flood_mapping_full`. `US-089` is the story that owns `replay.ps1`.

## Status history

- **2026-10-10, ready.** Written at the Scrum adoption ([[decision-log|D-024]]), because `US-101` reached `Done` without the replay its acceptance check names, and `BL-028` stays `monitoring` until the replay. Moves the open step "next action 2" of the old `TODOS.md` into a story.

## Evidence and details

Fill this when the story reaches `Done`. **Evidence** is a screenshot of the replay output that shows the tables of the gap and the hotstart line, saved under `artifacts/docs/stories/evidence/`. **Details** is a numbered list: what was built, how, why, and what it changes for dependent stories.
