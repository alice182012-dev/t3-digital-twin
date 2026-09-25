---
date_open: 2026-09-25
date_closed: 
type: blocker
status: open
severity: P1
subsystem: 3di-orchestration
approaches_tried: 0
approaches_remaining: 1
tags: [blocker, 3di, hotstart, saved-state, forecast]
related: ["[[map-shows-forecast-not-now]]", "[[3di-simulation-orchestration]]", "[[decision-log]]"]
last_updated: 2026-09-25
---

# Each run hotstarts from a state saved at the end of the previous run

## Description

`run_forecast_process` in `scripts/create_simulation.py` (lines 267-282) saves the simulation state at
`time=SIMULATION_DURATION`, which is 7200 s, the last second of the run. The next run loads that state
(`load_last_state`, line 226) and starts at `intervals[0].startTime`, the start of the new forecast window,
which is about when the rain check runs.

During rain, the DAG starts the next run as soon as the previous one ends. A run takes about 28 minutes, so
run R1 starts at X+28 but begins from the water state of R0 at X+120. The model starts about 92 minutes
ahead of itself: water that has not fallen yet is already on the ground.

| Run | Starts at | Hotstarts from the state at | Offset |
| --- | --- | --- | --- |
| R0 | X+0 | cold start or older state | |
| R1 | X+28 | R0 at X+120 | 92 min ahead |
| R2 | X+56 | R1 at X+148 | 92 min ahead |

The error does not grow from run to run, but every run after the first starts from a future state. The "now"
tiles from R1 onward ([[map-shows-forecast-not-now]]) are therefore too wet.

## Why this matters

The map, routing, and any forecast chart read these tiles. If each run starts from a state 92 minutes too
late, every depth it produces is biased toward more water.

## Decision and explanation

Agreed with the user on 2026-09-25: save the state at 1800 s (one output interval) instead of 7200 s. The
next run starts about 28 to 30 minutes after the previous one, so a state at start + 1800 s is within about
2 minutes of the next start.

Change: in `run_forecast_process`, pass a separate setting (for example `HOTSTART_SAVE_SECONDS`, default
1800) as the `TimedSavedState` `time`, in place of `SIMULATION_DURATION`. Update the log line at 269.

## Concerns

- **The gap after dry cycles.** After a dry spell, the saved state can be hours old, and `load_last_state`
  does not check its age. The state file already stores `updated_at`. Decide whether a state older than some
  limit should mean a cold start.
- **Failed runs.** The state ID is written only when the run succeeds (line 299), so a failed run leaves the
  older state in place. A save at 1800 s exists as soon as the simulation passes 1800 s, so a run that fails
  later could still provide it. The code does not use that today.
- **Expiry.** Saved states expire after one day (line 270). A dry spell longer than a day leaves an ID
  that 3Di no longer holds.
- **Pipeline time.** The 2-minute match holds only while a run takes about 30 minutes. If processing time
  changes, the offset changes with it.

## Related topics

- [[map-shows-forecast-not-now]]
- [[3di-simulation-orchestration]]

## Status history

- **2026-09-25, open.** Found while working through the run timeline for [[map-shows-forecast-not-now]].
  The user asked to log it, with the fix: save the state at 1800 s.
