---
date_drafted: 2026-10-08
type: user-story
us_id: "US-092"
story_label: "3"
epic: "[[EP-14-routing-paper-experiments]]"
status: Reviewed
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
Priority: P2. Status: In progress. Estimate: M. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: `US-091` (its harness and its pair set), so the two stories sit in one sprint and the second starts
when the first has a working harness. If the harness slips, this story moves to Sprint 13 of [[SP-04-frontend-recheck|sprint-plan-4]]
(the rule is in the Risks table of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]).
Evidence: None yet.

## Status history

- **2026-10-09, active.** The real-graph runner `scripts/routing_experiments/real_run.py` (`20787b2`) ran the limit sweep on the 3 copied tables of the first replay: 30 node pairs inside the model border, 21 (table, step) settings, graph hash `8c13d884`. The result file is `marie-curie/real_run_replay1_seed1.json`. Plan limits 20, 30, 35, and 40 cm kept 90 to 97 percent of pairs routable. In 20 of the 21 settings the conclusion differs from the baseline setting, so the three old tables are too few and too dry to settle it. The story stays `In progress` until the tables of the second replay exist.
- **2026-10-09, preliminary storm run.** `real_run.py` ran from 21:55 to 22:17 +07 on 30 tables of the second replay (13:00 to 21:15 +07), 30 node pairs, departure steps 0 and 4, seed 1, 5 workers: 60 (table, step) settings, graph hash `8c13d884`. Result file: `marie-curie/real_run_replay2_prelim_seed1.json` (469 kB). The runner finished without a change. The file's baseline is the first setting (`storm|20261009T130000|0`, before the rain), so its "conclusion changes against the baseline" list holds 58 of the other 59 settings, which is expected and says little. The story needs the final run on the full table set after 00:45 +07 on 2026-10-10, with a baseline taken inside the storm, before it reaches `Done`.
- **2026-10-10, active.** The depth tables of the second replay are copied from the worker to `marie-curie/edge_tables_replay2_final_2026-10-10/` (48 files, 45 of the second replay `20261009T130000` to `20261010T010000` and 3 of the first, SHA-256 equal to the worker's). The four missing tables (`20261009T194500` to `20261009T203000`) are not a fault: the gate skipped those four runs (19:30 to 20:15 +07). The final full-table run uses these files.
- **2026-10-10, correction.** The entry above calls the four missing tables "not a fault". The user corrected this: they are the P0 blocker [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]], because the flood stands after the rain stops. The final run waits for `US-101`.
- **2026-10-10, active.** The final run on the current tables started at 01:49 +07 on the Mac only, at the user's choice (next action 1, option a): `marie-curie/edge_tables_replay2_final_2026-10-10/`, the 45 tables of the second replay (`20261009T130000` to `20261010T010000`, with the 4 missing tables named in [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] and a cold start at 20:30 +07), 30 pairs, departure steps 0 and 4, seed 1, 5 workers. Result file: `marie-curie/real_run_replay2_final_seed1.json`. The result must name the gap and the cold start.
- **2026-10-10, carried from the retired TODOS note.** The cost band is replaced by the precaution fraction (D-021), swept at 0.25, 0.5, and 0.75 by `sweep_fraction` in `scripts/routing_experiments/precaution.py`.
- **2026-10-10, final run on the 12-hour data (result).** `marie-curie/real_run_replay2_final_seed1.json`: the 45 tables, 30 pairs, departure steps 0 and 4, seed 1, 90 (table, step) settings, vehicle limits 20 (motorbike), 30 (car), 35 (truck), and 40 cm (foot), graph hash `8c13d884`. Every pair is reachable on the dry graph. Planning with a lower limit closes more road and finds fewer routes: mean closed length 94.7 km at 20 cm, 63.1 at 30, 52.9 at 35, and 45.9 at 40, route share 0.915, 0.965, 0.969, and 0.970, and mean detour 101 s, 88 s, 74 s, and 65 s. Violation rate when a route is planned and judged at the same limit: 1.9 percent (20 cm), 1.3 (30), 1.3 (35), and 1.0 (40), with a highest setting of 10.3 percent. The regret of planning at one limit and judging at a lower one is large: planning at 40 cm and judging at 20 cm gives 0.647 of the routes unsafe for the lower limit, 40 judged at 30 gives 0.483, 35 judged at 20 gives 0.605, and 30 judged at 20 gives 0.502. Planning at a lower limit than the judge costs nothing in safety (regret 0 to 0.002). The conclusion about which limit is best changes with the setting in 88 of 90 settings (violations change in 69, the ranking in 78). Precaution fraction (D-021): 0.25 gives 88.2 percent of recommended routes under the precaution depth with a mean extra time of 105 s, 0.5 gives 94.1 percent and 50 s, and 0.75 gives 98.7 percent and 21 s. Limits of this result: 30 pairs, one storm, free-flow arrival times, and the depths are 3Di output on the model grid.
