---
date_drafted: 2026-09-29
type: user-story
us_id: "US-051"
story_label: "R6"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: S
sprint: 9
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Add the `truck` and `foot` time-aware profiles"
---

# US-051 Add the `truck` and `foot` time-aware profiles

As a truck driver or a pedestrian, I want the same timing check for my mode, so the four modes behave alike.
Given Story R5's engine, when `truck` and `foot` requests run on the synthetic scenarios, then each uses its
own depth limit (35 cm and 40 cm) and passes the checker.
Priority: P1. Status: Done. Estimate: S. Sprint: 9 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]). Dependencies: Story R5.
Built on 2026-10-05, tests first. `td_limit_cm` 35 for `truck` and 40 for `foot` in `config.yml`. The engine needed no change, because it reads the limit from the profile. Tests: each of the four vehicles at depths 15, 25, 32, 37, and 45 cm through `route()` and through the search, a depth equal to the limit closes the road, `ScenarioReport` now runs 32 runs (4 scenarios, 4 vehicles, with and without a detour) and passes, and a test in each language keeps `config.yml` equal to the report's limits and to `flood_utils.py`. The blocker that stopped a `foot` profile (`graphhopper-vehicle-profile-rejection`) was `resolved` on 2026-09-23 and the profile is in `config.yml`.
Evidence: ![[us-051-scenario-check-2026-10-07.png]]
Details:
1. `java/time-aware-routing/scenario-check.sh` ran on host ADMIN on 2026-10-07 against the image built from `modular`: 32 of 32 runs (4 scenarios, motorbike/car/truck/foot, with and without a detour) match the sticky column, 0 crossings.
2. This run also forced a GraphHopper graph re-import: the new `td_limit_cm` hints on `truck`/`foot` changed GraphHopper's internal profile fingerprint, which required clearing `/data/graph-cache` and recreating the service. The app's own edge-based graph hash (`8c13d8841f83...`) did not change, so the published edge-depth table stayed valid with no rebuild. Procedure and findings in [[graph-reimport-procedure]].
