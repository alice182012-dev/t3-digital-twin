---
date_drafted: 2026-10-08
type: user-story
us_id: "US-093"
story_label: "4"
epic: "[[EP-14-routing-paper-experiments]]"
status: Not started
priority: P2
estimate: S
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Measure how often the sticky rule gives no route or a longer route than an arrival-only reference"
---

# US-093 Measure how often the sticky rule gives no route or a longer route than an arrival-only reference

As the author of Paper A, I want the cost of sticky closure measured, so the paper states how conservative the rule
is with a number.
Given random origin and destination pairs inside the model border and the real depth tables of the replay, when the
sticky route and an arrival-only route are computed for each pair, vehicle, and departure step, then a result file
records the share of cases with no sticky route where an arrival-only route exists, the share with a longer sticky
route, and the distribution of the extra time, by vehicle and storm stage.
The arrival-only rule closes a road only if its depth at the arrival step reaches the limit. `sticky_reference.py`
does not have this rule today. The story adds it as a second search that keeps several labels per node, because
the arrival-only function is not FIFO. If that search needs more than a label-correcting variant of
`earliest_arrival`, the estimate grows from S to M, and the first hour of work decides it. The decision goes in
Status history.
This is the backlog row "Measure how many routes arrival-only closure would change" of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], converted
into a story. The row said it needed the engine shipped first. The engine is deployed behind the flag (`US-052`,
`Done`), and the sticky side can come from the reference with a real table, so only the arrival-only search and the
depth tables are missing.
Priority: P2. Status: Not started. Estimate: S. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: `US-047` (the reference), `US-050` (the engine, for a cross-check of the sticky side on a sample of
pairs), the depth tables of the 12-hour replay (rule 5), and the pair sampler of `US-091` if it is ready. The sampler
can be copied if not.
Evidence: None yet.
Blocker tracking: [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

## Status history

- **2026-10-09, active.** The real-graph runner ran the sticky versus arrival-only comparison on the 3 copied tables: all 2,520 comparisons (30 pairs, 21 settings, 4 vehicles) came back `INEXACT`. The arrival-only search in `scripts/routing_reference/arrival_only.py` keeps distinct arrival times per node, and on a graph where every road is open both ways the cycles fill the cap of 16 labels per node before the destination is reached. Caps of 64 and 256 stay inexact and take 7 s and 35 s per pair. No share of "no route" or "longer route" is reported. Fixing it needs a decision on the reference (for example, allow only simple paths, or add a dominance rule), which changes what "arrival-only" means in the paper. The story stays `In progress`.
