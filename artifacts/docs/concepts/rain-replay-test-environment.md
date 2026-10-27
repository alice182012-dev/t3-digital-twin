---
date: 2026-10-07
type: concept
status: active
tags: [concept, rain, replay, test-environment, us-088, us-089, sprint-12]
related: ["[[EP-13-rain-replay-test-environment|rain-replay-test-environment-stories]]", "[[september-2026-storm-rain-replay]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[3di-simulation-orchestration]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[lessons#L-010|recreate-remote-services-on-the-remote-host]]", "[[2026-10-07]]"]
last_updated: 2026-10-10
---

# Plan: a rain test environment

## Context

The core DAG simulates only when the forecast reaches the rain gate. With no rain, `US-045`, `US-069`, `US-073`'s
timing, and the last reading of `US-070` have nothing to run on. The replay of [[us-063-realistic-rain-replay-for-us-037-and-us-034]]
already feeds a recorded event to the gate through three variables in `.env`. What the user asked for on 2026-10-07 is a
test environment around it: apply a real storm when none falls, with the storm of 2026-09-16 and 2026-09-17.

## What exists, and what failed

`create_simulation.get_rain_forecast` reads `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START`, and `rain_replay.py` turns
the event into the forecast intervals. The pieces work. The steps around them were by hand, and two failed on 2026-10-05.
The first start passed before the DAG was unpaused, so nothing ran. A shell variable was empty on the Mac, so the worker
started with `FLOOD_TEST_RAIN_START` blank, which makes every run fail. A read-back before the unpause caught the second
one. Nothing in the repository does that read-back.

## Design

The data shape is a replay setting: an event file, a start on a 15-minute slot, and a gate in millimetres per hour. Live
rain is the absence of a setting.

1. `scripts/rain_replay.py` gains subcommands that run without Docker and have tests: `next-slot` (the first slot at
   least a lead ahead of a given time), `status` (reads the three variables from the environment, loads the event, and
   prints the start, total, peak, the rate now, and the first and last simulating runs), and a check that rejects a
   start off the slot grid and an event whose preview has no run at the gate.
2. `scripts/rain_env/replay.ps1` has `start`, `stop`, and `status`. It edits `.env`, recreates
   the worker with `--no-deps`, and runs `rain_replay.py status` inside the worker as the read-back. It never builds an
   image and never touches the DAG or the databases. It prints the unpause time and does not unpause.
3. The same stack serves live and replay. A replay writes to the real tables, so the map and routing show the storm
   while it runs. This stack has no real users yet, and a second stack would copy the 3Di model's storage, which is
   about 100 GiB free on the server. Revisit this when the product has users.

## Decision for the user

The design above keeps one stack. An isolated second stack (own database, own MinIO, own frontend) would keep replay
data out of the tables that routing reads, at the price of disk, a second set of 3Di runs, and a second Airflow. The plan
takes the single stack because the frontend and routing are not deployed to real users. Say so if a second stack matters
sooner.

## Cost and limits

Every simulating run is a real 3Di simulation. The preview prints the number of runs before anything starts, and the
3Di organisation's session limit (HTTP 429) hit once on 2026-10-01. A storm is shorter than the 48-hour October replay,
so it makes fewer runs, but its peak is higher.

## Order of work

1. US-088: run the download and the area average for the storm window on the Mac, with the Late Run, and commit the CSV.
2. US-089, tests first on the Mac: the `rain_replay.py` subcommands with the October 2025 event as the fixture.
3. US-089, the PowerShell command. The Mac has no `pwsh`, so its parsing and its `.env` edits are checked by the
   server run, with the read-back as the check.
4. Server: run `start` with the new event, read back, unpause at the printed time. Then `stop` and read back live mode.

## Status history

- **2026-10-07, active.** Written after the user asked for a test environment and named the scripts that build the
  rain (`test-code/rain input/`). The scripts have the dates of an earlier event written into them and use the Final
  Run short name, which has no data for September 2026. The plan uses a copy with the Late Run.
- **2026-10-08, active.** The user decided that a replay runs for 12 hours only, to save 3Di compute cost. The storm event is cut to its wettest 12 hours before it is committed, so the preview shows fewer simulating runs than the 48-hour October event. `US-045` and `US-069` still need several `routing_adapter` runs; 12 hours of storm gives those runs, but not the 24-hour to 48-hour comparison that `US-069` names. Raise that with the user when the replay starts.
- **2026-10-10, active.** `US-089` is `Done`. On the server, `start` ran twice inside one quarter-hour with the same `.env` hash, and `stop` read back `mode live` at 18:49 +07 (see [[US-089-start-and-stop-a-rain-replay-on|US-089]]). The replay that used this stack ran 04:45 to about 18:15 +07 ([[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]).
