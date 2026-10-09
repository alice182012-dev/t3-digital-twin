---
date_drafted: 2026-09-29
type: user-story
us_id: "US-068"
story_label: "11"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P2
estimate: S
sprint: 5
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`"
---

# US-068 Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`

As the pipeline owner, I want the XCom of the task `1_trigger_simulation` to show how much rain was sent to 3Di, so I can read a run's rain input in the Airflow UI without opening the log or the 3Di run.
Given a run of `flood_mapping_full` that took the simulate branch, when `1_trigger_simulation` succeeds, then its XCom holds a key `rain_ingested` next to `sim_id`, with the run's slot, the source of the rain (Tomorrow.io, the replay file of `US-063`, or the fixed test rain), the interval count, the first and last offset in seconds, the maximum intensity in mm/h, and the total rain in mm. The numbers come from the same `[offset_seconds, m/s]` list that `run_forecast_process` sends to `simulations_events_rain_timeseries_create`, not from the forecast the rain gate saw. Given a run that fails before the rain is sent, then no `rain_ingested` is pushed.
Priority: P2. Status: Done. Estimate: S. Sprint: 5 ([[SP-02-routing-engine-foundations|sprint-plan-2]]). Dependencies: None. Building it needs no server. Reading it on a real run needs the server.
Evidence: ![[us-068-rain-ingested-xcom.png]]
Details:
1. What: `1_trigger_simulation` now pushes an XCom `rain_ingested` next to `sim_id`, with the slot, the rain source (Tomorrow.io, the replay file, or the fixed test rain), the interval count, the first and last offset in seconds, the maximum mm/h, and the total mm of the series sent to 3Di.
2. How: tests first. A pure function, `summarize_rain_values`, works on the `[offset_seconds, m/s]` list that `build_rain_values` returns, which is the list `run_forecast_process` sends to 3Di, and not on the forecast the rain gate saw. The total is a trapezoid sum, because the series is sent with `interpolate=True`. `get_rain_forecast` reports which branch gave the intervals. 22 tests pass in `test/test_create_simulation_cycle.py`.
3. Why: a run that ingests no rain, or a replay slice that is shifted, looked the same in the Airflow UI as a correct one, and the number had to be read from the log or the 3Di run.
4. Effect: on the server, the first run of the 48-hour replay (slot `2026-10-05T17:00:00Z`) pushed `rain_ingested` with source `replay:hanoi_20251005_48h.csv`, 9 points from offset 0 to 7200 s, a maximum of 1.096 mm/h and a total of 0.881 mm. The same numbers come out of `rain_replay.py` and `summarize_rain_values` on the event file, so the value in the UI is the value computed from the event, and the replay start of `US-063` reads the event from offset 0. `US-069` and the replay checks can read a run's rain input in the UI.
5. Limits: one run was read, the first of the window. The Tomorrow.io and fixed-rain branches are covered by tests and not by a server run. The evidence image is rendered from output the user pasted.
Why it is a separate story. Today `1_trigger_simulation` pushes only `sim_id` (`dags/flood_mapping_dag.py`). The XCom `rain_intervals` sits on `0_check_forecast_rain` and holds the forecast as the gate saw it, in mm/h. What 3Di receives is the result of `build_rain_values(intervals, start=slot)` in `scripts/create_simulation.py`, in m/s and offset from the slot, and nothing records it. A run that ingests no rain, or a replay slice that is shifted, looks the same in the UI as a correct one.
Open details for the build. `get_rain_forecast` returns only the intervals, so the source label needs a small change to say which branch produced them. The total is computed from the sent list with the trapezoid rule, because the series is sent with `interpolate=True`. Tests first, with a pure summary function over the `[offset, m/s]` list, so no server is needed.
