---
date_drafted: 2026-10-08
type: user-story
us_ids: ["US-090", "US-091", "US-092", "US-093", "US-099", "US-100"]
status: draft
subsystem: routing, paper
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[paper-handoff-routing-and-system]]", "marie-curie/idea-routing-paper-reviewer-questions.md", "marie-curie/vehicle-limit-sources.md", "[[SP-04-frontend-recheck|sprint-plan-4]]", "[[sticky-routing-reference]]", "[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[EP-13-rain-replay-test-environment|rain-replay-test-environment-stories]]", "[[EP-10-routing-first-consumer|routing-first-consumer-stories]]", "[[schedule-routing-paper-experiments-and-move-frontend]]"]
tags: [user-story, epic, routing, paper, experiments, sprint-12]
---

# Epic: routing paper experiments

Four experiments that Paper A (routing) needs before its Results section can be written. They answer the three
questions a reviewer would ask in `marie-curie/idea-routing-paper-reviewer-questions.md` (Questions 1, 2, and 3). The
handoff [[paper-handoff-routing-and-system]] lists them as work items P1 to P4. Those names are working names only. Each
story has its own `US-nnn`.

All four are in Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. The user decided on 2026-10-08: "We need to finish the routing first."
Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]], needed because the base shape has no per-row scheduling field (`.claude/CLAUDE.md`, rule 2). A
story reaches `Done` only with evidence and numbered details, recorded here and in `sprint-plan-3.md`. These are
backend and analysis stories with no UI, so the evidence is the verbatim command output rendered to an image, with a
caption that gives the capture time and host.

## Rules that apply to every story here

1. Name the storm behind every result. The real 2026-09-16 IMERG replay (`scripts/rain_events/hanoi_20260916_storm.csv`,
   12 hours, 53.88 mm, peak 8.73 mm/h) is real rain. The constant 50 mm/h storm of 2026-10-02 is synthetic. A result
   that mixes both says so, and a table row names its storm.
2. The depths are 3Di model output, not observations. A violation rate is a rate in the model driven by that rain. No
   result is described as a measured rate of drivers meeting closed roads.
3. Every coordinate stays inside the model border (`.claude/CLAUDE.md`, "Test points stay inside the model border").
   The pair set drops a pair that gives `Cannot find point` and counts the drops.
4. The vehicle limits (motorbike 20 cm, car 30, truck 35, foot 40) are policy parameters. No result calls a limit
   "safe". `VEHICLE_PROFILES` in `flood_utils.py` is the one owner of the deployed values (`US-074`). An experiment
   passes a limit as a parameter and never edits that file.
5. Where the depth comes from is stated in each result. The edge depth table keeps only the newest 3 runs
   (`EDGE_TABLE_KEEP_RUNS=3`), so the copy of the tables of a replay must be made before the replay's retention
   removes them. `flood_road_values` has no retention but is keyed by road segment and not by graph edge.

- [[US-090-write-the-fifo-lemma-and-the-correctness|US-090]] Write the FIFO lemma and the correctness proof of the sticky-closure forward search. Story 1.
- [[US-091-measure-how-often-a-single-timestep-route|US-091]] Measure how often a single-timestep route meets a closed road on arrival. Story 2.
- [[US-092-test-how-the-vehicle-limits-change-the|US-092]] Test how the vehicle limits change the result. Story 3.
- [[US-093-measure-how-often-the-sticky-rule-gives|US-093]] Measure how often the sticky rule gives no route or a longer route than an arrival-only reference. Story 4.
- [[US-099-run-the-simple-path-arrival-only-search-on-the-real|US-099]] Run the simple-path arrival-only search on the real graph and record its exact rate and runtime. Story 5.
- [[US-100-decide-between-option-a-and-sticky-closure|US-100]] Decide between option A closure and sticky closure for a vehicle already on the route. Story 6.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-14-routing-paper-experiments-history|the archived history]]. This section keeps plan-level changes only.

- **2026-10-08, draft.** Written at the user's request: "From P1-P4 lets move them to sprint 12, and the front end can be
  sprint 13. We need to finish the routing first." The four stories come from the work items P1 to P4 of
  [[paper-handoff-routing-and-system]]. P5 (open the Vu 2024 report) is replaced by the source search of 2026-10-08, so
  it has no story. IDs `US-090` to `US-093`, in the order P1, P2, P3, P4.
- **2026-10-09, active.** Stories 5 and 6 (`US-099`, `US-100`) added for [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]], at the user's list of next steps: run option A on the real graph first, then decide between option A and sticky closure. Both are in Sprint 12.
