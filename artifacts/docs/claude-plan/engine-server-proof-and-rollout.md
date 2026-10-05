---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-10, routing, rollout, latency, us-055]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[time-aware-backend-integration]]", "[[route-departures-endpoint]]", "[[wait-until-alert]]", "[[routing-not-time-aware]]", "[[graphhopper-backend]]", "[[sprint-plan-3]]"]
---

# Plan: prove the engine on the server and roll it out (US-055)

## Context

Acceptance, from [[time-aware-routing-engine-stories]] Story R10. On the deployed image and a real run: the four scenarios pass the checker. The p50 and p95 of `POST /route` are within the factor of the baseline of `US-046` (the user set 2 on 2026-10-02). For a fixed set of pairs, run against today's model and the engine, the share of routes that change and the median detour ratio are recorded. [[graphhopper-backend]] and [[routing-not-time-aware]] are updated, and the blocker moves to `resolved` only with this evidence.

The user wants everything built first, then one test on the server, and then nothing more built. This story is therefore the tooling and the runbook, and the server run is its evidence step. No image is built on the server before the 48-hour replay ends.

## What the server run does, in order

One script, `scripts/routing_proof/rollout.ps1`, in PowerShell on the server:

1. Check the DAG is paused (no builds during the replay), and list the table folder.
2. `git pull`, then build the three images: `graphhopper` (its Docker build runs every module test), `floodmap-backend`, and `flood-routing-frontend` (it carries the alert of `US-054`). These are the only builds.
3. Recreate the three services with the flag off. Read the engine's start log: the module is active, it follows `/tables`, and it loaded a table (a table for another graph would be refused and logged).
4. Route the fixed pairs through the backend with the flag off (today's model).
5. Turn the flag on for the backend only, and route the same pairs.
6. `compare`: the share of routes that change and the median detour ratio.
7. `crossings`: every engine route, walked over the depth table with the checker of `US-047`, must cross no closed road. Today's routes are listed for contrast.
8. `departures`: `POST /route/departures` for each trip.
9. `latency`: p50 and p95 of `POST /route` for the short, medium, and long trips, for motorbike and car, 30 requests each, against target C of the baseline (the app's path), factor 2. A fallback or a non-200 fails the cell.
10. Put the flag back off, or leave it on with `-LeaveOn` when every check passed.

The four synthetic scenarios on the deployed image are `java/time-aware-routing/scenario-check.sh` (32 runs), run from the Mac. The real-run proof of the story is the checker over real routes and the real table in step 7, because a synthetic table cannot be put in the volume without moving the real `latest`.

## Decisions

1. **Baseline cell.** Target C of [[routing-not-time-aware]] ("Latency of POST /route, 2026-10-02"): `POST /route` through the backend, areas cached. It is the path the app takes, so it is what the traveller waits for. Target B (GraphHopper with the flood model) is kept in the tool for comparison. The baseline constants are checked against the vault's table by a test.
2. **Pairs.** The three trips of the baseline for all four vehicles, plus a second set of three trips shifted by about 100 to 200 m, 24 in all, all inside the model border. A pair with no route is listed and left out of the percentages, because the flood changes the routes from run to run.
3. **Flag toggled by the script**, because the flag is a backend environment variable and the comparison needs both modes on the same graph and the same run.
4. **Result files** go to `<data>\routing_proof` and the log to `C:\Users\TECOTEC\rollout-proof.log`.

## Steps built (tests first)

1. `routing_proof.py` and its 25 tests: the baseline parsing and its equality with the vault, the latency verdict (the factor is inclusive, either percentile can fail, a non-200, a fallback, no baseline, and nothing measured all fail), the comparison (the share changed, the median ratio, pairs left out, engine statuses), the crossings (the pinned run, the vehicle limit, the step that contains the request), and the request and record shapes. Four changes each fail a test.
2. `pairs.json`, and a test that its pairs are inside the border.
3. `rollout.ps1`. It could not be run in the cloud session, because it needs PowerShell and Docker on the server.
4. Docs.

## Risks

- **`rollout.ps1` is untested.** The first run on the server is its test. It stops at the first failed precondition or build and logs each step.
- **Detail alignment** on a real route (US-053): the departures step and the crossings step both need the `edge_id` and `time` details to line up.
- **The graph hash.** If the live graph's hash differs from the table's, the engine logs a refusal, step 3 fails, and every request would fall back. The log line shows both hashes.
- **Latency** is unmeasured. The engine has no landmarks, so it visits more nodes than the stock search. The long trip is the cell to watch.
- **Table freshness.** The proof reads the table that is on the volume. After the replay it can be old, but a route's `td.departure` is floored to a step inside it, and `unknown` answers are counted as known answers.

## Status history

- **2026-10-05, active.** Plan written, and the tooling built and tested. The server run is the evidence step and waits for the end of the replay window.
