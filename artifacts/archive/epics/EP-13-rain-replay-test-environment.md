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

Story-level progress lines up to 2026-10-10 are in [[EP-13-rain-replay-test-environment-history|the archived history]]. This section keeps plan-level changes only.

- **2026-10-07, draft.** Written at the user's request. The plan of the storm, [[september-2026-storm-rain-replay]],
  said no code was needed and listed the server steps as manual. The user then asked for a test environment that
  applies rain when none falls, and pointed to the scripts that build the rain. Story 1 is the event, and Story 2 is the
  environment.
- **2026-10-07, active.** `US-089` is `Reviewed`: built and merged into `modular` (`4de0895`, `a53eb0b`, `6bf8673`), not run on the server. `scripts/rain_replay.py` has `next-slot`, `check`, and `status` (37 tests in `scripts/test_rain_replay.py`, 21 in `scripts/pipeline_margins/test_report.py`, all pass), and `scripts/rain_env/replay.ps1` has `start`, `stop`, and `status`. The Mac has no `pwsh` or Docker, so no line of `replay.ps1` has run. The first server run is its test, and its read-back inside the worker is the check. Review found one defect, a second `stop` that dropped the restored gate, fixed in `6bf8673`. `create_simulation.get_rain_forecast` and `read_rain_env` repeat the same refusal message, a follow-up to merge them. `US-089` reaches `Done` after a server run of `start`, a read-back, and `stop` with a screenshot of the output.
