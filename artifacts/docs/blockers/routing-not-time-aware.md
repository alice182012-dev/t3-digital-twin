---
date_open: 2026-09-25
date_closed: 
type: blocker
status: open
severity: P1
subsystem: floodmap-backend
approaches_tried: 0
approaches_remaining: 3
tags: [blocker, routing, forecast, graphhopper, safety]
related: ["[[map-shows-forecast-not-now]]", "[[route-forecast-query]]", "[[depth-forecast-chart]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-29
---

# Routing checks each road at one moment, not at the time the traveller reaches it

## Description

A route request carries one timestep. The frontend interceptor in `FloodStore.ts`
(`installRoutingInterceptor`) adds the selected `valid_time` and `run` to `POST /route`.
`_handle_route` in `floodmap/graphhopper-flood-road/backend/server.py` builds one `custom_model` from the
flood areas at that timestep (`cached_areas(valid_time, ...)`), and GraphHopper routes with it. Every road
on the route is judged at the same moment.

The user's example: someone leaves now on a 20-minute route. A road reached at minute 15 is dry now but
flooded by minute 15. Today's routing sends them down it.

## Why this matters

This is a safety gap. [[map-shows-forecast-not-now]] moves the map to "now", so the forecast has to show up
somewhere. Routing is where it changes what people do.

## Candidate approaches

None tried.

| Option | How | Effort | Cost and risk |
| --- | --- | --- | --- |
| A. Worst case over the trip | Build the `custom_model` from the deepest water on each road across all timesteps from now to now plus a trip-time bound (for example 1 hour). | S to M | Simple and safe. Too cautious on long trips: it avoids a road that floods after the traveller has passed it. |
| B. Check the arrival time, then re-route | Route with now. Compute the arrival time on each road from GraphHopper's time data. Look up the depth at the timestep for each arrival time. If a road on the route is impassable at arrival, block it and route again. Repeat until the route holds. | M to L | Several GraphHopper calls per route. Needs a limit on repeats. |
| C. Time-dependent routing | Edge weights that depend on arrival time, inside the routing engine. | L | A GraphHopper `custom_model` has no time dimension. This needs engine changes or another engine. The 2026-09-29 survey found no engine that does it off the shelf. On GraphHopper it is a small custom Java module, see "Build plan if we keep GraphHopper". |

Timesteps are 30 minutes apart, so any option has to decide how to map an arrival time to a timestep: the
step at or before it, the nearest step, or the worse of the two around it. (Superseded by the
fifteen-minute cycle for tiles and the flood histogram; this blocker's own scope is unaffected, but a
future implementation should use 15-minute steps, not 30.)

## Research, 2026-09-28

Two independent research passes, one on how production systems (Google Maps, Waze) handle this, one
on the academic time-dependent shortest path (TDSP) literature. Full agent reports are in this
session's transcript; this section is the synthesis.

**Industry practice.** Neither Google Maps nor Waze checks a hazard against the traveller's arrival
time. A hazard (a closure, a flood report, an evacuation zone) is a binary exclusion for as long as
it is active, the conservative choice. Google's own published sophistication (the DeepMind GNN work)
is about predicting travel-time *cost*, not about timing hazard *availability*. Neither product's
public documentation describes anything resembling Option B's route-then-recheck loop as a planning
method; Waze's live re-routing during a trip is the closest analogue, and that only reacts to
conditions changing, it doesn't pre-plan around them.

**Academic literature.** Option C is the best-grounded of the three theoretically. A flood closure
(edge cost becomes infinite) satisfies the FIFO condition that makes time-dependent Dijkstra and A*
exact and no more expensive than plain Dijkstra (Kaufman & Smith 1993), as long as waiting at
intersections is allowed; rising water is FIFO even without that. Kleff, Schulz, Wagenblatt & Zeitz
(SEA 2020, "Efficient Route Planning with Temporary Driving Bans, Road Closures, and Rated Parking
Areas") solves the structurally identical problem (edges forbidden during time windows) at ~1 s per
query. Lämmel, Grether & Nagel (2010) implemented genuine time-dependent flood-arrival routing for
tsunami evacuation in Padang, Indonesia, inside MATSim. Option A is "sound but conservative": correct
in the sense of never sending someone into water, but can return "no route" over a long window when a
timed route would actually work. **Option B has no theoretical backing.** No paper analyzes a
route-then-recheck loop as a planning method; by the literature's own reasoning it has no convergence
guarantee (can oscillate between two routes) and can miss a route that's only valid because of good
timing (a road that floods now but drains before the traveller would arrive gets excluded at the
first pass and never reconsidered).

**Where the two agree.** Both independently proposed the same shape of fix without prompting each
other: bound each road's worst-case check to a time window scoped by *how far into the trip that
segment is*, not one flat window for the whole route (the industry pass calls this "A′"; the academic
pass calls it "a local Option A inside Option C"). Concretely: a segment's worst-case depth check
spans `[earliest possible arrival at that segment, now + trip bound]`, where earliest arrival is
distance from the origin over the fastest plausible speed. A segment close to the route's start only
needs near-term forecast steps; a segment reachable only much later can ignore near-term steps that
will have resolved by the time anyone gets there.

**Caveats a chosen implementation must respect**, regardless of which option:
- **Pick a waiting policy explicitly.** Allowing waiting at intersections keeps flood closures FIFO
  and the theory exact. Forbidding waiting on *receding* water (not rising) makes the problem non-FIFO
  and provably NP-hard (Zeitz 2022). Scope any real time-dependent logic to "may still be flooded
  when I arrive," not "might have to wait for it to drain."
- **Check the whole traversal window per segment**, not just the entry instant: the worst depth across
  every forecast step the traversal actually touches, which is itself a small Option A nested inside
  the windowed check.
- **Re-plan when the forecast updates**, mirroring both Waze's live re-route model and the academic
  literature's two-stage "plan on forecast, revise on new data" pattern. This is not the same as
  Option B's per-request arrival-time loop.
- GraphHopper's `custom_model` weighting has no time parameter (confirmed against GraphHopper's own
  forum: `calcWeight` would need a time argument threaded through the algorithm), and Contraction
  Hierarchies don't support time-dependent weights without a dedicated variant. A′ can be built
  entirely inside the existing `flood_areas.py` mechanism (band the SQL query by distance instead of
  one global `valid_time`) with no GraphHopper engine change. True Option C would mean bypassing
  GraphHopper's CH/LM preprocessing and running plain time-dependent Dijkstra or A* directly, which
  both research passes agree is fast enough at Hanoi's road-network scale but is real engine surgery,
  not a `custom_model` change.

**Recommendation from this research (not yet a product decision):** build A′ (the time-windowed
worst case) inside the existing `custom_model.areas` mechanism, drop Option B entirely (the
literature gives a concrete reason to, not just lack of time), and treat full Option C as a stretch
goal only if A′ proves too conservative in practice.

## Option C engine survey, 2026-09-29

A research subagent checked whether any open-source routing engine supports Option C: a road that is
blocked during a time window, judged at the traveller's arrival time, with the windows refreshed every
15 minutes. Findings come from each project's documentation and issue tracker unless a row says
"unverified". This survey is not a product decision.

**Bottom line.** No engine found does this out of the box. Valhalla comes closest.

| Engine | Time-dependent closure support | Refresh every 15 minutes without a rebuild | Effort against today's stack |
| --- | --- | --- | --- |
| Valhalla (MIT, 3.9.0 released 2026-09-19) | Partial. The route API takes `date_time`, and conditional access (`access:conditional`) is checked against it. | Live speeds come from a `traffic.tar` overlay that updates in place. Predicted speeds are baked into the routing tiles. | High. Different API, tiles instead of a GraphHopper graph, and the `custom_model` flood logic has to be rewritten. |
| GraphHopper (Apache 2.0) | Partial. Conditional access is resolved when the graph is imported, so it depends on the import date. | No. A change needs a re-import. | Lowest. A custom weighting in flexible mode. |
| OSRM (BSD-2) | No. Conditional restrictions are resolved at build time. The maintainers call time-dependent travel times "out of reach" for CH (issue 2695). | Speed updates need `osrm-customize`. No time windows. | Not applicable. |
| CATCHUp and `rust_road_router` (KIT, BSD-3) | Yes for the algorithm. A blocked window can be modelled as a very large travel time. | Not documented. | Very high. Research code with no HTTP server. |

Details behind the table:

- **Valhalla.** A live speed of 0 acts as a closure according to search results, but the speeds
  documentation does not confirm it (unverified). Live data describes the present, not a forecast.
  Discussion 5944 is a 2026 GSoC proposal for per-edge `start_time` and `end_time` closures. It has not
  shipped. Two points are unverified: whether costing evaluates time at each edge's arrival, and how
  live traffic behaves for a future arrival time. Valhalla works from an OSM extract, and no
  Vietnam-specific problem is known.
- **GraphHopper.** The 2020 TARDUR project (Heidelberg University with GraphHopper) promised
  query-time evaluation at arrival time. The survey found no confirmation that a general per-edge
  time-window mechanism exists in master. Pull request 621 covers only restrictions longer than one
  day. The 2020 blog post says time-dependent routing needs flexible mode, not CH or LM.
- **Correction to the survey.** The survey reported the latest GraphHopper release as 11.0 dated
  2024-10-14 and marked the date as stale. The GitHub releases API returns 11.0 published on
  2025-10-14.
- **Not verified or not a fit.** RoutingKit: no time-dependent implementation found. TD-CRP: no open
  implementation found. OpenTripPlanner (LGPL): time-dependent for transit, no street-edge closure
  windows found. pgRouting (GPL-2): `pgr_trsp` handles turn restrictions only. SUMO, MATSim, and OR-Tools
  were not verified. From memory, SUMO and MATSim are simulators with time-varying link states, and
  OR-Tools is a vehicle-routing solver, not a road router (unverified).

The survey's recommendation was to stay on GraphHopper and add a flexible-mode weighting, which reads
per-edge blocked windows from a table that Airflow refreshes every 15 minutes. It also said to confirm
in GraphHopper's source that a weighting can see arrival time. The next section does that.

The section "Valhalla, 2026-09-29" adds a second research pass on Valhalla against our flood
visualization and routing needs.

Sources:

- https://github.com/valhalla/valhalla/discussions/5944
- https://github.com/valhalla/valhalla/releases
- https://valhalla.github.io/valhalla/concepts/speeds/
- https://github.com/valhalla/valhalla/issues/1313
- https://github.com/valhalla/valhalla/pull/2268
- https://github.com/Project-OSRM/osrm-backend/issues/2695
- https://github.com/Project-OSRM/osrm-backend/issues/6168
- https://www.graphhopper.com/blog/2020/02/26/time-dependent-restrictions/
- https://heigit.org/project-tardur-starts-open-source-routing-with-time-dependent-restrictions/
- https://discuss.graphhopper.com/t/ch-and-conditional-access-restrictions/7451
- https://github.com/graphhopper/graphhopper/pull/621
- https://github.com/graphhopper/graphhopper/releases
- https://github.com/kit-algo/catchup
- https://docs.pgrouting.org/latest/en/pgr_trsp.html
- https://docs.opentripplanner.org/en/latest/Changelog/

## Valhalla, 2026-09-29

A second research agent checked whether Valhalla could serve our flood visualization and routing, and why
the team dropped it. It read the old Valhalla code from git history and Valhalla's own documentation and
issue tracker. Its findings are below. This is research, not a product decision.

### Why the switch happened is not recorded

Commit `6394e27` (2026-09-08) has the message "replace valhalla with grasshopper routing logic to embed
flood as a cost factor more effectively". No page in the vault gives a reason beyond that phrase.
ADR-002 in `artifacts/raw/T3-Digital-Twin_Architecture.md` (lines 349 to 362) records the decision and its
consequences, not the cause.

ADR-002 also says the Valhalla proof of concept is "left on disk untouched". That is wrong at HEAD.
Commit `5d1a606` (2026-09-23) deleted `floodmap/valhalla-flood-road-test/`. Commit `6394e27` removed only
its compose service. ADR-002 is in `artifacts/raw/`, which Claude does not edit, so the user should correct
it. The agent read the old code at `6394e27^:floodmap/valhalla-flood-road-test/`.

### How Valhalla was used

- **Costing.** `linear_cost_factors`: line strings with a factor from 1 to 100, each walked onto graph
  edges. Depths of 20 cm or more were also sent as `exclude_locations` points, gated by
  `FLOOD_USE_HARD_EXCLUDES`, which defaulted to false (`backend/server.py:24-25`).
- **Cap.** `MAX_ROUTE_CONSTRAINTS=4` sent only 4 flooded segments per request (`server.py:23`). They were
  chosen by proximity to a first, unflooded baseline route (`server.py:651-663`), so each flood-aware
  request made two routing calls.
- **Edge-walk failures.** The old README says Valhalla 3.5.1 silently ignored `linear_cost_factors`.
  Version 3.6.2 applied them but rejected any feature that failed the edge walk ("Failed to edge walk line
  feature"). In the test, 21 of 26 features were walkable.
- **Tested case.** The baseline route was 1.2 km with a 353 cm maximum depth. The flood-aware detour was
  3.5 km with a 93 cm maximum depth.
- **Vehicles.** `motor_scooter` (20 cm), `auto` (30 cm), and `truck` (50 cm). There was no pedestrian
  profile, and the depth factor was a step function relative to the threshold.
- **No recorded failure.** Neither the README nor `server.py` mentions a problem that stopped Valhalla from
  working.

### What our model needs, against Valhalla

| Requirement | Valhalla | Verdict | Source |
| --- | --- | --- | --- |
| Graded penalty per flood polygon | `exclude_polygons` is a hard exclusion only. Graded `cost_polygons` is an open issue from 2025-05. | No | github.com/valhalla/valhalla/issues/5268, the route API reference |
| Polygon limits | Defaults are 10,000 m total perimeter, 100 vertices, and 50 exclude locations. Our polygons can reach about 1,000 vertices, so the defaults need raising. | Partial | `scripts/valhalla_build_config` lines 412 to 421 |
| Graded penalty by other means | `linear_cost_factors` needs a successful edge walk and edge-aligned lines, not areas. The limit is `max_linear_cost_edges` 50000. | Partial | API reference, old `valhalla.json:216-223` |
| Change costs without a tile rebuild | Per-request options need no rebuild. The live `traffic.tar` overlay is a separate per-edge file. | Partial | `docs/docs/concepts/speeds.md:22-27` |
| Per-vehicle depth thresholds | The costings `motor_scooter`, `motorcycle`, `auto`, `truck`, and `pedestrian` exist. The threshold logic stays in our code, as before. | Partial, workable | Old `flood_utils.py:25-39` |
| Time-aware closures | `date_time` varies speeds. Flood closures stay static per request. | Partial | API reference lines 63 and 368 |
| Return flood-affected segments | The route response has none. `/tile` returns vector tiles of the graph (marked beta), separate from our polygon layer. | No | `docs/docs/api/tile.md` |
| Correct routes with many polygons | Open issues cover an `exclude_polygons` speed-up (4387, 6152), no route with excluded edges (6228), and suboptimal routes from hierarchy pruning (6091). | Unverified at our scale | github.com/valhalla/valhalla/issues |
| Maintenance | Release 3.9.0 on 2026-09-19. Last push 2026-09-28. | Yes | api.github.com/repos/valhalla/valhalla |

### Likely reasons for the switch

Ranked by how well the evidence supports each one.

1. **No graded area penalty.** Valhalla offers a hard exclusion or edge-walked lines. This is the closest
   match to the commit message's "cost factor". Evidence in Valhalla documentation, plus the old README's
   own use of linear factors.
2. **The 4-constraint cap and the two-pass request.** Neither covers a whole flooded city, and linear
   factors need edge-aligned lines. Evidence in the repo (`server.py:23,651-663`).
3. **Edge-walk brittleness, and the silent ignore in 3.5.1.** Evidence in the repo (the old README).
4. **Polygon limits.** The defaults are 100 vertices and 10 km of perimeter. That these limits mattered is
   inference only.
5. **GraphHopper's `custom_model.areas`.** It takes a graded per-area multiplier in each request, and
   `ch.disable` works in the request body. Evidence in the repo ([[graphhopper-backend]]). That this
   drove the decision is inference only.
6. **Tile builds under the old stack.** Inference only.

### Verdict

Valhalla could be adapted in part. Raising the polygon limits is a configuration change. Grading would
need road edges bucketed by band and sent as `linear_cost_factors`, which needs an edge-to-way table and an
edge-walk check on every request. The other paths are a C++ patch to Valhalla or waiting for issue 5268.
Each costs more than staying on GraphHopper, and each throws away the tests built for GraphHopper. The
agent did not recommend adapting Valhalla, and this page agrees.

### Effect on Option C

None. `date_time` varies speeds from predicted or live traffic. Per-request polygons and
`linear_cost_factors` are static, so a closure that starts partway through a trip cannot be expressed.
Valhalla would give the same answer as one `POST /route` per timestep.

### Not verified

- The team's actual reason for the switch.
- Valhalla's performance with hundreds of polygons on Hanoi data.
- Whether any release after 3.9.0 adds graded polygons. Issue 5268 was open when checked, and its
  comments were not read.
- Whether `/tile` output could carry flood attributes without a patch.
- Whether the old `exclude_locations` sampling worked as intended. The old code was not run.

## Build plan if we keep GraphHopper, 2026-09-29

This section plans the build on GraphHopper. It is a plan, not a decision, and nothing is built. It
has two tiers with a measurement between them. Claims about GraphHopper's source were read from
`master` on GitHub on 2026-09-29, where the version in `pom.xml` is 12.0-SNAPSHOT. The pinned image is
`israelhikingmap/graphhopper@sha256:3e79eb33...`, described in [[graphhopper-backend]] as a
12.0-SNAPSHOT build. Its exact source revision is not known, so every claim below about that build is
unverified until it is tested on the pinned image.

### What runs today

- **Profiles.** `graphhopper/config.yml` defines `motorbike`, `car`, `truck`, and `foot`, each backed
  by a `custom_model` file. `profiles_ch` is empty, so no profile has a Contraction Hierarchy.
  `profiles_lm` lists all four profiles, so landmarks (LM) are prepared for each.
- **Request path.** `_handle_route` in `server.py` sets `ch.disable: true` and attaches a
  `custom_model` built by `build_custom_model` from `flood_areas.derive_areas`. That model is a
  `priority` list of `if` and `else_if` rules over `in_<area id>` conditions, with a `multiply_by` of
  0.2, 0.05, or 0 per depth band, deepest band first. The `areas` member holds the flood polygons.
- **Time.** `derive_areas` reads one `forecast_time` from `flood_road_values`. Nothing in the
  `custom_model` carries time.
- **LM likely applies.** In `master`, `Router` builds an LM solver when the profile has LM and the
  request does not set `lm.disable`. It checks that the request's `custom_model` only raises edge
  weights (`FindMinMax.checkLMConstraints`), which the flood bands satisfy. So flood requests are
  probably already routed with LM. That is inferred from `master` and unverified on the pinned build.

### Can GraphHopper see arrival time?

Not through any interface that exists. This confirms and sharpens the survey's unverified claim.

- **`Weighting` has no time parameter.** `calcEdgeWeight(EdgeIteratorState edgeState, boolean reverse)`
  and `calcEdgeMillis(edgeState, reverse)` take an edge and a direction only
  (`routing/weighting/Weighting.java`). `CustomWeighting` reads `distance`, speed, and priority from
  edge properties only.
- **The search label carries weight, not time.** `SPTEntry` has `edge`, `adjNode`, `weight`, `parent`,
  and `deleted`. There is no millisecond field. `Dijkstra.runAlgo` adds `calcEdgeWeight` to
  `currEdge.weight`. Weight is not time, because priority and `distance_influence` add weight
  without adding time.
- **The algorithm could compute time.** `calcEdgeMillis` exists, and the Javadoc says it is meant for
  post-processing on a few thousand edges. Calling it once per expanded edge is possible but not what
  the interface promises (unverified for speed).
- **Which algorithms can know arrival time.** Only a forward search. Unidirectional `Dijkstra` and
  `AStar` expand from the origin, so the arrival time at a node is the sum of edge times along its
  parent chain. `DijkstraBidirectionRef` and `AStarBidirection` also expand backward from the
  destination, where the arrival time at a node is unknown. `RoutingAlgorithmFactorySimple` picks the
  algorithm from the request's `algorithm` field, and an empty value selects `astarbi`, the
  bidirectional one. A request can ask for `dijkstra` or `astar`.
- **Conditional access does not help.** `master` has `foot_temporal_access`, `car_temporal_access`,
  and `bike_temporal_access` encoded values, and `CustomizableConditionalRestrictionsTest` sets
  `datareader.date_range_parser_day` to `2023-08-01` at import. The value is fixed when the graph is
  built, which matches the forum answer in the survey.
- **`custom_model` cannot carry time.** A rule can read an encoded value, an area, or a parameter
  (`p_name`), all fixed for the request.

### Extension points without forking GraphHopper

A custom Java module is enough. It does not need a fork of GraphHopper, only a build that depends on
its jars. Checked in `master`:

1. `GraphHopper.createWeightingFactory()` is `protected`, so a subclass can return a
   `WeightingFactory` that builds a time-aware weighting.
2. `GraphHopper.doCreateRouter(...)` is `protected` and returns a `Router`. `Router` is a public
   class with a `protected createFlexSolver`. `Router.FlexSolver` is a public static class whose
   `createPathCalculator` is `protected`. Today it hard-codes `new RoutingAlgorithmFactorySimple()`,
   so a subclass can supply a different `RoutingAlgorithmFactory`.
3. `Dijkstra.runAlgo` is `protected`, and `fromMap`, `fromHeap`, and `currEdge` are `protected`. A
   subclass can override `runAlgo`, create an `SPTEntry` subclass with a `millis` field, and keep it
   as the label.
4. `GraphHopperManaged` in `web-bundle` calls `new GraphHopper()`. A subclass therefore needs its own
   Dropwizard application class that builds the subclass instead. Stock `graphhopper.sh` and the
   `israelhikingmap/graphhopper` image would be replaced by an image built from our module.

Two points are unverified. First, whether the pinned snapshot has the same visibility and signatures as
`master`. Second, whether `QueryGraphWeighting`, which wraps every weighting for snapped start and
end points, keeps a stateful weighting working. A cleaner path is an algorithm that passes the arrival
time into the weighting before each edge call through a setter on a per-request instance. The router
builds a fresh weighting for each request (`FlexSolver.createWeighting`), so per-request state does not
cross requests.

### Tier A-prime: windowed worst case, no engine change

**What it does.** For each road piece, `flood_areas.py` takes the deepest water over the forecast steps
the traveller could touch that piece, not over one step.

**Algorithm.**

1. The request supplies the origin point, the departure step `t0` (the selected `valid_time`), and the
   vehicle. The backend adds a trip bound `T`. The value is open, see Questions.
2. For each piece in `flood_road_values`, compute `d`, the straight-line distance from the origin in
   EPSG:3405. A straight-line distance never exceeds the route distance, so it gives a safe earliest
   arrival.
3. Earliest arrival is `e = t0 + d / v_max`, with `v_max` the vehicle's fastest plausible speed. Pick
   `v_max` from the profile's speed cap, for example the 120 km/h cap in `motorbike.json`, or a lower
   urban value. A higher `v_max` widens the window and so is more conservative.
4. The window for the piece is the forecast steps from the step at or before `e` (rounded down) to the
   step at or after `t0 + T` (rounded up). This is the "worse of the two around it" mapping, and it
   costs at most one extra step per end. It also covers the traversal time of the piece itself.
5. The piece's depth is the maximum of `depth` over the window. The band is chosen from that maximum,
   with the same vehicle-relative thresholds as today.
6. The rest of the pipeline is unchanged: buffer, union, simplify, and `build_custom_model`.

**Files.** `backend/flood_areas.py` (SQL, `derive_areas` signature, added parameters), `backend/server.py`
(`_handle_route`, `cached_areas`, the origin taken from `body["points"][0]`), and
`backend/test_flood_areas.py`. `scripts/flood_utils.py` needs no change.

**Query shape.** Today each band runs one SQL statement against one `forecast_time`. The windowed
version filters `forecast_time` between the window ends, groups by piece, takes `max(depth)`, and then
applies the band range. The window start depends on `d`, so the statement joins on a per-piece
expression. `flood_road_values` already has a GIST index on `geom_4326` and, since `flood_on_roads`,
a `segment_id`. Query cost is unmeasured.

**Cache.** `cached_areas` keys on `(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)`
with a 30-second TTL. The windowed result depends on the origin, so the key needs the origin, `T`, and
`v_max`. Round the origin to a grid (for example 250 m) so nearby requests share an entry. The hit rate
will fall, so expect more PostGIS queries per route.

**Overlay decision.** [[graphhopper-backend]] says `GET /flood/areas` and `POST /route` share one
derivation so the overlay never disagrees with routing. A-prime breaks that for routing, because the
areas now depend on the origin. Either the overlay keeps showing one timestep and the route shows its
own windowed areas, or `/flood/areas` accepts the same origin. This is a product question.

**Latency risk.** Higher than today, from the extra SQL work and the lower cache hit rate. GraphHopper's
own work does not change. Measure before and after on the server.

**Rollback.** Guard the new path with a request or environment flag. With the flag off, `derive_areas`
runs the single-step query as it does today.

**Cost of being conservative.** A-prime never sends someone into water that could be flooded inside the
window. It can return no route, or a detour, when a timed route would have worked. It also treats a
road that floods at minute 45 the same as a road that floods at minute 5 if both fall inside the window.

### Decision gate between the tiers

Build Tier C-lite only if measurements on A-prime show a real cost. Run A-prime and today's model on a
fixed set of origin and destination pairs, with the flood scenarios from the test plan below and, when
available, real forecast runs. Record for each pair:

1. Whether A-prime returns no route where the arrival-time answer (from a slow offline reference, such
   as a plain time-dependent Dijkstra script in `marie-curie/`) finds a passable one.
2. The detour ratio of A-prime against that reference.
3. The p95 request latency of A-prime.

A starting rule to confirm with the user: build C-lite if A-prime returns no route on more than 10% of
pairs where a passable timed route exists, or if the median detour is more than 25% longer. These two
numbers are proposals, not measurements. If neither holds, stay on A-prime.

### Tier C-lite: arrival-time search in a custom weighting

**What it does.** A forward search carries the arrival time in each label, and a weighting looks up
each edge's depth at that time.

**Design.**

1. **Weighting.** A `FloodTimeWeighting` wraps the vehicle's `CustomWeighting`. It returns the base
   weight, multiplied by the band factor, or infinity when the edge is impassable at the arrival time.
   Because it only raises weights, LM's lower bounds should stay admissible (reasoning from the LM
   constraint check in `master`, unverified by a test). That would let the search keep LM's speed-up.
2. **Algorithm.** A `TimeDependentDijkstra` (or a unidirectional `AStar` with the LM approximator, which
   is unverified) subclasses `Dijkstra`, carries `millis` in its label, and sets the arrival time on
   the weighting before each edge call. Bidirectional search is not allowed, because the backward half
   cannot know arrival time.
3. **Waiting policy.** Pick one explicitly. Option one, sticky closure: an edge counts as impassable
   from its first flooded step until the end of the horizon, even if the water drains. Closures then
   only grow, so an earlier arrival is never worse, and the search is exact without waiting. It is as
   conservative as A-prime on receding water. Option two, arrival-only: the depth at the arrival step
   (or the worst step across the traversal). This is less cautious, but a road that opens later can
   make a later arrival better, which breaks the earliest-arrival rule, so the search becomes a
   heuristic. Start with option one and measure how many routes option two would change. The
   literature point in the research section, that forbidding waiting on receding water is NP-hard,
   applies to option two.
4. **Depth table.** The weighting reads a table indexed by GraphHopper edge id and step, holding depth
   in centimetres.
5. **Edge-id mapping.** `road_segment` pieces are cut per OSM way by length (see [[road-segment-table]]).
   GraphHopper edges are cut at junctions, so pieces and edges do not line up one to one. Two options.
   Sample the depth raster along each GraphHopper edge's geometry, as [[flood-on-roads]] does for pieces,
   after exporting the edge geometry from the graph. Or add `osm_way_id` to `graph.encoded_values`
   (`OSMWayID` exists in `master`, unverified in the pinned build) and join on way and position. The
   first option is independent of how pieces are cut. Edge ids change on every re-import, so tag each
   table with a hash of the graph build and refuse a mismatch.
6. **Publishing.** Airflow gets a task after `9b_load_depth_raster` that samples the run's tiles along the
   exported GraphHopper edges and writes one binary file per run, one depth value per edge per step.
   The file goes to a volume the routing container mounts, or to MinIO. The size depends on the edge
   count of `hanoi-model-area.osm.pbf`, which is not measured. Compute it before choosing the storage.
7. **Reload without restart.** The module memory-maps the newest file and swaps a reference when a new
   file appears, for example by polling for a `latest` pointer file every 30 seconds. Requests in
   flight keep the old mapping until they finish.
8. **Fallback.** Register the time-aware weighting as a separate profile, for example `motorbike_td`.
   `_handle_route` picks it when a flag is on and the depth table is fresh. When the table is missing,
   stale, or its graph hash does not match, the backend sends the request to the plain profile with the
   A-prime `custom_model`.

**Files.** A Java module (Maven) with the `GraphHopper` subclass, the weighting, the algorithm, the
table reader, and a Dropwizard application class. A Dockerfile. `compose.yml` (image and volume).
An Airflow task and script in `scripts/flood_roads/`. Changes in `server.py` for profile selection.

**Latency risk.** Unmeasured. The label carries one extra field and each edge adds a table lookup, so
the search should stay close to a plain unidirectional search. A unidirectional search visits more nodes
than a bidirectional one. Measure p50 and p95 for short, medium, and long Hanoi trips against today's
LM path before deciding. The Kleff et al. figure of about 1 second per query, from the research
section, is for a different implementation and network.

**Cost beyond code.** The routing service changes from a pinned stock image to an image we build. That
means Java code, a build, and tests that this repository does not have today, and the pin policy in
[[graphhopper-backend]] changes with it.

**Rollback.** Turn the flag off, or point the compose service back at the pinned stock image. The
plain profiles and the A-prime path keep working.

### Test and verification plan

Use a synthetic flood on a real Hanoi corridor, built in scratch space under `marie-curie/` with a
throwaway PostGIS, not in the shared database.

| Scenario | Corridor road state | Traveller reaches it at | Today's model | A-prime | C-lite, sticky | C-lite, arrival-only |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Rises before arrival | Dry at step 0, flooded from minute 10 | Minute 15 | Passes (wrong) | Blocks | Blocks | Blocks |
| 2. Rises after passing | Dry until minute 45 | Minute 15 | Passes | Blocks if the window reaches minute 45 (cautious) | Passes | Passes |
| 3. Flooded and drains | Flooded minutes 0 to 20, dry after | Minute 25 | Blocks at step 0 (cautious) | Blocks | Blocks | Passes |
| 4. Far road floods late | Flooded from minute 45, far from the origin | Minute 30 | Passes | Blocks if the window reaches minute 45 | Passes | Passes |

The table states expected results from the designs above. They are not observed. Run each scenario for
`motorbike` and `car`, with a detour available and with no detour, to test the "no route" response. For
each result, check that the route never crosses an edge that is impassable at its arrival step, using
an offline check that re-walks the returned path with per-edge millis.

**Latency budget.** Set it from a baseline. First measure p50 and p95 of today's `POST /route` on the
server (flexible mode with LM), then require A-prime and C-lite to stay within a factor the user picks.
No budget is set yet.

### Questions for the user

1. Trip bound `T`: one hour, or tied to the route length?
2. `v_max` for the earliest-arrival estimate: the profile cap or a lower urban speed?
3. Should the map overlay show one timestep while the route uses windowed areas, or should the overlay
   take the same origin and window?
4. Is sticky closure acceptable as the first waiting policy?
5. Are the gate numbers (10% no-route pairs, 25% detour) the right starting point?
6. Is a custom GraphHopper image, with Java code we own, acceptable for the routing service?
7. Should the exact source revision of the pinned image be found first (unverified visibility and
   signatures above)?

## Questions

1. Which option, or A first and B later? Research above suggests A′ (a time-windowed worst case, not
   flat) over plain A, and against building B at all.
2. What upper bound on trip time should option A (or A′) use?
3. How should the answer show in the UI? For example, "This road floods at 21:40" on the route.

## Related topics

- [[map-shows-forecast-not-now]]
- [[route-forecast-query]] and [[depth-forecast-chart]]
- [[graphhopper-backend]]

## Status history

- **2026-09-25, open.** Logged at the user's request while working on [[map-shows-forecast-not-now]].
  Routing should use the time the traveller reaches each road.
- **2026-09-28, open.** Researched how production systems and academic literature handle this before
  any implementation choice. See Research above. Still open: the user's decision on which approach to
  build and the trip-time bound.
- **2026-09-29, open.** Added the Option C engine survey (no engine supports it off the shelf, Valhalla
  is the closest partial fit) and a build plan for staying on GraphHopper: Tier A-prime, a decision gate,
  and Tier C-lite. GraphHopper's `Weighting` and `SPTEntry` carry no arrival time, so Option C needs a
  custom module, not a `custom_model`. No approach tried yet.
- **2026-09-29, open.** Added "Valhalla, 2026-09-29". The reason for the 2026-09-08 switch is not recorded
  (commit `6394e27` gives only "embed flood as a cost factor more effectively"). The likeliest cause is that
  Valhalla has no graded area penalty. Adapting Valhalla is possible but not worthwhile, and it does not
  change the Option C answer. The Valhalla proof of concept was deleted in `5d1a606`, so ADR-002's "left on
  disk" needs correcting in `artifacts/raw/`, which the user owns.
