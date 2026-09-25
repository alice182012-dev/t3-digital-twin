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

`run_forecast_process` in `scripts/create_simulation.py` (lines 267-284) saves the simulation state at
`time=SIMULATION_DURATION`, which is 7200 s, the last second of the run. The next run loads that state
(`load_last_state`, line 226) and starts at `intervals[0].startTime`, the start of the new forecast window,
which is about when the rain check runs.

During rain, the DAG starts the next run as soon as the previous one ends. The observed
`manual__2026-09-25T14:09:53` run (21:09:53 to tiles published around 21:17 local) took about 8 minutes
trigger to tiles, not the 28 minutes assumed at first. On a fast cycle like that, run R1 starts at X+8 but
begins from the water state of R0 at X+120. The model starts about 112 minutes ahead of itself: water that
has not fallen yet is already on the ground, and the gap is worse than a slower cycle would give, because the
next run starts sooner while the saved state's sim-time stays fixed at 7200 s.

| Run | Starts at | Hotstarts from the state at | Offset |
| --- | --- | --- | --- |
| R0 | X+0 | cold start or older state | |
| R1 | X+8 | R0 at X+120 | 112 min ahead |
| R2 | X+16 | R1 at X+128 | 112 min ahead |

The error does not grow from run to run, but every run after the first starts from a future state. The "now"
tiles from R1 onward ([[map-shows-forecast-not-now]]) are therefore too wet. `D`, the wall-clock time per
run, is one observed data point, not a measured average; it depends on rain complexity and grid size, so the
offset varies run to run.

## Why this matters

The map, routing, and any forecast chart read these tiles. If each run starts from a state 112 minutes too
late, every depth it produces is biased toward more water.

## Decision and explanation

Agreed with the user on 2026-09-25: save the state at 1800 s (one output interval) instead of 7200 s. This
was decided before the 8-minute cycle time was confirmed, so it does not fully close the gap: with an
8-minute cycle, a state saved at 1800 s (30 min of sim time) still lands about 22 minutes ahead of the next
run's start, down from 112, but not near zero. The saved-state offset is always `(the save point) - D`, and
`D` is short enough now that no fixed save point removes it. Revisit with the user whether 1800 s is still
the right value, or whether the save point should track the observed cycle time instead of a constant.

Change: in `run_forecast_process`, pass a separate setting (for example `HOTSTART_SAVE_SECONDS`, default
1800) as the `TimedSavedState` `time`, in place of `SIMULATION_DURATION`. Update the log line at 269.

## Concerns

- **The gap after dry cycles.** After a dry spell, the saved state can be hours old, and `load_last_state`
  does not check its age. The state file already stores `updated_at`. Decide whether a state older than some
  limit should mean a cold start.
- **Failed runs.** The state ID is written only when the run succeeds (line 301), so a failed run leaves the
  older state in place. A save at 1800 s exists as soon as the simulation passes 1800 s, so a run that fails
  later could still provide it. The code does not use that today.
- **Expiry.** Saved states expire after one day (line 270). A dry spell longer than a day leaves an ID
  that 3Di no longer holds.
- **Pipeline time.** With the observed 8-minute cycle, 1800 s leaves a 22-minute offset, not a close match.
  A fixed save point only tracks the next run's start time by coincidence.

## Related topics

- [[map-shows-forecast-not-now]]
- [[3di-simulation-orchestration]]

## Status history

- **2026-09-25, open.** Found while working through the run timeline for [[map-shows-forecast-not-now]].
  The user asked to log it, with the fix: save the state at 1800 s.
- **2026-09-25, open.** Corrected the run duration: the user pointed to the real
  `manual__2026-09-25T14:09:53` run, whose tiles were ready by about 21:17, roughly 8 minutes after trigger,
  not the 28 minutes first assumed. Recomputed the offset at 112 minutes (not 92), and the 1800 s fix now
  leaves about 22 minutes (not "about 2 minutes"). The fix itself is unchanged; the numbers in Description
  and Concerns are corrected.
- **2026-09-25, open.** The proposed design in [[map-shows-forecast-not-now]] replaces the 1800 s fix, pending
  the user's approval. Runs start on a 15-minute clock at tₖ, with the state saved at 900 s (= tₖ₊₁) and at
  1800 s as a backup. The save point then equals the cycle length, so the offset is zero by design.
