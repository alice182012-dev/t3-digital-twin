---
date_drafted: 2026-10-07
type: user-story
us_id: "US-089"
story_label: "2"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P1
estimate: M
sprint: 
subsystem: rain-replay
related: ["[[EP-13-rain-replay-test-environment]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Start and stop a rain replay on the server with one command each"
---

# US-089 Start and stop a rain replay on the server with one command each

As a tester, I want one command that applies a recorded storm when no rain falls, and one that restores live rain, so I do not edit `.env` by hand.
The hand edit failed on 2026-10-05, first when the start time passed before the DAG was unpaused, then when an empty shell variable left `FLOOD_TEST_RAIN_START` blank.
Given the server with live rain, when the user runs the start command with an event file, then the command picks the first 15-minute slot at least 30 minutes ahead (the lead is a parameter), writes `FLOOD_TEST_RAIN_CSV`, `FLOOD_TEST_RAIN_START`, and the rain gate to `.env`, empties `FLOOD_TEST_RAIN_MM_HR`, recreates only the worker with `--no-deps`, and reads the values back from inside the worker.
It prints the event's total and peak, the number of runs that pass the gate, the chains with their start times, and the time to unpause `flood_mapping_full`.
It stops with a message, and changes nothing, when the event file does not load, when the start is not on a 15-minute slot, or when the preview shows no run passing the gate.
Given a replay is on, when the user runs the stop command, then the three replay variables and the gate are back to their live values, the worker is recreated, and the read-back shows no replay.
A status command shows the current mode, the start, the next slot, the rate at this moment, and the first and last runs that simulate.
Both commands are idempotent.
Running start twice with the same event and slot leaves the same `.env`.
The command is PowerShell for the server's shell (5.1, so `;` and not `&&`), run on the host as the lesson
[[lessons#L-010|recreate-remote-services-on-the-remote-host]] requires.
The checks that can run without Docker live in `scripts/rain_replay.py` as new subcommands, with tests on the Mac, so the PowerShell stays thin.
Dependencies: None to build.
Story 1 supplies the storm, and the existing event `scripts/rain_events/hanoi_20251005_48h.csv` works until then.
The server run needs no image build, so it can run while a replay is on.
## Status history

- **2026-10-10, carried from the retired TODOS note.** `scripts/rain_replay.py` and `replay.ps1` start, stop, and report a replay, idempotently, and read the values back inside the worker.
- **2026-10-10, done.** The product owner gave the go, and the server run of the storm replay covered start, a second start, status, and stop.
  The details list what the output shows and the parts it does not show.

## Evidence and details

**Evidence:** rendered output of the `replay.ps1` session on the server. The start lines come from the session record of 2026-10-10 04:01 +07, and the status and stop lines were captured at 18:49 to 18:50 +07 from the Mac over SSH.

![[us-089-start-stop-output.png|900]]

**Details:**

1. Start: `replay.ps1 start -Event scripts\rain_events\hanoi_20260916_storm.csv -LeadMinutes 30 -Gate 5` ran at 04:01:26 +07. The output reads the event as 24 rows, 53.9 mm, peak 8.7 mm/h, and it reports that 42 of 46 runs pass the 5 mm/h gate, in 2 chains.
2. The start printed the unpause time (before 04:45 +07, which is 21:45Z on 2026-10-09). The read-back from inside the worker showed `mode replay` and the start 2026-10-09T21:45:00Z.
3. Idempotency: the same start ran again at 04:01:38 +07, inside the same quarter-hour. The `.env` hash (`Get-FileHash`) was the same before and after, so the second start left the same `.env`.
4. Status at 18:50:05 +07 showed `mode replay`, the start, and the gate line. It also showed the slot at 11:45Z with a rate of 0 mm/h and the next slot at 12:00Z.
   The gate line gave the first run (04:45 +07) and the last gate-passing run (16:00 +07). It did not print the last run that simulated (18:15 +07), which the acceptance text names.
5. Stop at 18:49:50 +07 restored the four rain keys from `.env.rain-replay.json` and deleted that file. The worker was recreated with `--no-deps`. The read-back from inside the worker showed `mode live` and exit 0.
6. A `status` after the stop showed `mode live`, no state file, and empty `FLOOD_TEST_RAIN_MM_HR`, `FLOOD_TEST_RAIN_CSV`, and `FLOOD_TEST_RAIN_START`.
7. Not shown in the evidence: the read-back after the stop printed the three replay variables but not the gate line, so the restored gate value is not in the output.
8. Not shown in the evidence: the start output gave the chain count (2) but not the chain start times that the acceptance text names.
9. The Mac has no `pwsh`, so the PowerShell ran only on the server. The 37 tests of `scripts/rain_replay.py` passed in the SPR-013 analysis of 2026-10-10. They were not run again for this close.
