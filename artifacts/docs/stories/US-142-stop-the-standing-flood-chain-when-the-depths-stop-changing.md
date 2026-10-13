---
date_drafted: 2026-10-13
type: user-story
us_id: "US-142"
title: "Stop the standing-flood chain when the depths stop changing"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Draft
kind: story
priority: P2
estimate: S
sprint: 
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

- **2026-10-13, Draft.** Raised from [[BL-030-the-standing-flood-rule-never-ends-with-permanent-water|BL-030]] when the owner ruled it not a blocker. It is in the backlog and has no `sprint`.
