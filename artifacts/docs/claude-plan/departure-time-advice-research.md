---
date: 2026-09-29
type: plan
status: draft
tags: [routing, forecast, departure-time, graphhopper, safety, research]
related: ["[[BL-011-routing-not-time-aware|routing-not-time-aware]]", "[[graphhopper-backend]]", "[[flood-on-roads]]", "[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]"]
last_updated: 2026-09-29
---

# Departure-time advice: how to answer "when should I go?"

This page is research and a proposal. Nothing here is built, and no number in it was measured unless it says so.
It answers question 8 in [[BL-011-routing-not-time-aware|routing-not-time-aware]]. Every tier in that blocker answers "which route, if I leave
at `t0`?". A traveller asks the reverse: "given where I am going, which `t0` is safe?".

Each claim carries one of three labels. **Verified** means read in the repo or a cited source. **Inference**
means reasoned from verified facts. **Unmeasured** means a cost or latency nobody has timed.

## What the system has today

- **Verified.** `POST /route` takes one `valid_time` and judges every road at that step. `_handle_route` in
  `floodmap/graphhopper-flood-road/backend/server.py` pops `valid_time`, `run`, and `vehicle_type`, calls
  `cached_areas`, and sends one `custom_model` to GraphHopper.
- **Verified.** `cached_areas` keys on `(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)`.
  The key has no origin, so all users share an entry for one step and vehicle. The TTL is 30 seconds
  (`FLOOD_AREAS_CACHE_TTL_SECONDS`). Expired entries are never deleted, so the dict grows with each new key.
- **Verified.** A cache miss runs `derive_areas`, which runs one SQL statement per depth band. The blocker
  describes three bands. Each miss also opens a new PostgreSQL connection.
- **Verified.** With `run: "latest"`, `_WINNER_SEG_SQL` picks the newest `timestamp` for each `forecast_time`
  separately (`DISTINCT ON (forecast_time) ... ORDER BY timestamp DESC`). Two steps of one sweep can therefore
  come from two different forecast runs. A pinned `run` uses `_PINNED_RUN_SEG_SQL` and does not.
- **Verified.** A forecast step is one `forecast_time` in `flood_road_values`, with a `depth` for each road
  piece. Timesteps are 30 minutes today, and the blocker says a future implementation should use 15.
- **Unmeasured.** The latency of `POST /route`. [[graphhopper-backend]] says only the point-depth endpoint has
  local numbers (about 58 ms per request, mostly connection and raster-library load), and those do not carry
  over to routing.

## Definitions

- `t0` is a departure time, one of the forecast steps `t_1 ... t_N`. A candidate set has N members.
- `R(t0)` is the router's answer for departure `t0` under some tier: a route with arrival times, or "no route".
- A departure is **clear** when the route for that `t0` crosses no impassable road at its arrival time,
  including a margin. "Clear" is a claim about the forecast, not about the world. The UI wording is a
  separate question, see "Failure modes".
- The **margin** of a clear route is the smallest gap, in minutes, between the arrival at a piece and the
  first step at which that piece is impassable.

## Approaches

### 1. Sweep: call the router once for each candidate `t0`

Loop over `t0`, call `R(t0)`, and collect the clear ones. It needs no new routing code, so it is the obvious
first idea. What it returns depends entirely on the tier behind `R`, see the next section.

Two variants cut the calls:

- **Full sweep.** N calls. Returns every clear departure, so it can show windows.
- **Bisection.** About `ceil(log2 N) + 1` calls. It is valid only when the set of clear departures is a
  prefix of the candidate list (later is never better). That holds under sticky closure and does not hold
  when water drains, see the next section.

### 2. Single-pass time-dependent search

The time-dependent shortest-path literature has two query kinds. A **time query** answers "earliest arrival
if I leave at `t0`". A **profile query** returns the travel-time function over a whole interval of departure
times, which is what a user needs "to choose a convenient departure time" (Delling and Wagner survey,
described in a [search result](https://publikationen.bibliothek.kit.edu/1000047759/3569195)). A reversed
time-dependent Dijkstra grows a tree from a fixed arrival time and computes latest departure times at edge
tails ([Yuan et al., PVLDB 2019](http://www.vldb.org/pvldb/vol12/p1058-yuan.pdf), verified from the search
summary, not read in full). All of these assume an engine that carries time in its labels.

- **Verified.** GraphHopper's `Weighting` and `SPTEntry` carry no arrival time
  ([[BL-011-routing-not-time-aware|routing-not-time-aware]], "Can GraphHopper see arrival time?"). No off-the-shelf engine in the
  2026-09-29 survey supports flood closure windows. So a profile query needs the custom Java module of Tier
  C-lite or a research engine such as CATCHUp.
- **Inference (mine, not from a paper).** Under sticky closure and constant travel times, the latest
  departure needs no profile. Let `c_e` be the first step at which edge `e` is flooded. Entering `e` at time
  `s` needs `s < c_e`. Run a Dijkstra-like search backward from the destination, with label `L(v)` = the latest
  time you can be at `v` and still finish. Relaxing edge `e = (u, v)` gives
  `L(u) = max(L(u), min(c_e - step, L(v) - travel_time(e)))`. It is a bottleneck-path search and it returns
  the latest departure from the origin in one pass. I did not find this written up. Before relying on it,
  test it against the sweep on the synthetic scenarios in the blocker.
- **Verified.** Orda and Rom (JACM 1990) show that when waiting is unrestricted, the shortest path stays
  simple and reaches the minimum delay of the least restricted path
  ([source](https://sites.cs.ucsb.edu/~suri/cs231/Rlist/ordaRom.pdf)). Waiting at the origin is exactly the
  "leave later" choice, so the departure question stays tractable. The blocker's NP-hardness note concerns
  forbidding waiting at intersections on receding water, which this question does not need.

### 3. Cheap heuristic: scan the forecast along a fixed route

Take one route, from `POST /route` at `t0 = now`. For each piece `i` of the route, take the arrival offset
`tau_i` from the start (GraphHopper returns cumulative `time` on instructions, and the `time` path detail is
requested with `details`, both unverified on the pinned build). For each candidate `t0`, look up the depth of
piece `i` at step `t0 + tau_i`, or across the traversal window. The route is clear for `t0` if no piece is
impassable for the vehicle.

- One router call, plus one spatial query that joins the route pieces to `flood_road_values` across the steps.
- It answers "is this route usable if I leave at each time, and which road blocks it first". It does not
  find a better route. If the fixed route is blocked at every `t0`, the scan cannot say a detour exists.
- **Inference.** It doubles as the offline checker the blocker's test plan asks for: re-walk a returned
  route with per-piece arrival times and confirm no piece is impassable at its arrival step.
- Variant: request alternatives from GraphHopper (`algorithm: "alternative_route"`, unverified on the pinned
  build with a `custom_model`) and scan each. K alternatives cost K scans and still one router call.

## What each approach returns, and how each tier changes it

The four tiers are today's model, A-prime, sticky C-lite, and arrival-only C-lite, as in the blocker.

| Tier behind `R(t0)` | Are clear departures a prefix? | What a sweep can honestly return | Main risk |
| --- | --- | --- | --- |
| Today (one step, no time) | No | Nothing usable. | False reassurance. Every road is judged at `t0`, so a road that floods at `t0 + 15 min` passes. A sweep would call late departures clear whenever the flood has not started by `t0`. |
| A-prime (windowed worst case) | No, the window slides | A ranked list and clear windows. The latest departure is the end of the last clear stretch. | "No route" can come from the trip bound `T`, not from flood. Later windows may look better only because an earlier flood slid out of the window. |
| Sticky C-lite | Yes | The latest safe departure, found by bisection or by the backward pass. The earliest is "now" or never. | Conservative on receding water, so it never advises "wait for the water to drain". |
| Arrival-only C-lite | No | Clear windows, the earliest safe departure ("wait until 20:00"), and a ranking. Needs a full sweep. | Non-FIFO, so the per-`t0` search is a heuristic. **Inference.** It can miss a valid route (false caution) but every returned route is checked at its own labelled arrival times, so it should not return a blocked route. Verify with the offline checker. |

The important consequence is that the answer type follows the waiting policy.

- **Sticky closure gives a deadline.** A road that has flooded stays closed to the end of the horizon, so
  leaving later is never better. The useful advice is "leave before 18:15", and "wait" is never advice.
  This matches rising-water events and is the safe default. It cannot say "the water drains by 20:00".
- **Arrival-only gives windows.** Roads can reopen, so "wait until 20:00" becomes possible. It is also the
  policy most exposed to forecast error, because the advice depends on a predicted recession. Treat it as a
  later phase, and show windows only with a margin.
- **The output shapes.**
  - **Latest safe departure.** One time. Best for rising water.
  - **Earliest safe departure.** One time, only meaningful under arrival-only, or when now is blocked.
  - **Clear windows.** A list of `[from, to]` intervals, each shrunk by the margin.
  - **Ranked list.** Sort clear departures by margin first, then by trip time. A ranking by trip time alone
    would put the departure just before a road closes first. That is the wrong order for a flood.

### Rules that every tier needs

1. **Leaving between steps.** A traveller who leaves at 18:07 is not at 18:00 or 18:15. Advice is a step,
   so "latest safe departure" is the last clear step, and the UI says "leave by" that time, not "before the
   next one".
2. **Horizon end is unknown, not dry.** If `t0 + trip time` passes the last forecast step, the answer for that
   `t0` is `unknown`. Treating missing steps as dry gives false reassurance.
3. **Pin one run.** Resolve `latest` once, echo the run in the response, and pass it to every call. Mixing
   runs across steps (see "What the system has today") makes a timeline that no forecast ever predicted.
4. **Slower travel in floods.** The router's travel times assume normal speeds. Add the margin, or scale the
   arrival offsets, so a late arrival does not land in a later step.
5. **Departure is never before now.** The server reads the clock. Candidates start at the step that contains
   the request time, and the horizon shrinks as the run ages. A run with no step at or before now leaves
   the gap before its first step as unknown, and the advice says so. See [[sticky-c-lite-routing]].

## Cost

The horizon is 2 hours and every run covers it, so N is at most 9 candidate steps at 15-minute steps (5 at
30-minute steps). At that size, bisection saves nothing and the sticky-from-`t0` rule does not give a
sorted answer anyway, so a full sweep of N steps is the baseline for comparison.

| Approach | Router calls | Extra PostGIS work | Cache behaviour | Latency |
| --- | --- | --- | --- | --- |
| Full sweep, today or sticky model | At most 9 | Up to 9 misses, each 3 statements and 1 connection (verified structure) | Keys differ only in `valid_time`, so one user's sweep warms the cache for the next user with the same vehicle and run, for 30 seconds | Unmeasured. 9 sequential calls are 9 times a single call, and the server is `ThreadingHTTPServer`, so calls can run in parallel |
| Full sweep, A-prime | At most 9 | Up to 9 misses, each heavier (windowed `max(depth)`, per-piece window) | The key must include the origin, so the shared-entry benefit mostly disappears. Round the origin to a grid (the blocker suggests 250 m) | Unmeasured, and higher than today by the blocker's own estimate |
| Fixed-route scan (the recommendation) | 1 | 1 spatial statement over route pieces and at most 9 steps | Not served by `cached_areas`. Key on `(run, route hash, vehicle)` if needed | Unmeasured. Expect below a sweep, since GraphHopper runs once. **Inference** |
| Sticky C-lite search | 1 per request, with the arrival time in the search | Reads the run's depth table | None needed | Unmeasured. One search |

Two practical points.

- **The 30-second TTL and the unbounded dict.** A sweep adds up to 9 entries per vehicle and run, each a
  GeoJSON collection with up to about 1,000 vertices per polygon (verified in [[graphhopper-backend]]).
  Nothing evicts them, so the dict still grows with each new run. Add an eviction rule before a sweep ships.
- **Measure before choosing.** The first measurement is p50 and p95 of one `POST /route` on the server, which
  the blocker already asks for as the latency baseline. Every row above scales from it.

Caching the whole departure answer by `(run, origin cell, destination cell, vehicle)` helps only when two
users pick nearby points in the same run. Skip it until load shows a need.

## How other systems present it

- **Verified.** Google Maps for consumers offers "Leave now", "Depart at", and "Arrive by". After you pick a
  time, it shows the typical trip duration and the leave or arrive time, from historical traffic
  ([Google Maps Help](https://support.google.com/maps/answer/6291839?hl=en&co=GENIE.Platform%3DDesktop),
  described in a search summary). It answers one time at a time, not a range of departures with hazards.
- **Verified.** The Google Routes API accepts `arrivalTime` only for transit. The field "is ignored when
  requests specify a `RouteTravelMode` other than `TRANSIT`", and you can set `departureTime` or
  `arrivalTime`, not both
  ([computeRoutes reference](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes)).
  So driving "arrive by" is not exposed by the public API. **Inference.** A latest-departure answer for
  driving must be built by the caller, which is what a sweep does.
- **Verified.** Valhalla's `date_time` has four types: current, depart at, arrive by, and a fixed-time type.
  It uses `time_dependent_forward_a*` for depart-at and current. Bidirectional A* does not support time
  dependence, so timed access restrictions and historical speeds are not applied during its search
  ([Valhalla route API](https://valhalla.github.io/valhalla/api/route/api-reference/),
  [issue 5183](https://github.com/valhalla/valhalla/issues/5183),
  [issue 5616](https://github.com/valhalla/valhalla/issues/5616),
  [PR 2660](https://github.com/valhalla/valhalla/pull/2660)). I recall a reverse time-dependent search for
  arrive-by, but did not verify it. Per [[BL-011-routing-not-time-aware|routing-not-time-aware]], Valhalla's flood closures stay static per
  request, so `arrive_by` would not solve this.
- **Verified from the blocker.** GraphHopper and OSRM have no per-request time-dependent closures.
- **Verified.** Emergency management already uses the "latest departure" idea. A hurricane evacuation start
  time is the arrival time of tropical-storm-force winds minus the clearance time
  ([FEMA hurricane evacuation studies](https://www.fema.gov/sites/default/files/documents/fema_nhp_hurricane-evacuation-studies_fact-sheet_022024.pdf),
  [South Carolina decision timeline](https://www.scemd.org/media/1994/annex-a-evacuation-decision-and-response-timeline.pdf),
  from search summaries). That is the sticky-closure deadline in another domain: the hazard has an onset, and
  the traveller must finish before it. The lesson to copy is the added lead time for preparation, so a "leave
  by" time should already include the margin.
- **Not verified.** I did not find a production flood tool that returns departure-time advice for a road
  route. The academic work I found on flood evacuation routes uses spatiotemporal inundation and Dijkstra
  variants, for example [Water 2020, 12(8), 2271](https://doi.org/10.3390/w12082271) and a
  [NOAA report on human-centered flood mapping and routing](https://repository.library.noaa.gov/view/noaa/57328/noaa_57328_DS1.pdf).
  I read only search summaries of both. Absence from a short search is weak evidence.

## Failure modes and safety framing

False reassurance is worse than false caution. A traveller who is told "clear" and meets water takes on
real risk. A traveller who is told "blocked" and waits an hour loses an hour. Every design choice below
leans toward the second error.

1. **Forecast error.** The forecast has no uncertainty band in the tables described here. "Clear" means
   only that the forecast puts no impassable water on the route. Word the answer that way, never as "safe".
2. **Undetected dry cells.** [[graphhopper-backend]] says the raster source cannot tell a dry cell from a cell
   the model did not cover, so both read as `dry`. Whether `flood_road_values` has the same gap is not
   confirmed. A road with no coverage looks clear. The advice needs a coverage flag, or a stated limit.
3. **Horizon and run staleness.** Mark a `t0` past the horizon `unknown`. Show the run time on the advice.
   When a new run arrives, an advice screen must refresh, because a "leave by 18:15" can become "leave
   now" in 15 minutes.
4. **Trip-time error.** Traffic and water slow the trip. Use a margin, and set the trip bound `T` from the
   route, not a fixed hour, when a route exists.
5. **Quantisation.** Steps are 15 or 30 minutes. Report the last clear step, and compare the whole
   traversal window, rounding outward.
6. **"No route" is not "stay".** A blocked answer in A-prime can come from `T` alone. Say why: "no route
   avoids floods reported in the next hour", not "no safe route exists".
7. **Sweep artifacts.** Mixed runs across steps, or a cache entry from a previous run, can produce a
   timeline that jumps. Pin the run, and key every cache on it.
8. **Two routes for one screen.** If the map shows step `t` and the advice uses windows, they can disagree,
   the same concern as question 3 in the blocker. Show the advice's own time range on the map.
9. **Do not turn a window into a promise.** A clear window of 18:00 to 19:00 does not mean 19:00 is safe.
   Show the margin at each end.

## Recommendation

Build in two steps, and build the second only after a measurement.

### Step 1: departure timeline for one route (no engine change, no tier decision)

Use the fixed-route scan. It needs one router call and one spatial query, so it is the cheapest honest
answer, and it does not depend on which tier the blocker chooses. It also gives an offline checker that the
later tiers need anyway.

Scope it narrowly. It answers "is this route clear if I leave at each of these times, and which road blocks
it first". It says nothing about other routes.

- **Waiting policy.** Sticky closure measured from the departure step, decided 2026-09-29 when the team
  chose sticky C-lite (see [[sticky-c-lite-routing]]). For a departure at `t0`, a piece is blocked if
  its depth reaches the vehicle limit at any step in `[t0, arrival + margin]`. Steps before `t0` are the
  past and do not count, so a road that drained before `t0` is open and "wait until" can help. The router and
  the advice use the same rule. The traveller waits only at the origin, and the route does not change.
  An arrival-only check (judging a piece only at its arrival step) stays a later option.
- **Endpoint.** `POST /route/departures`. The `run` field is optional in the request and always echoed in the
  response, resolved once so the whole timeline uses one forecast.

Request body:

```json
{
  "points": [[105.8019, 21.0398], [105.8412, 21.0285]],
  "profile": "motorbike",
  "run": "latest",
  "depart_from": "2026-09-29T17:00:00+07:00",
  "step_minutes": 15
}
```

`depart_from` is optional and defaults to now. The server clamps it: the effective start is the later of
`depart_from` and the request time (the server clock), rounded to the step that contains it. The window ends
at the run's last step, so the request has no `depart_to`. A `depart_from` in the past is not an error, it is
raised to now and the response says so. The client never sends the current time.

Response body:

```json
{
  "run": "20260929T090000",
  "requested_at": "2026-09-29T17:08:00+07:00",
  "run_age_minutes": 68,
  "effective_depart_from": "2026-09-29T17:00:00+07:00",
  "horizon_end": "2026-09-29T18:00:00+07:00",
  "policy": "sticky",
  "margin_minutes": 10,
  "route": {"distance_m": 5400, "time_ms": 1260000},
  "candidates": [
    {"depart": "2026-09-29T17:00:00+07:00", "status": "clear", "margin_minutes": 45},
    {"depart": "2026-09-29T17:15:00+07:00", "status": "clear", "margin_minutes": 30},
    {"depart": "2026-09-29T17:30:00+07:00", "status": "blocked",
     "first_block": {"arrival": "2026-09-29T17:52:00+07:00", "closes_at": "2026-09-29T17:45:00+07:00",
                     "depth_cm": 34, "limit_cm": 20, "lon": 105.82, "lat": 21.03}}
  ],
  "advice": {
    "latest_clear_departure": "2026-09-29T17:15:00+07:00",
    "earliest_clear_departure": "2026-09-29T17:00:00+07:00",
    "clear_windows": [["2026-09-29T17:00:00+07:00", "2026-09-29T17:15:00+07:00"]],
    "reason": "The route floods at 17:45 near (21.03, 105.82)."
  }
}
```

`status` is `clear`, `blocked`, or `unknown` (the trip passes `horizon_end`). Sticky closure is measured from
each departure step, so a later departure can be clear when an earlier one is blocked. `clear_windows` can
hold several entries, and `earliest_clear_departure` is the "wait until" time.

The example response shows a case where 17:30 is `blocked`. If 18:00 were `clear`, `advice` would read
"wait until 18:00".

With a 2-hour horizon, "wait until" has a hard limit: the wait plus the trip must end inside the run. If
every candidate is `blocked` or `unknown`, the advice says no clear departure appears in this run, and
that the next run may show one. It never says "stay home".

Algorithm:

1. Get one route from the router with no flood `custom_model`, so a flooded network still returns a route
   to walk. The regular flood-aware request fails with a `ConnectionNotFoundException` (HTTP 400) when every road is
   blocked, as [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]] records, and that is the case this endpoint exists for. Read the per-piece arrival offsets from `details.time`. **Inference.**
   A request without `custom_model` returns the normal route. This exact request was not run.
2. Set the start: the later of `depart_from` and the request time, rounded to the containing step. Steps
   before it are the past and are not read. In one SQL statement, read for each piece the `depth` at every
   step in `[start, horizon_end]`, and
   compare it with the vehicle limit from `flood_utils.VEHICLE_PROFILES`. Use `flood_on_roads` pieces and
   the `geom_4326` GIST index, with the same buffer as `derive_areas` (22 m).
3. For each candidate `t0`, a piece is blocked if its depth reaches the limit at any step inside
   `[t0, t0 + offset + margin]`. Report the earliest blocked piece as `first_block`. The optional
   arrival-only variant checks `[t0 + offset - margin, t0 + offset + margin]` instead.
4. Return the candidates and the advice fields.

Tests, on the `marie-curie/` synthetic corridor from the blocker: scenarios 1, 2, and 4 must match the
"sticky" column, and a route that runs past the horizon must return `unknown`.

### Step 2: alternatives and a real sweep, after a measurement

Run this only if step 1 often returns "blocked at every time" while a detour exists. That is the same
question as the decision gate in the blocker, asked from the departure side.

- If Tier A-prime is built, sweep the router over candidate steps with a pinned run, using bisection when the
  policy is sticky and a full sweep otherwise. Cache by `(run, origin cell, destination cell, vehicle)`.
- If Tier C-lite is built, use the backward bottleneck pass for the sticky deadline and a full sweep for
  arrival-only windows.
- Keep the step 1 response shape. Add `route` to each candidate, so the UI can draw the route for the chosen
  departure.

### What I would not build

- A sweep on today's single-step model. It gives false reassurance, see the tier table.
- Arrival-only windows ("wait until 20:00") before someone checks how well the forecast predicts
  recession. It is the policy most likely to mislead.

## Decisions and open questions

Decided on 2026-09-29:

1. **Answer type: "wait until".** The first version uses sticky closure from the departure step, see step 1.
2. **Forecast horizon: 2 hours, and every run covers all of it.** N is 9 candidates at 15-minute steps, or
   5 at 30-minute steps, so a full sweep is cheap.
3. **Roads outside the model do not matter.** Drop the coverage flag from the failure-mode list. A road with
   no model coverage reads as clear, and the product accepts that.
4. **GraphHopper checks.** Both ran against the server on 2026-09-29, GraphHopper 12.0, profile `motorbike`,
   `ch.disable: true` and a `custom_model`.
   - **Verified.** `details: ["time", "distance"]` returns one `[fromIndex, toIndex, milliseconds]` entry per
     road piece (199 entries on an 11 km route). Cumulative sums give the per-piece arrival offset.
   - **Verified.** `algorithm: "alternative_route"` with a `custom_model` returns two paths for the same
     request, each with its own `distance` and `time`. The alternative response carried no `details` key, so
     step 2 must request the details in a second call for each alternative, or test `details` together with
     `alternative_route` before relying on it.

5. **Margin: 10 minutes.** (Set to 5 earlier the same day, then raised.) The margin widens the time window in which each road piece is checked, on
   both sides of the expected arrival. It covers a trip that runs slower than routed and the gap between a
   step and the true arrival time. A larger margin blocks more departures and shrinks the "wait until"
   window. Ten minutes is below the 15-minute step, so the window is rounded outward to whole steps and
   still reads at least one step on each side when an arrival falls between steps. Revisit it once trip
   times on flooded roads are compared with the router's estimates.
6. **The server fixes `margin_minutes` and `policy`.** The request no longer carries either field. The
   response echoes both, so the UI can show what the advice assumed. A client cannot pick a smaller
   margin than the product intends.
7. **When to compute: on request.** See the following section.
8. **Who fetches it: the client.** When a route request fails with a no-connection error, the client sends `POST /route/departures`.
   `POST /route` stays unchanged. The server-attached alternative is rejected, see "Alert behavior".
9. **Where the advice shows: in the existing no-route alert.** `NoSafeRouteMessage` in
   `floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx` (line 116) shows "No safe route available"
   when a route request has no route. The "wait until" recommendation goes into that alert. It
   appears only when the alert appears, so a user with a clear route sees no advice. See "Alert behavior".

Still open:

1. None on the design. Implementation is not scheduled.

## Alert behavior

The advice extends the alert that says no safe route exists. Nothing changes for a user whose route request
returns at least one path.

- **Trigger.** The route request fails with a no-connection error, and the departure request has not run yet.
  Today that failure is not shown. `RouteStore.ts` has no branch for `RouteRequestFailed`, so the previous
  mode's route stays on the map and the banner is empty (todo 13 in
  [[frontend-todos-and-backend-dependencies]]). That fix must land first.
- **Wording.** Where the scan finds a clear departure: "No safe route now. The usual route is clear from 18:00
  (forecast run 12:00)." The time is `earliest_clear_departure`. Where it finds none: "No safe route
  in the next 2 hours. Check again after the next forecast run." Keep the existing advice to reach the
  safest location or stay put, since "wait until" does not make waiting at the current spot safe.
- **Wording rule.** Say "clear in the forecast", not "safe". The advice is a forecast claim, see the
  failure modes.
- **Which route.** The advice describes the flood-free route from step 1 of the algorithm, not a route the
  flood-aware router would draw. The message names it "the usual route" so a user does not expect the map
  to show it. Drawing it is a UI decision.
- **Client-triggered advice (decided 2026-09-29).** `selectRoutingResultsView` in
  `routingResultsView.ts` returns `empty` only for zero paths, and a failed request never reaches it today.
  After todo 13 makes a failed request produce the no-route state and `NoSafeRouteMessage`, add a fetch
  on that state and show the advice when it returns. Keep `POST /route` unchanged. The cost is one extra request
  after a failed route, and a short state where the alert shows without the advice, which needs a
  loading line so the alert does not read as final.
- **Server-attached advice (rejected).** `_handle_route` adds an `advice` object when
  GraphHopper returns a no-connection error, so the client needs no second request. The cost is that every
  empty route now pays for the scan inside the route call, and the response shape of `POST /route`
  changes for a client that does not expect it.

## Compute on request or ahead of time

The choice is between three ways to run the departure check.

- **On request.** Run the check when a user asks for a route, which is one router call and one spatial
  query for the fixed-route scan.
- **Shared precompute per run.** When a forecast run lands, compute for each road piece and vehicle the steps
  at which the piece is impassable, and store them. A request then reads stored windows and skips the
  depth comparison. No origin or destination is involved, so the work is bounded by roads and steps, not by
  route pairs.
- **Automatic per route.** Compute advice for routes users have not asked about, or push it to them.

| Option | Work done | Wasted work | Latency for the user | Needs |
| --- | --- | --- | --- | --- |
| On request | 1 router call, 1 spatial query, for each request | None | One request time. Unmeasured. | Nothing new |
| Shared precompute per run | One pass over all road pieces for each run, vehicle, and step | Pieces nobody routes over | Lower, since the depth comparison is stored. Unmeasured. | A table or view, plus a hook when a run lands |
| Automatic per route | One check for each route, repeated for each new run | Most routes: nobody reads them | Zero, but only for routes already known | Saved routes, an alert channel, and an opt-in |

**Recommendation: on request.** Three facts drive it.

1. **The request is cheap and small.** The horizon is 2 hours, so a scan covers 9 steps at most. Each request
   makes one router call and one spatial query. No route pair is shared between users, so caching an answer
   for a pair helps only when two users pick the same points. That is an inference, and latency is not
   measured.
2. **Automatic work needs routes the system does not have.** No saved routes, accounts, or alert channel are
   described in the repo pages I read. Precomputing for every origin and destination pair is unbounded, and
   precomputing for known routes needs something that stores them.
3. **The risk of stale advice grows with precompute.** Advice depends on the run. Every new run invalidates
   stored advice, so automatic work repeats on every run, and a stored answer shown after a run change is
   the false reassurance the plan warns about.

The shared precompute is the one worth reconsidering. It is bounded and it does not depend on user
behavior. Build it only if a measurement shows the request-time spatial query is the slow step. The
measurement is the p50 and p95 of the fixed-route scan on the server, next to the router baseline the
blocker already asks for.

A push alert ("your saved route floods at 18:15") is a separate product feature. It needs saved routes
first, and belongs in its own plan.

## Sources

- https://publikationen.bibliothek.kit.edu/1000047759/3569195 (time-dependent route planning with CH, profile queries)
- http://www.vldb.org/pvldb/vol12/p1058-yuan.pdf (query types, reverse time-dependent Dijkstra)
- https://sites.cs.ucsb.edu/~suri/cs231/Rlist/ordaRom.pdf (Orda and Rom 1990, waiting policies)
- https://support.google.com/maps/answer/6291839?hl=en&co=GENIE.Platform%3DDesktop
- https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes
- https://valhalla.github.io/valhalla/api/route/api-reference/
- https://github.com/valhalla/valhalla/issues/5183
- https://github.com/valhalla/valhalla/issues/5616
- https://github.com/valhalla/valhalla/pull/2660
- https://www.fema.gov/sites/default/files/documents/fema_nhp_hurricane-evacuation-studies_fact-sheet_022024.pdf
- https://www.scemd.org/media/1994/annex-a-evacuation-decision-and-response-timeline.pdf
- https://doi.org/10.3390/w12082271
- https://repository.library.noaa.gov/view/noaa/57328/noaa_57328_DS1.pdf
