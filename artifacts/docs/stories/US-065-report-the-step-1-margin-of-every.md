---
date_drafted: 2026-09-29
type: user-story
us_id: "US-065"
story_label: "10"
epic: "[[EP-07-carried-over-backlog]]"
status: Done
priority: P2
estimate: M
sprint: 5
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Report the step-1 margin of every run of the replay"
---

# US-065 Report the step-1 margin of every run of the replay

As the pipeline owner, I want one command that reads the per-run timings of the 48-hour replay and says whether every simulated run published step 1 before it became now, so `US-037` is judged on every simulated run by a number and not by eye.
Given the rows that `run_margins.sh` prints (slot, trigger, depth, raster, tiles, margin) and the simulating slots from Story 8, when the report runs, then it prints the run count, the worst, median, and best margin, the runs with a negative margin, the slots that should have simulated and have no row, and the slope of the margin per run inside each chain. It exits with 0 only if no run is late and none is missing.
Priority: P2. Status: Done. Estimate: M. Sprint: 5 ([[SP-02-routing-engine-foundations|sprint-plan-2]]). Dependencies: Story 8, for the schedule function. `run_margins.sh` moves from `marie-curie/us-037/`, which git does not track, to `scripts/pipeline_margins/`. Tests use the four runs of 2026-10-02 as a fixture (margins +1.9, +4.1, +2.7, +2.4). It needs no server to build, and a server only to run it on real rows.
Evidence: ![[us-065-margin-report-check-output.png|700]]
Details:
1. What: `scripts/pipeline_margins/report.py` reads the rows of `run_margins.sh` and prints the run count, the worst, median, and best margin, the late runs, the runs the replay should have simulated and did not, and the margin slope of each chain. It exits with 0 only if no run is late, none is missing, and at least one run has a margin.
2. How: tests first (21). `run_margins.sh` moved from `marie-curie/us-037/`, which git does not track, to `scripts/pipeline_margins/`. With `--event`, `--start`, and `--threshold` the report takes the expected runs from `simulating_slots` of `US-063`. `--since` and `--until` limit the runs judged. A line that is not a row stops the report with exit 1, so a Docker error cannot pass.
3. Why: `US-037` is judged on every simulated run of the 48-hour replay, by a number and not by eye.
4. Effect: on the 50 mm/h storm of 2026-10-02 (50 real runs, 00:45 to 13:00 +07) the report fails. The mean margin was +2.3 minutes in the 01:00 hour, +0.5 in the 02:00 hour, and -0.7 or lower from the 03:00 hour, while the tile task grew from 5.8 to 11.5 minutes. That confirms the reopening of `US-037`. The margin is measured to the end of the tile task, which is 1 to 1.3 minutes after step 1 is published, so a run that is slightly late here can still have published step 1 on time. The 07:00 run (-19.2 minutes) is not explained.
