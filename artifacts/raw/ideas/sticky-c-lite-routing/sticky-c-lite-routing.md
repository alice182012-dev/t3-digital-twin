---
date_captured: 2026-09-29
type: idea
status: go
source: User decision in a Claude Code session on 2026-09-29, after the research recorded in [[routing-not-time-aware]] and [[departure-time-advice-research]].
subsystem: floodmap-backend
tags: [idea, routing, forecast, graphhopper, sticky-closure, c-lite]
related: ["[[routing-not-time-aware]]", "[[departure-time-advice-research]]", "[[graphhopper-backend]]", "[[flood-on-roads]]"]
---

# Sticky C-lite: time-aware flood routing in GraphHopper

## Idea

Route each request against the flood forecast at the time the traveller reaches each road, counted
forward from the moment of the request, not at one fixed step. A custom GraphHopper module carries the arrival time in each search label, and a weighting
looks up each edge's depth at that time. Closures are sticky: an edge is impassable from its first flooded
step at or after the departure step until the end of the forecast horizon. This page records why the
team chose this tier, what the switch costs, and the roadmap. The design detail lives in the
"Tier C-lite" section of [[routing-not-time-aware]].

## Why we choose it

Today's `POST /route` judges every road at the one `valid_time` in the request. A road that dries at
`valid_time` and floods 10 minutes later passes, and a traveller who arrives in 15 minutes drives into
water. That is scenario 1 in the blocker's test table, and it is a safety fault, not a tuning issue.

Sticky C-lite fixes that fault with the least model risk of the three tiers.

1. **Exact under sticky closure.** Closures only grow with time, so an earlier arrival is never worse.
   The search needs no waiting policy at intersections and stays a plain forward Dijkstra. Arrival-only
   closure breaks that rule, and forbidding waiting on receding water is NP-hard (see the research
   section of the blocker).
2. **No tuning parameters.** A-prime needs a trip bound `T`, a top speed `v_max`, and an origin-based cache
   key, and it returns "no route" when a flood inside the window would not have affected the traveller.
   Sticky C-lite has none of those, and it returns the earliest-arrival route.
3. **Right answer on the scenarios A-prime gets wrong.** In scenarios 2 and 4 of the blocker table, a road
   floods at minute 45 and the traveller passes it at minute 15 or 30. A-prime blocks when the window
   reaches minute 45. Sticky C-lite passes. These are expected results, not observed ones.
4. **Conservative in the safe direction.** A road that drained stays closed for a traveller who arrives
   during the horizon after it flooded. The error is a longer detour, never a route through water.
5. **It supports the "wait until" advice.** The departure timeline in [[departure-time-advice-research]] needs
   the router and the advice to use one rule. Sticky closure measured from the departure step gives that.

### The departure step is never before the request time

Today `POST /route` takes `valid_time` from the client and never reads the wall clock. The map picks the
timestep closest to now, which can lie in the future (see [[map-shows-forecast-not-now]]). A time-aware
router needs the request time as a second input, because a traveller cannot leave in the past.

- **Departure step.** `t0` is the later of the selected `valid_time` and the request time, rounded to the
  step that contains it. If the user picks a future step on the map, `t0` is that step. If the step is in
  the past, `t0` is now.
- **Remaining horizon.** The horizon is 2 hours from the run's first step, not from now. A run that is 40
  minutes old leaves 80 minutes, and a trip that ends after the last step returns `unknown`.
- **Steps before now.** They count as the past and are ignored, the same as steps before `t0`.
- **Current state.** The forecast has no step at or before now in some runs (the blocker above), so
  the first usable step can be later than now. The router then treats the gap between now and that step as
  unknown, and the advice says so.
- **Wait until.** Candidate departures start at now, not at the start of the run.
- **Run age.** The response echoes the run and its age, so a stale run shows as stale.

The server reads the clock. The client does not send it, so a wrong device clock cannot change the answer.

### Assumption made on 2026-09-29: sticky is measured from the departure step

The blocker defines sticky closure as "from its first flooded step until the end of the horizon". A road
that flooded at 17:00 and drained at 17:30 would then stay closed for a traveller who departs at 18:00,
and "wait until 18:00" could never help. This page defines it from the departure step `t0` instead. For a
request departing at `t0`, an edge is impassable at arrival time `a` when its depth reaches the vehicle limit
at any forecast step in `[t0, a + margin]`. Steps before `t0` are the past and do not count. The margin is
10 minutes, fixed on the server.

This is my reading of the decision, not something the user stated. The blocker page and the departure
plan need the same wording. Confirm it before the Java work starts.

## Cost-benefit of changing

The change replaces a pinned stock GraphHopper image and one SQL path with an image we build and a depth
table that Airflow publishes. Sizes are relative (S, M, L), not measured effort. Nothing here was timed.

| Piece | What it costs | Size | What it buys |
| --- | --- | --- | --- |
| Java module (weighting, time-dependent search, `GraphHopper` subclass, Dropwizard class) | New language and build in a repo with none. Tests we must write. Pin policy in [[graphhopper-backend]] changes. | L | The arrival-time lookup that today's engine cannot do. |
| Depth table keyed by GraphHopper edge id and step | An Airflow task after `9b_load_depth_raster`. Edge ids change on every re-import, so each table carries a graph hash and a mismatch is refused. Storage size depends on the edge count of `hanoi-model-area.osm.pbf`, not measured. | M | The per-edge, per-step depth the weighting reads. |
| Edge-id mapping | `road_segment` pieces are cut per OSM way and GraphHopper edges are cut at junctions, so they do not line up. Sampling along exported edge geometry is one option, `osm_way_id` in `graph.encoded_values` is the other (unverified in the pinned build). | M | A join that does not depend on how pieces are cut. |
| Reload without restart | Memory-mapped file, polled `latest` pointer, reference swap. | S | New runs go live without dropping requests. |
| Backend profile selection and fallback | A flag and a freshness and hash check in `_handle_route`. | S | A defined path when the table is missing, stale, or mismatched. The fallback is today's model, so the response must say the timing check was skipped (see the review findings). |
| Latency | Unmeasured. A unidirectional search visits more nodes than a bidirectional one, and LM's speed-up is unverified for this weighting. | Unknown | Must stay within a factor of today's p95, chosen after the baseline. |
| Verification | Synthetic corridor scenarios for `motorbike` and `car`, an offline checker that re-walks each route, a slow reference Dijkstra in `marie-curie/`. | M | Proof that no returned route crosses a road that is impassable at its arrival step. |

**Benefit summary.** A routing answer that matches the forecast at arrival time, no parameters to tune, and
one shared rule for routes and departure advice. **Cost summary.** One large module we own for the life of
the routing service, plus an Airflow task and a table format to maintain.

**Alternative kept in reserve.** A-prime needs no engine change, but it adds `T`, `v_max`, and a lower cache
hit rate, and it blocks routes a timed search would allow. The blocker's decision gate said to build
C-lite only if measuring A-prime showed no route on more than 10% of pairs that have a timed route, or a
median detour more than 25% longer. The team chose C-lite without running that gate, and A-prime is not
built. After C-lite ships, run the same pairs against today's model and the offline reference, and use
the two thresholds to judge how much C-lite changed.

**Risks.**

- **The image is ours to keep working.** A GraphHopper upgrade can break the extension points. Mitigation:
  pin the version, keep the module small, and test against the pinned image in CI.
- **LM admissibility is unverified.** The reasoning says a weight that only rises keeps LM's lower bounds valid.
  A unit test must confirm it before the design relies on it, or the search falls back to plain Dijkstra.
- **Stale or mismatched table.** The fallback covers it. A table for the wrong graph hash must never be read.
  The fallback is today's single-step model, which has the fault this work exists to fix, so a fallback
  response must carry a flag that the UI shows as "timing check unavailable".
- **Forecast error.** Sticky closure is a claim about the forecast. Answers say "clear in the forecast", not "safe".

## What's already covered

- **Today's model** covers a single moment and stays as the fallback profile. It has the fault described above.
- **The departure timeline** ([[departure-time-advice-research]], step 1) needs no engine change and no tier
  decision. It also gives the offline checker this work needs. Build it in parallel.
- **A-prime** is documented in the blocker and is not built.

## Engineering review findings (gstack plan-eng-review, reduced run, 2026-09-29)

The review covered scope, architecture, tests, and performance against this page and the blocker. It did
not run the skill's decision ledger, outside voice, or review log, because the session was a background job
with no one to answer per-finding questions. Confidence is out of 10.

1. **Scope trips the complexity threshold.** The work adds a Java module, a container image, an Airflow
   task, a table format, a backend profile switch, and a client fetch. That is more than one service and
   more than eight files. The separable pieces are the departure timeline (phase 2, no engine change) and
   phase 7. Keep the timeline as its own delivery so it can ship without the Java work. (Confidence 8.)
2. **Fallback reintroduces the fault silently.** The blocker's fallback sends a stale-table request to the plain
   profile with an A-prime `custom_model` (`routing-not-time-aware.md`, "Fallback", item 8). A-prime is not
   built, so the real fallback is today's single-step model. The response needs a flag and the UI needs
   wording. Added above. (Confidence 8.)
3. **The gate the roadmap cited cannot run.** Phase 6 said to run the A-prime gate numbers, and A-prime does
   not exist. Changed to compare against today's model and the offline reference. (Confidence 9.)
4. **Table size is a small risk at a 2-hour horizon.** With 15-minute steps the table holds 9 values for each
   edge. Even 2 million edges at 2 bytes each is about 36 MB per run. This is an estimate from a
   guessed edge count, not a measurement, and phase 0 replaces it with the real count. It removes table size
   as a reason to revisit. (Confidence 6.)
5. **Phases 3 and 4 can run in parallel.** The Java module can be developed and tested against a synthetic
   table from phase 1. Only the phase 4 exit test on real data needs phase 3. (Confidence 7.)
6. **No Java exists in the repo.** A search for `.java`, `pom.xml`, and Gradle files found none. The plan
   adds a build and test toolchain, so phase 4 also needs a CI job that builds the module against the
   pinned GraphHopper version. The Python side already has pytest-style tests, for example
   `floodmap/graphhopper-flood-road/backend/test_flood_areas.py`. (Confidence 9.)
7. **Sticky-from-`t0` needs a lookup per edge and step.** The weighting scans at most 9 steps for the first
   flooded step at or after `t0`, so the cost is small. It is unmeasured, and phase 6 covers it.
   (Confidence 6.)

### Test requirements the roadmap did not list

- **Regression:** with the flag off, `POST /route` returns the same body as today for a fixed request.
- **Departure not on a step:** a `t0` between two steps rounds outward and never inward.
- **Horizon edge:** a trip that ends after the last step returns `unknown`, and no edge reads past the table.
- **Run pinning:** a request during a run switch reads one run for all steps.
- **Reload race:** a request in flight during a table swap finishes on the old table.
- **Hash mismatch:** a table for another graph build is refused and triggers the fallback with its flag.
- **No coverage on an edge:** an edge with no value reads as clear, per the 2026-09-29 decision.

## Roadmap

Each phase has an exit test. A later phase starts when the earlier exit test passes, except where a
phase says it can run in parallel.

| Phase | Work | Exit test |
| --- | --- | --- |
| 0. Baselines and unknowns | Measure p50 and p95 of `POST /route` on the server (flexible mode, LM). Count edges in `hanoi-model-area.osm.pbf`. Find the source revision of the pinned image. Check `OSMWayID` in the pinned build. Confirm the sticky-from-`t0` wording with the user. | The latency baseline, the edge count, and the revision are written to [[routing-not-time-aware]]. |
| 1. Reference and scenarios (parallel with 0) | In `marie-curie/`, build the synthetic corridor and a slow time-dependent Dijkstra reference. Build the offline checker that re-walks a route with per-edge times. | The reference reproduces the sticky column of the blocker's test table on all four scenarios. |
| 2. Departure timeline (parallel with 1) | Build `POST /route/departures` as in [[departure-time-advice-research]], with the sticky-from-`t0` rule. Client fetch when the route view is `empty`. | The alert shows "wait until" for scenario 3, and shows none for a clear route. |
| 3. Depth table (parallel with 4, using a synthetic table in 4) | Export GraphHopper edge geometry. Add the Airflow task that samples the run's depth tiles along each edge and writes one file per run, tagged with the graph hash. | A table for one real run loads, the hash check refuses a mismatched file, and values match a raster spot check. |
| 4. Java module | Weighting, time-dependent Dijkstra with millis in the label, `GraphHopper` subclass, `motorbike_td` profile, image build, compose change. Unit-test LM admissibility. | The four scenarios match the sticky column for `motorbike` and `car`, with and without a detour, and the offline checker finds no crossing of an impassable edge. |
| 5. Backend integration | `_handle_route` picks `motorbike_td` behind a flag and falls back on a missing, stale, or mismatched table. Reload without restart. | Turning the flag off restores today's behavior. A stale table triggers the fallback. |
| 6. Server proof and rollout | Run on the server, compare p50 and p95 with the phase 0 baseline, run the blocker's gate numbers on a fixed set of pairs (today's model and the phase 1 reference as the comparison, since A-prime is not built), update [[graphhopper-backend]] and the blocker. | Latency is inside the factor the user sets, and the blocker moves to `resolved` with evidence. |
| 7. Later | Measure how many routes arrival-only closure would change. Build it only if the count justifies a heuristic search. | A number, not a decision. |

Phase 6 needs the latency factor. No factor is set yet.

## Trigger to revisit

Revisit if phase 0 shows the pinned image cannot accept the extension points, or if the LM test fails and
the plain search is too slow. Either can send the team back to A-prime.

## Status history

- **2026-09-29, go.** The user chose sticky C-lite as the routing option in a Claude Code session, and
  allowed a write in `artifacts/raw/ideas/`. Captured with the reasoning, cost-benefit, and roadmap. The
  sticky-from-`t0` wording is an assumption to confirm.
