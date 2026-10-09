---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-088", "US-089"]
status: draft
subsystem: rain-replay
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[rain-replay-test-environment]]", "[[september-2026-storm-rain-replay]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[3di-simulation-orchestration]]", "[[EP-07-carried-over-backlog|carried-over-backlog]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[2026-10-07]]"]
tags: [user-story, epic, rain, replay, test-environment, sprint-12]
---

# Epic: a rain test environment

The pipeline only simulates when rain is forecast. When no rain falls, a test of the timing work (`US-045`, `US-069`,
`US-073`, and the final reading of `US-070`) has nothing to run on. [[us-063-realistic-rain-replay-for-us-037-and-us-034]]
built the replay itself. These stories add a real storm to replay and a command to start and stop a replay safely.
Both are in Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request. Each row carries Priority, Status, Estimate, Sprint,
and Dependencies, as an extension of the base Epic shape in [[user-story-types]]. A story reaches `Done` only with
evidence and numbered details, recorded here and in `sprint-plan-3.md`. The design is in [[rain-replay-test-environment]].

- [[US-088-cut-the-hanoi-storm-of-2026-09|US-088]] Cut the Hanoi storm of 2026-09-16 and 2026-09-17 into a replay event. Story 1.
- [[US-089-start-and-stop-a-rain-replay-on|US-089]] Start and stop a rain replay on the server with one command each. Story 2.

## Status history

- **2026-10-07, draft.** Written at the user's request. The plan of the storm, [[september-2026-storm-rain-replay]],
  said no code was needed and listed the server steps as manual. The user then asked for a test environment that
  applies rain when none falls, and pointed to the scripts that build the rain. Story 1 is the event, and Story 2 is the
  environment.
- **2026-10-07, active.** `US-088` and `US-089` started at the user's request, before Sprint 12 starts. For `US-088`, the copies of the two scripts are in `marie-curie/us-088/` (`download.py`, `build_hyetograph.py`), and the download did not run. This session reached CMR but timed out on `urs.earthdata.nasa.gov` and `disc.gsfc.nasa.gov`, the login and download hosts, so it could not fetch a granule. The user runs `python3 download.py`, then `python3 build_hyetograph.py`, in that folder on the Mac. `US-089` is built in a separate worktree.
- **2026-10-07, active.** `US-089` is `Reviewed`: built and merged into `modular` (`4de0895`, `a53eb0b`, `6bf8673`), not run on the server. `scripts/rain_replay.py` has `next-slot`, `check`, and `status` (37 tests in `scripts/test_rain_replay.py`, 21 in `scripts/pipeline_margins/test_report.py`, all pass), and `scripts/rain_env/replay.ps1` has `start`, `stop`, and `status`. The Mac has no `pwsh` or Docker, so no line of `replay.ps1` has run. The first server run is its test, and its read-back inside the worker is the check. Review found one defect, a second `stop` that dropped the restored gate, fixed in `6bf8673`. `create_simulation.get_rain_forecast` and `read_rain_env` repeat the same refusal message, a follow-up to merge them. `US-089` reaches `Done` after a server run of `start`, a read-back, and `stop` with a screenshot of the output.
- **2026-10-08, active.** Decision from the user: a replay tests for 12 hours only, to save 3Di compute cost. `US-088`'s event file is the wettest 12 hours (24 steps of 30 minutes) of the 2026-09-16 to 2026-09-18 series, not the full storm. `marie-curie/us-088/build_hyetograph.py` now cuts that window and writes `hanoi_20260916_storm.csv`. The download did not run in this session: `urs.earthdata.nasa.gov` returned "No route to host" from the build session again, so the user runs `python3 download.py`, then `python3 build_hyetograph.py`, in that folder. The cut keeps the sharpest part of the storm, so the peak stays at the full-storm value and the total can be lower.
- **2026-10-08, active.** `US-088` data is in. The download ran on the Mac with an `EARTHDATA_TOKEN`, because `urs.earthdata.nasa.gov` is unreachable from the Mac and the server (the netrc login failed with "No route to host"; `cmr` and `data.gesdisc` answer). 97 Late Run granules, 2026-09-16T00:00Z to 2026-09-18T00:00Z. Full series: 84.95 mm total, peak 8.73 mm/h (area mean over the model extent). The 12-hour event `scripts/rain_events/hanoi_20260916_storm.csv` runs 2026-09-16T16:00Z to 2026-09-17T03:30Z: 53.88 mm, peak 8.73 mm/h, 24 rows. At the gate of 5 mm/h, `rain_replay.py check` lists 42 of 46 runs in 2 chains. The area mean is far below the station totals (about 200 mm), as the story expected, and was not scaled. Not committed yet.
- **2026-10-09, active.** `US-088` is `Done`. Evidence: `us-088-event-check-output.png` (24 rows, 53.88 mm, peak 8.73 mm/h, preview 42 runs in 2 chains, file tracked in git). The server ran 45 simulating runs, 3 more than the preview, and the cause is not yet checked.
