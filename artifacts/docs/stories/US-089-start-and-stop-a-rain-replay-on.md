---
date_drafted: 2026-10-07
type: user-story
us_id: "US-089"
story_label: "2"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
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
Evidence: see the Evidence and details section.

## Status history

- **2026-10-10, carried from the retired TODOS note.** `scripts/rain_replay.py` and `replay.ps1` start, stop, and report a replay, idempotently, and read the values back inside the worker.
- **2026-10-10, reviewed.** The commands ran on the server for the Scope A replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]].
  The status stays Reviewed.
- **2026-10-10, reviewed.** `replay.ps1` start ran twice inside one quarter-hour, at 04:01 +07.
  `.env` was byte-identical after the second run, with SHA-256 `61B7CDF166A31691586069DDFD4C9169CFF2DC61E65046AC0C93A3923B9C94CD` both times.
- **2026-10-10, reviewed.** Before the start, `.env.rain-replay.json` was found to hold the values of the first replay, the 48-hour event of 2025-10-05 with gate 0.01.
  Stop would have restored that old replay.
  The file was backed up as `.env.rain-replay.json.bak-2026-10-10` and rewritten with the live values.
- **2026-10-10, reviewed.** `replay.ps1` stop ran at 18:49 +07.
  It restored the four rain keys, deleted `.env.rain-replay.json`, recreated the worker, and read back `mode live`.
  Status at 18:50 +07 showed `mode live`, with the CSV, START, and MM_HR keys empty.
- **2026-10-10, reviewed.** The preview and status now say "at least N runs", because US-101 adds runs.
  Stop now expects `mode live` when the saved rain is empty.
  This PowerShell edit ran for the first time on the server (PowerShell 5.1) and worked.
- **2026-10-10, reviewed.** `git pull` on the server failed on two clippings with a "?" in the file name, which Windows rejects.
  They were renamed, and the file-name rule in `Home.md` covers this case.

## Evidence and details

The image is rendered output, not a live screenshot.
The start lines come from the session record of 04:01 +07.

![[us-089-start-stop-output.png|900]]

Rendered output of `replay.ps1` start, status, and stop on the server, captured 2026-10-10 18:49 to 18:50 +07 on gods-macbook.local (the Mac), over ssh to the server 100.67.84.55.

Not in this evidence: the stop cases that change nothing, which are an event file that does not load, a start that is not on a 15-minute slot, and a preview with no run passing the gate.

1. What was built: `replay.ps1` with start, stop, and status, and the checks that run without Docker in `scripts/rain_replay.py`.
2. How: start writes the three replay variables and the gate to `.env`, recreates only the worker with `--no-deps`, and reads the values back from inside the worker.
   Stop restores the four rain keys from `.env.rain-replay.json`, then deletes that file.
3. Why: a second start with the same event and slot must leave `.env` unchanged, and the hash matched after the second start, so the start is idempotent as the story requires.
4. What it changes: the Scope A replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] used these commands for its start and stop.
   The stop case with no saved rain now expects `mode live`.
