---
date_drafted: 2026-10-08
type: user-story
us_id: "US-092"
story_label: "3"
epic: "[[EP-14-routing-paper-experiments]]"
status: Not started
priority: P2
estimate: M
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Test how the vehicle limits change the result"
---

# US-092 Test how the vehicle limits change the result

As the author of Paper A, I want a sensitivity analysis of the motorbike and truck limits, so the paper answers "why
20 and 35 cm" with a measured range and not with a source that does not exist.
Given the harness and the pair set of `US-091`, when the motorbike limit runs over 10, 15, 20, 25, 30, and 40 cm, the
truck limit over 25, 30, 35, 40, 50, and 60 cm, and the precaution fraction of D-021 at 0.25, 0.5, and 0.75 of the
limit, then a result file records for each setting the closed road length, the share of origin and destination pairs
that still have a route, the mean detour, and the violation rate of `US-091`. It also holds a regret table: plan
with limit A, judge against limit B. A short list names the settings where the conclusion changes. The file states
whether Hanoi shows the "no noticeable change" that Kasmalkar reported over 1 to 12 inches.
The provenance of the four limits is already searched (`marie-curie/vehicle-limit-sources.md`, 2026-10-08). This story
does not repeat the search. It copies the verdicts into the result file: car 30 cm supported for a small passenger
car, motorbike 20 cm partly supported, truck 35 cm no source, foot 40 cm partly supported and conservative.
Copy the note out of `marie-curie/` first, because that folder is disposable.
Priority: P2. Status: Not started. Estimate: M. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: `US-091` (its harness and its pair set), so the two stories sit in one sprint and the second starts
when the first has a working harness. If the harness slips, this story moves to Sprint 13 of [[SP-04-frontend-recheck|sprint-plan-4]]
(the rule is in the Risks table of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]).
Evidence: None yet.

## Status history

- **2026-10-09, active.** The real-graph runner `scripts/routing_experiments/real_run.py` (`7049880`) ran the limit sweep on the 3 copied tables of the first replay: 30 node pairs inside the model border, 21 (table, step) settings, graph hash `8c13d884`. The result file is `marie-curie/real_run_replay1_seed1.json`. Plan limits 20, 30, 35, and 40 cm kept 90 to 97 percent of pairs routable. In 20 of the 21 settings the conclusion differs from the baseline setting, so the three old tables are too few and too dry to settle it. The story stays `In progress` until the tables of the second replay exist.
- **2026-10-09, preliminary storm run.** `real_run.py` ran from 21:55 to 22:17 +07 on 30 tables of the second replay (13:00 to 21:15 +07), 30 node pairs, departure steps 0 and 4, seed 1, 5 workers: 60 (table, step) settings, graph hash `8c13d884`. Result file: `marie-curie/real_run_replay2_prelim_seed1.json` (469 kB). The runner finished without a change. The file's baseline is the first setting (`storm|20261009T130000|0`, before the rain), so its "conclusion changes against the baseline" list holds 58 of the other 59 settings, which is expected and says little. The story needs the final run on the full table set after 00:45 +07 on 2026-10-10, with a baseline taken inside the storm, before it reaches `Done`.

