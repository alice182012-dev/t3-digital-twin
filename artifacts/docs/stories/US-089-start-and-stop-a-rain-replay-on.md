---
date_drafted: 2026-10-07
type: user-story
us_id: "US-089"
story_label: "2"
epic: "[[EP-13-rain-replay-test-environment]]"
status: Reviewed
priority: P1
estimate: M
sprint: 12
subsystem: rain-replay
related: ["[[EP-13-rain-replay-test-environment]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Start and stop a rain replay on the server with one command each"
---

# US-089 Start and stop a rain replay on the server with one command each

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
[[L-010-recreate-remote-services-on-the-remote-host|recreate-remote-services-on-the-remote-host]] requires. The checks that can run without Docker live in
`scripts/rain_replay.py` as new subcommands, with tests on the Mac, so the PowerShell stays thin.
Priority: P1. Status: Reviewed. Estimate: M. Sprint: 12. Dependencies: None to build. Story 1 supplies the storm,
and the existing event `scripts/rain_events/hanoi_20251005_48h.csv` works until then. The server run needs no image
build, so it can run while a replay is on.
Evidence: None yet.
- **2026-10-10, carried from the retired TODOS note.** `scripts/rain_replay.py` and `replay.ps1` start, stop, and report a replay, idempotently, and read the values back inside the worker.
