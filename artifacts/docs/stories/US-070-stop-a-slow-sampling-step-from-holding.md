---
date_drafted: 2026-09-29
type: user-story
us_id: "US-070"
story_label: "E8"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: S
sprint: 10
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Stop a slow sampling step from holding the database"
---

# US-070 Stop a slow sampling step from holding the database

As the operator, I want task 9c to analyze the run's tiles first and cancel a step that runs past its limit, so
one slow query cannot starve the runs behind it (blocker [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]]).
Given a step that runs past 120 s, when 9c samples it, then the build fails naming the step, no table is written,
and the previous table stays published. Given a normal run, the table is the same as before.
Priority: P1. Status: Done (2026-10-10). Estimate: S. Sprint: 10. Dependencies: Story E3.
- **2026-10-10, done.** The user approved closing the story on its own check (a step past 120 s is cancelled, a normal run gives the same table). Across all 92 runs of `9c` none went past 120 s, and all succeeded. [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]] stays `monitoring`, because `9c` rose from 46 s to 96 s within chain 1 and no cause is known.
- **2026-10-10, carried from the retired TODOS note.** On the server, run `20261006T104500` took 51.1 s and its `ANALYZE` ran.

## Evidence and details

**Evidence:** rendered output of `evidence/us-070-9c-in-airflow-check.sh`, captured at 02:05:41 +07 on 2026-10-10 from the Mac, reading the server.

![[us-070-9c-in-airflow-check-output.png|1000]]

**Details:**

1. Built: task `9c` analyzes `flood_depth_raster_tile` first and cancels a step that runs past 120 s, so the build fails naming the step, writes no table, and leaves the previous table published (`5e358bf`, 133 tests).
2. How: it ran on the server from 2026-10-06. In the second replay `9c` took 46 to 96 s (mean 65 s) over 45 runs, and over all 92 runs none reached the 120 s cancel. The original incident was one step of 770 s.
3. Why: one slow query held the database and starved the runs behind it. No such step has happened since the change.
4. What it changes: `9c` still gets slower within a chain (chain 1: 46 s to 96 s over 27 runs, chain 2: 46 s to about 60 s over 18 runs), even after the prune of `US-086` and its `VACUUM FULL`. The story's check does not cover this, so `BL-023` stays `monitoring` and the growth is recorded as unexplained. If a run reaches 120 s, the task fails loudly and the previous table stays published.
