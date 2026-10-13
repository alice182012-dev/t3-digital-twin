---
date_drafted: 2026-10-13
type: user-story
us_id: "US-133"
title: "Pick soak pairs that can prove a blocked edge"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Reviewed
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: routing, testing
source_ideas: []
related: ["[[graphhopper-backend]]", "[[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]]", "[[lessons#L-013|L-013]]"]
tags: [user-story]
---

# US-133 Pick soak pairs that can prove a blocked edge

As a developer, I want the soak `roads` check to test the blocked promise, so a run that skips every blocked pair cannot pass.

On 2026-10-13 the check skipped all 51 blocked pairs of its 104, because the dry control route did not cross the picked edge ([[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], details item 7).
A skipped pair shows no kept promise, and the run reported 0 failures.
The story picks pairs whose dry route must cross the edge, for example the two ends of an edge that is the only way across, and it fails a run that has no blocked pair to judge.

Given a run with edges at or above a vehicle's limit, when the check runs, then at least one blocked pair per vehicle is judged and not skipped.
Given a run with no judged blocked pair, then the check reports it and exits with a failure.

Dependencies: [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]] is `Done`.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: it has no open dependency, it fits one sprint, and its acceptance is a check on the server.
- **2026-10-13, Reviewed.** Built and run on the server. The owner has not accepted it. The check now over-samples edges, sends the dry control straight to GraphHopper, and exits 1 when a vehicle with an edge at or above its limit has no judged blocked pair (`blocked_unproven`). On the pinned flood it judged 7 blocked pairs and proved all four vehicles, and it reported 3 failures that [[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]] holds.

## Evidence and details

**Evidence:** the JSON of the run in details item 4. No screenshot yet.

**Details:**

1. The first change (over-sample and the `blocked_unproven` field) did not make the pairs judged. On the small flood of run `20261013T104500` it exited 1 with all four vehicles unproven, and on the pinned flood 51 pairs were still skipped.
2. The cause was the dry control. A request sent through `floodmap-backend` is flooded even with no `run` and `valid_time`. With `TIME_AWARE_ROUTING` on, the backend sends the clock as the departure and the engine judges the newest table. In `DEMO` mode the backend replaces the request step with the pinned one. So the control never crossed a blocked edge, and every blocked pair skipped. The check of 2026-10-02 passed 40 blocked promises with the flag off.
3. The control now goes to GraphHopper (`roads --graphhopper`, default `http://graphhopper:8989`) with only `points`, `profile`, `points_encoded`, and `instructions`. `roads --oversample` (default 5) sets the candidate edges per bucket as a multiple of `--per-bucket`, which now counts judged pairs per bucket and vehicle.
4. Run on the server with a temporary `DEMO` row, at the pinned step (`--run 20261011T001500 --valid-time 2026-10-11T02:00:00+07:00`, 19:00 UTC): 26 roads and 79 pairs. 15 `found` and 10 `crosses` pairs passed, 7 `blocked` pairs passed, 44 `blocked` pairs and 5 `crosses` pairs were skipped, 3 pairs failed, `blocked_unproven` was empty, and there were 0 server errors. The exit code was 1 because of the failures.
5. The 3 failures are a truck on edge `116434665:2` (15 cm, promise `crosses`) and a car and a truck on edge `400545823:1` (21 cm, promise `found`). The flooded request found no route in both directions, and the dry control found one.
6. The pure functions `dry_shows_promise` and `unproven_vehicles` have 2 test classes. 56 tests pass without a database, and 4 database tests skip.
7. The concept page [[graphhopper-backend]] describes the new control and flags.

