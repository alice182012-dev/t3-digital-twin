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
