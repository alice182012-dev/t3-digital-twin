---
date: 2026-10-09
type: concept
status: active
tags: [routing, sticky-c-lite, proof, fifo, paper, sprint-12]
related: ["[[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]]", "[[sticky-routing-reference]]", "[[graphhopper-backend]]", "[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[BL-011-routing-not-time-aware|routing-not-time-aware]]", "[[paper-handoff-routing-and-system]]"]
last_updated: 2026-10-09
---

# Sticky-closure proof

This page proves that the sticky-closure forward search is exact. It is Story 1 (`US-090`) of
[[EP-14-routing-paper-experiments|US-090-093-routing-paper-experiments-stories]]. It turns the sketch in Question 3 of
`marie-curie/idea-routing-paper-reviewer-questions.md` into a definition, a lemma, and two theorems, and it
ties each step to the code that implements it.

The rule has two implementations, and the page covers both:

- `StickyClosure.closing_step` and `earliest_arrival` in `scripts/routing_reference/sticky_reference.py`.
  The reference search orders by arrival time.
- `StickyClosure.closed` in `java/time-aware-routing/src/main/java/com/graphhopper/timeaware/StickyClosure.java`
  and `TimeAwareDijkstra` beside it. The engine search orders by the profile's weight, not by time.

## Notation

The following symbols are used throughout:

- The forecast steps are at times `s_0 < s_1 < ... < s_(K-1)`. A real run has `K = 8` steps, 900 s apart.
- `t0` is the departure that the rule is built with.
- `d_e(k)` is the depth of edge `e` at step `k`, in cm. `L` is the vehicle's limit, in cm.
- `m` is the margin. It is 600 s in both implementations (`DEFAULT_MARGIN_S` and `DEFAULT_MARGIN_MS`).
- `tau_e >= 0` is the travel time of edge `e`. It does not depend on the time of day.
- An arrival `a` at an edge is the time the traveller enters that edge.

Both implementations close edge `e` for an arrival `a` when this holds:

> some step `k` has `t0 <= s_k <= a + m` and `d_e(k) >= L`.

The Python loop at `closing_step` (line 70) and the Java loop at `closed` (line 48) test exactly this
condition. Each one stops at the first step past `a + m`, skips a step before `t0`, and closes on the first
remaining step whose depth is at or above the limit.

## Part 1. The closing time of an edge

**Definition.** The closing time of edge `e` for a query that departs at `t0` is the earliest step time at or
after the departure where the depth reaches the limit:

    c(e) = min { s_k : s_k >= t0 and d_e(k) >= L }

When no such step exists, `c(e) = +infinity`.

**Claim.** Edge `e` is closed for arrival `a` if and only if `a >= c(e) - m`. So the edge is open for every
arrival before `c(e) - m`, and closed for every arrival from `c(e) - m` on, with that instant included.

**Proof.** Suppose the edge is closed for `a`. Then some step `s_k` has `s_k >= t0`, `d_e(k) >= L`, and
`s_k <= a + m`. That step is in the set that defines `c(e)`, so `c(e) <= s_k <= a + m`.

Now suppose `c(e) <= a + m`. Then `c(e)` is finite, so `c(e) = s_k` for some step with `s_k >= t0` and
`d_e(k) >= L`. That step also has `s_k <= a + m`, so the rule closes the edge. Both directions hold, and
`c(e) <= a + m` is the same as `a >= c(e) - m`.

The sketch in the reviewer-questions note has no margin. It is the case `m = 0`, where the edge is open before
`c(e)` and closed from `c(e)` on. The margin moves the switch 10 minutes earlier, so a traveller does not enter
a road in the 10 minutes before it floods. If `c(e) - m <= t0`, the edge is closed for the whole query.

## Part 2. The FIFO lemma

The arrival function of edge `e` gives the time the traveller leaves `e` when entering it at `a`:

    f_e(a) = a + tau_e    if a < c(e) - m
    f_e(a) = +infinity    otherwise

**Lemma (FIFO).** For every edge `e`, `f_e` is non-decreasing. For any two arrivals `a <= b`,
`f_e(a) <= f_e(b)`. Also `f_e(a) >= a`.

**Proof.** Take `a <= b`. If `b < c(e) - m`, then `a < c(e) - m` too, and
`f_e(a) = a + tau_e <= b + tau_e = f_e(b)`. Otherwise `f_e(b) = +infinity`, which is at least any value of
`f_e(a)`. The second statement follows from `tau_e >= 0`.

This is the first-in, first-out (FIFO) property. Entering an edge later never leads to leaving it earlier. The
infinite values do not break it, because once an edge is closed it stays closed for every later arrival in the
query. The Java test `closureOnlyGrowsWithArrivalTime` in `StickyClosureTest.java` checks this minute by minute.

Two facts follow by composing edge functions along a path:

1. The arrival function of a path is non-decreasing. Waiting at a node never gives an earlier arrival at the
   destination, so the search needs no waiting policy.
2. A route that repeats a node can drop the loop. The traveller then reaches the repeated node no later. By the
   lemma, every edge after it is entered no later, so each one is still open and the end time is no later.
   An earliest route can therefore always be taken as a simple path.

## Part 3. The forward search is exact

### Theorem 1: the reference search

**Theorem 1.** `earliest_arrival(graph, origin, destination, rule)` returns `None` exactly when no route from
`origin` reaches `destination` without entering a closed edge. Otherwise it returns a route that enters no
closed edge and whose end time `end_s` is the least over all such routes.

Let `D(v)` be the least arrival time at node `v` over all routes from the origin that enter no closed edge. The
search keeps a tentative time `best[v]` and a heap of `(time, node)` entries. It settles a node when it pops an
entry that is not stale (`time == best[v]`), and only then relaxes the node's out-edges.

**Proof.** Every value in `best` is the end time of a real route, because the search only relaxes an edge that
`is_closed` reports open at the tail's settled time. So `best[v] >= D(v)` always.

Suppose node `v` is settled with `best[v] > D(v)`. Take a route `u_0 = origin, u_1, ..., u_k = v` that reaches
`v` at `D(v)`, with entry times `alpha_0 = t0` and `alpha_(i+1) = f(alpha_i)` along its edges. The times
`alpha_i` do not decrease, because each `tau >= 0`. Let `i` be the largest index whose node `u_i` was already
settled with `best[u_i] <= alpha_i`. The origin qualifies at `i = 0`, and `i < k`.

When `u_i` was settled, the search relaxed the edge to `u_(i+1)` at time `best[u_i] <= alpha_i`. By the lemma,
that edge's arrival function gives at most `alpha_(i+1)`, which is finite, so the edge was open and
`best[u_(i+1)]` became at most `alpha_(i+1)`. A heap entry with that key was pushed. By the choice of `i`,
`u_(i+1)` has not been settled at a time at or below `alpha_(i+1)`, so that entry has not been popped. Its key
is at most `alpha_(i+1) <= D(v) < best[v]`, yet the heap popped `v`'s entry first. That contradicts the order
of the heap, so `best[v] = D(v)` when `v` is settled.

The search stops when it settles `destination`, so `end_s = D(destination)`. A popped key is never smaller than
an earlier one, and every relaxed arrival is at least its key, so a settled node's time never drops later and
the route rebuilt from `via` matches the times it records. If the heap empties first, no route exists, and the
function returns `None`.

The test `test_the_search_matches_brute_force_on_random_graphs` checks Theorem 1 on 300 random graphs against
an exhaustive search over simple paths. The second fact after the lemma is why simple paths are enough.

**Cost.** Each node is settled once, and each edge is relaxed once from its settled tail. Each relaxation calls
`is_closed`, which scans at most `K` steps. The search costs the work of a static Dijkstra search plus `K`
step reads per edge, with `K = 8`. That is the same order as a static search.

The literature says the same. Kaufman and Smith (1993), entry S03 of
`marie-curie/lit-review-flood-routing/sources.md`, state in their abstract that "under consistency, the
time-dependent fastest path can be calculated with exactly the same computational complexity as for static
fastest paths". Consistency is their name for FIFO. Bast et al. (2016), entry S10, write that "Dijkstra's
algorithm still works [65] as long as later departures cannot lead to earlier arrivals". The review read the
full text of Bast et al., but only the abstract of Kaufman and Smith. Any claim from Kaufman and Smith beyond
that quoted sentence is unchecked.

Dean (2004), entry S06, is about waiting policies. The review opened its abstract only, which says that waiting
"is constrained by a (potentially time-varying) waiting policy". Bast et al. cite it as reference [69], among
the scenarios "besides FIFO with no waiting at vertices". The page cites Dean only for that point: waiting
policies are a studied part of the model, and the sticky rule needs none. No theorem from Dean's full text is
used here, and none was checked.

### Theorem 2: the engine search

`TimeAwareDijkstra` orders its heap by the profile's weight, which is not the travel time. A node can hold
several labels `(weight, elapsedMs)`. The method `keep` (line 103) drops a label only when another label at the
same traversal id is no heavier and no later.

**Theorem 2.** Suppose every edge weight and turn weight is non-negative and the search runs to the end,
without reaching `maxVisitedNodes` or the timeout (line 69). Then the first label popped at the target (line
70) has the least weight among all routes that enter no closed edge at their own entry times.

**Proof.** First, dropping a dominated label loses nothing. Let label `(w, t)` and label `(w', t')` sit at the
same traversal id, with `w <= w'` and `t <= t'`. Take any continuation that is feasible from `(w', t')`. From
`(w, t)` the same continuation enters each edge no later, by the lemma applied edge by edge, so each edge is
still open. The turn costs are the same, because the traversal id fixes the incoming edge. The weights do not
depend on time, so the continuation adds the same weight. Its total from `(w, t)` is therefore no heavier.

Second, the heap order finds the lightest route. Take a lightest feasible route `P*` with weight `W*`. At any
moment before the target is popped, the heap holds a label that dominates some prefix of `P*`, with a key of at
most `W*`. This holds at the start, and each pop either extends that prefix or leaves a dominating label behind.
Weights are non-negative, so no label at the target with weight above `W*` is popped before that label.

When the weight is the travel time, two labels at one node are always ordered the same way on both values, so
each node holds one label and Theorem 2 reduces to Theorem 1. The test
`theSearchMatchesBruteForceOnRandomGraphs` in `TimeAwareDijkstraTest.java` checks the engine against an
exhaustive search.

**Cost.** Theorem 2 gives no polynomial bound. The number of labels kept at a node is the size of a set of
labels where none dominates another, and the page does not bound it. The same-order claim of Theorem 1 applies
to the engine only when the weight is the travel time.

## Part 4. The step-boundary cases

Each case follows from the claim in Part 1. The tests are in `scripts/routing_reference/test_sticky_reference.py`
unless the row names a Java file. `US-090` added the first and third Python tests. Each was run against a
mutated copy of `sticky_reference.py` and failed there before it passed on the real rule.

| Case | What the rule does | Test |
| ---- | ------------------ | ---- |
| An arrival exactly on a step | The step counts, because `s_k = a <= a + m`. With `m = 0`, an arrival at 900 s closes a road wet at 900 s, and an arrival at 899 s does not. | `test_an_arrival_exactly_on_a_step_counts_that_step`. Java: `aStepAtTheDepartureCounts` in `StickyClosureTest.java`. |
| The window end exactly on a step | The end is included. A step at exactly `a + m` closes the road. | `test_the_end_of_the_window_is_included`. Java: `theEndOfTheWindowIsIncluded`. |
| A departure between two steps | The rule ignores the step before `t0` and counts every later step inside the window. The engine first floors the requested departure to the step that contains it (`TimeAwareRouter.floorToStep`, line 96), so the step that contains the departure counts there. | `test_a_departure_between_two_steps_ignores_the_step_before_it`. Java: `aDepartureBetweenStepsCountsTheStepThatContainsIt` in `TimeAwareRouterTest.java`. |
| A depth equal to the limit | The road closes, because the test is `d_e(k) >= L`. | `test_a_depth_equal_to_the_limit_closes_the_road`. Java: `aDepthEqualToTheLimitClosesTheRoad`. |
| A road that drained before the departure | The water is ignored, because steps before `t0` are skipped. | `test_water_that_drained_before_departure_does_not_close_the_road`. Java: `waterThatDrainedBeforeDepartureDoesNotCloseTheRoad`. |

The reference and the engine differ in the third row. To compare them, call the reference with the engine's
floored departure, as `check_crossings` in `scripts/routing_proof/routing_proof.py` does (lines 219-224).

## Part 5. The landmark heuristic

The engine does not use landmarks. `TimeAwareRouter` sends every time-aware request to a flexible solver that
runs `TimeAwareDijkstra`, which is a plain label-setting search with no lower bound. Its class comment says why.
Landmarks and contraction hierarchies precompute bounds and shortcuts that do not know the time.

What is shown is narrower. `LandmarkLowerBoundTest` (`US-049`) prepares landmarks with the stock speed
weighting, then routes with a weighting that only raises edge weights, or closes some edges by giving them an
infinite weight. On 10 random graphs, no landmark estimate exceeds the real weight, and landmark A* finds the
same weight as Dijkstra. A third test lowers the weights and confirms that the check catches the broken bounds.

So landmark bounds stay valid for a static weighting that only raises weights. The sticky rule is not a static
weighting, because whether an edge is open depends on the arrival time. A landmark bound that ignores closures
is still a lower bound, since closures only remove routes. No test checks a time-aware landmark search, and the
page does not claim that one would be correct or faster.

## Part 6. What the proof does not say

The proof has these limits:

- It does not solve the problem of Kleff et al. (entry S01). Their closures are time windows that reopen, with
  waiting allowed only at parking areas, and that problem is NP-hard. The sticky rule changes the model so that
  no road reopens inside a query. The proof is about that changed model.
- It is exact for the sticky rule, not for the true arrival-time rule. The true rule would let a traveller
  enter a road that flooded earlier and drained before the traveller reaches it. The sticky rule keeps that
  road closed, so it can report no route, or a longer route, where the true rule has a shorter one. How often
  that happens is not measured here.
- It treats the depths as given. The depths are 3Di model output, and the proof says nothing about their
  accuracy or about the choice of the vehicle limits.
- It says nothing about the depth between two steps. The rule reads only the depths at the step times.
- Theorem 2 holds only when the engine search runs to the end. If it reaches `maxVisitedNodes` or the timeout,
  it returns no route, even when one exists.
- It gives no polynomial bound for the engine's weighted search (Theorem 2).
- It covers times measured from the departure that the rule is built with. The engine builds its rule with the
  floored departure and counts the elapsed time of each label from that floored step
  (`closure.departureEpochMs() + enterMs` in `TimeAwareDijkstra.java`, line 94). The real entry time is later
  by `delta`, the gap between the requested departure and the floored step, where `0 <= delta < 900 s`. Measured
  against real time, the margin is `m - delta`, which is negative when `delta > 600 s`. For example, take a
  road that is wet from the step at 1,800 s, a departure requested at 840 s and floored to 0 s, and an entry
  1,000 s into the trip. The engine checks the window `[0, 1600]` and admits the road. The real entry is at
  1,840 s, after the road is wet, and the window `[0, 2440]` closes it. The proof holds for the engine's own
  clock, but not for the requested departure. `check_crossings` walks routes from the same floored departure,
  so it cannot detect this case.
