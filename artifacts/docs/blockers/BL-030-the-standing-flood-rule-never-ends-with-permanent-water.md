---
date_open: 2026-10-13
date_closed: 2026-10-13
type: blocker
status: closed
severity: P1
subsystem: airflow-pipeline, 3di-orchestration
approaches_tried: 0
approaches_remaining: 4
tags: [blocker, standing-flood, 3di, cost]
related: ["[[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]", "[[US-101-keep-simulating-while-the-flood-still-stands|US-101]]", "[[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]]", "[[US-139-skip-a-flood-run-whose-slot-is-hours-old|US-139]]", "[[decision-log|D-037]]", "[[3di-simulation-orchestration]]"]
last_updated: 2026-10-13
---

# The standing-flood rule never ends because the model holds permanent water

## Description

`standing_flood.py` keeps `flood_mapping_full` simulating every slot until the newest 5 runs of `edge_depth` have a deepest value under 5 cm (`DRY_DEPTH_M`, `DRY_RUNS_TO_STOP`) and no rain is forecast.
After the unpause of 2026-10-13 at 09:39 UTC, every slot has started a real 3Di simulation with a forecast of 0 mm/h: the slots of 09:45, 10:00, 10:15, and 10:30 UTC (simulations 452835, 452839, 452846, and 452854), and the log of each says "Standing flood: standing_flood, 0 of 5 dry runs in a row".

The water that keeps the rule open does not move.
Every run since `20261013T104500` has 157 to 158 edges at or above 5 cm, 47 to 48 edges at or above 50 cm, and 13 edges at or above 100 cm.
The deepest edge, `601448364:0` (21.00543, 105.72381), reads 223 cm at every one of the 8 steps of every run.
The run of the slot 09:45 UTC started cold ("Coldstart: no saved state within 30 minutes") and shows the same edges, so the water is in the model or its initial state and not in a hotstart chain.
The deepest edge of the stored storm run `20261011T001500` also ends at 223 cm.
So some edge is always at or above 5 cm, and the rule cannot see 5 dry runs.

## Why this matters

- **Cost.** A run for every slot is 96 simulations a day on 3Di compute, with no rain.
- **Mode.** `forecast_mode` stays `LIVE`, so the map never shows the `DEMO` flood.
- **The rule was never shown to end on its own.** On 2026-10-10 the chain ran inside a replay, and on 2026-10-13 at 02:47 UTC the gate ended because the newest run was older than 45 minutes, not because the flood was dry.
- **US-114.** The archive of real-mode runs grows with these runs, which are not real rain.

## Approaches tried

None as a fix. The cause was found on 2026-10-13 while the owner's question about the chain was open.

## Candidate approaches

| Option | What it does | Cost and risk |
| ------ | ------------ | ------------- |
| A. Subtract a permanent-water baseline | Keep the depth of each edge in a dry reference (a cold start with no rain) and count an edge as wet only above that baseline plus 5 cm. | S to M. Needs a baseline run and a refresh when the model changes. |
| B. Stop on a steady state | Stop when no edge changed by more than 1 cm between consecutive runs for 5 runs in a row and no rain is forecast. | S. A slow recession of a real flood changes by more than 1 cm for a long time, so it keeps running, which is wanted. A real standing flood that stops changing would stop the chain, which is also wanted. |
| C. Mask the permanent-water edges | List the edges that read at or above the limit in a dry reference and leave them out of the rule. | M. The list needs the same refresh as option A. |
| D. Raise `DRY_DEPTH_M` above the pond depth | The ponds read below the limit. | Not safe: a real flood below 2.3 m would end the chain at once. |
| E. Pause `flood_mapping_full` | Stops the cost. | Blocks real rain and the proof of [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], and freezes `forecast_mode`. |

B is the smallest change that follows the physics (the chain should run while the water changes).

## Decision and explanation

Pending. The owner decides the fix and whether to pause the DAG until then.

## Concerns

The cause (permanent water in the template or its initial state) is inferred from the data and not read in the 3Di model.
The edge `601448364:0` and the other deep edges should be checked on a map before option A or C is built.

## Related topics

- [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]
- [[3di-simulation-orchestration]]
- [[US-139-skip-a-flood-run-whose-slot-is-hours-old|US-139]]

## Status history

- **2026-10-13, open.** Found when the chain started by the unpause of 09:39 UTC did not stop. Four real simulations ran with a forecast of 0 mm/h by 10:30 UTC, and the depth data of the runs is static.
- **2026-10-13, open.** The owner chose to pause `flood_mapping_full` and decide the fix later. Paused at about 10:36 UTC to stop the cost. Real-rain monitoring for US-114 waits until the DAG is unpaused.
- **2026-10-13, closed.** The owner ruled that this is not a blocker: the flood model is not verified, so deep water at some edges is no problem to fix. The chain's cost is the backlog story US-142.
