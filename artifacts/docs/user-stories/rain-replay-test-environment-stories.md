---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-088", "US-089"]
status: draft
subsystem: rain-replay
source_ideas: []
related: ["[[sprint-plan-3]]", "[[rain-replay-test-environment]]", "[[september-2026-storm-rain-replay]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[3di-simulation-orchestration]]", "[[carried-over-backlog]]", "[[edge-depth-table-stories]]", "[[2026-10-07]]"]
tags: [user-story, epic, rain, replay, test-environment, sprint-12]
---

# Epic: a rain test environment

The pipeline only simulates when rain is forecast. When no rain falls, a test of the timing work (`US-045`, `US-069`,
`US-073`, and the final reading of `US-070`) has nothing to run on. [[us-063-realistic-rain-replay-for-us-037-and-us-034]]
built the replay itself. These stories add a real storm to replay and a command to start and stop a replay safely.
Both are in Sprint 12 of [[sprint-plan-3]], at the user's request. Each row carries Priority, Status, Estimate, Sprint,
and Dependencies, as an extension of the base Epic shape in [[user-story-types]]. A story reaches `Done` only with
evidence and numbered details, recorded here and in `sprint-plan-3.md`. The design is in [[rain-replay-test-environment]].

- **Story 1 (US-088): Cut the Hanoi storm of 2026-09-16 and 2026-09-17 into a replay event.**
  As a tester, I want the real storm of 2026-09-16 and 2026-09-17 as an event file, so a replay exercises the roads
  inside the flood model's border under a sharper storm than the October 2025 one.
  Given NASA's GPM IMERG half-hourly Late Run data for the window, when the download and the area average run for the
  model extent, then the result is `scripts/rain_events/hanoi_20260916_storm.csv` with the header
  `offset_minutes,precipitation_mm_hr` and rows 30 minutes apart, committed to git. A line in the plan records the
  source window, the total in millimetres, and the peak in millimetres per hour. The file loads with `load_event` and
  `python3 scripts/rain_replay.py preview` lists its chains at the gate that the replay uses.
  The tools are the three scripts under `test-code/rain input/` (git-ignored, on the user's Mac). They have the paths and
  the dates of an earlier event written into them, so the story runs a copy with the new dates, and the copy goes in
  `marie-curie/`. Use the Late Run (`GPM_3IMERGHHL`). The Final Run (`GPM_3IMERGHH`, the value in
  `download_gpm_imerg.py`) is published 3.5 to 4.5 months late. A CMR query on 2026-10-07 for 2026-09-16T00:00Z to 2026-09-18T00:00Z returned 97 Late Run granules and 0 Final Run granules. The folder
  `GPM_3IMERGHHL_07-...` that the earlier event used confirms the Late Run was the working choice.
  The news reports of the storm give station totals (about 200 mm at the heaviest stations) and no time series. The
  event file comes from the satellite series and not from those totals. IMERG averages a 0.1 degree grid over the
  model extent, so its total is lower than a station's. The story records both numbers and does not scale the series
  to match the stations.
  Priority: P1. Status: In progress. Estimate: S. Sprint: 12. Dependencies: A NASA Earthdata login in `~/.netrc` on the
  Mac, and the Python packages the scripts import (`earthaccess`, `h5py`, `fiona`, `pyproj`, `numpy`), which the Mac
  has. The story needs no server.
  Evidence: None yet.

- **Story 2 (US-089): Start and stop a rain replay on the server with one command each.**
  As a tester, I want one command that applies a recorded storm when no rain falls, and one that restores live rain, so
  I do not edit `.env` by hand. The hand edit failed on 2026-10-05, first when the start time passed before the DAG was
  unpaused, then when an empty shell variable left `FLOOD_TEST_RAIN_START` blank.
  Given the server with live rain, when the user runs the start command with an event file, then the command picks the
  first 15-minute slot at least 30 minutes ahead (the lead is a parameter), writes `FLOOD_TEST_RAIN_CSV`,
  `FLOOD_TEST_RAIN_START`, and the rain gate to `.env`, empties `FLOOD_TEST_RAIN_MM_HR`, recreates only the worker with
  `--no-deps`, and reads the values back from inside the worker. It prints the event's total and peak, the number of
  runs that pass the gate, the chains with their start times, and the time to unpause `flood_mapping_full`. It
  stops with a message, and changes nothing, when the event file does not load, when the start is not on a 15-minute
  slot, or when the preview shows no run passing the gate.
  Given a replay is on, when the user runs the stop command, then the three replay variables and the gate are back to
  their live values, the worker is recreated, and the read-back shows no replay. A status command shows the current
  mode, the start, the next slot, the rate at this moment, and the first and last runs that simulate.
  Both commands are idempotent. Running start twice with the same event and slot leaves the same `.env`.
  The command is PowerShell for the server's shell (5.1, so `;` and not `&&`), run on the host as the lesson
  [[recreate-remote-services-on-the-remote-host]] requires. The checks that can run without Docker live in
  `scripts/rain_replay.py` as new subcommands, with tests on the Mac, so the PowerShell stays thin.
  Priority: P1. Status: Reviewed. Estimate: M. Sprint: 12. Dependencies: None to build. Story 1 supplies the storm,
  and the existing event `scripts/rain_events/hanoi_20251005_48h.csv` works until then. The server run needs no image
  build, so it can run while a replay is on.
  Evidence: None yet.

## Status history

- **2026-10-07, draft.** Written at the user's request. The plan of the storm, [[september-2026-storm-rain-replay]],
  said no code was needed and listed the server steps as manual. The user then asked for a test environment that
  applies rain when none falls, and pointed to the scripts that build the rain. Story 1 is the event, and Story 2 is the
  environment.
- **2026-10-07, active.** `US-088` and `US-089` started at the user's request, before Sprint 12 starts. For `US-088`, the copies of the two scripts are in `marie-curie/us-088/` (`download.py`, `build_hyetograph.py`), and the download did not run. This session reached CMR but timed out on `urs.earthdata.nasa.gov` and `disc.gsfc.nasa.gov`, the login and download hosts, so it could not fetch a granule. The user runs `python3 download.py`, then `python3 build_hyetograph.py`, in that folder on the Mac. `US-089` is built in a separate worktree.
- **2026-10-07, active.** `US-089` is `Reviewed`: built and merged into `modular` (`4de0895`, `a53eb0b`, `6bf8673`), not run on the server. `scripts/rain_replay.py` has `next-slot`, `check`, and `status` (37 tests in `scripts/test_rain_replay.py`, 21 in `scripts/pipeline_margins/test_report.py`, all pass), and `scripts/rain_env/replay.ps1` has `start`, `stop`, and `status`. The Mac has no `pwsh` or Docker, so no line of `replay.ps1` has run. The first server run is its test, and its read-back inside the worker is the check. Review found one defect, a second `stop` that dropped the restored gate, fixed in `6bf8673`. `create_simulation.get_rain_forecast` and `read_rain_env` repeat the same refusal message, a follow-up to merge them. `US-089` reaches `Done` after a server run of `start`, a read-back, and `stop` with a screenshot of the output.
