---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-096", "US-046", "US-047", "US-048", "US-049", "US-050", "US-051", "US-052", "US-053", "US-054", "US-055"]
status: draft
subsystem: floodmap-backend, floodmap-frontend
source_ideas: ["[[sticky-c-lite-routing]]"]
related: ["[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[BL-011-routing-not-time-aware|routing-not-time-aware]]", "[[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]]", "[[departure-time-advice-research]]"]
tags: [user-story, epic, routing, graphhopper, sprint-5, sprint-6, sprint-8, sprint-9, sprint-10]
---

# Epic: time-aware routing engine (sticky C-lite)

The requirements are in [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]. The depth data the engine reads is in
[[EP-08-edge-depth-table|edge-depth-table-stories]]. The order of work is in [[SP-02-routing-engine-foundations|sprint-plan-2]] (Sprints 5 to 8) and [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] (Sprints 9 to 12).

Each row carries Priority, Status, Estimate, Sprint, and Dependencies. The base Epic shape in
[[user-story-types]] has no per-row scheduling field. This file adds those fields on purpose, as the
project's sprint-delegation convention allows. Sprint numbers continue from [[SP-01-prd-and-backlog|sprint-plan]], which covers
Sprints 1 to 4. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`sprint-plan-2.md` or `sprint-plan-3.md`, whichever holds the story.

- [[US-046-record-the-routing-baselines-on-the-server|US-046]] Record the routing baselines on the server. Story R1.
- [[US-047-build-the-synthetic-scenarios-the-offline-reference|US-047]] Build the synthetic scenarios, the offline reference, and the offline checker. Story R2.
- [[US-048-show-no-route-for-a-mode-that|US-048]] Show "no route" for a mode that has none. Story R3.
- [[US-049-build-the-java-module-skeleton-the-image|US-049]] Build the Java module skeleton, the image, and the CI job. Story R4.
- [[US-050-build-the-time-aware-weighting-and-search|US-050]] Build the time-aware weighting and search for `motorbike` and `car`. Story R5.
- [[US-051-add-the-truck-and-foot-time-aware|US-051]] Add the `truck` and `foot` time-aware profiles. Story R6.
- [[US-052-integrate-the-engine-into-the-backend-with|US-052]] Integrate the engine into the backend with a flag and a fallback. Story R7.
- [[US-053-build-post-route-departures|US-053]] Build `POST /route/departures`. Story R8.
- [[US-054-show-wait-until-in-the-no-route|US-054]] Show "wait until" in the no-route alert. Story R9.
- [[US-055-prove-the-engine-on-the-server-and|US-055]] Prove the engine on the server and roll it out. Story R10.
- [[US-096-check-each-road-at-the-requested-departure|US-096]] Check each road at the requested departure, not the floored one. Story R11.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-09-time-aware-routing-engine-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-29, draft.** Written from [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]. No story has started.
- **2026-09-29, draft.** Re-cut with the plans: Stories R1 to R2, R4, and R5 stay in [[SP-02-routing-engine-foundations|sprint-plan-2]] (Sprints 5 to 8). Stories R6 to R10
  moved to [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] (Sprints 9 and 10). Story R3 is superseded by [[EP-02-frontend-polish|frontend-polish]] Story 4 in Sprint 3 of [[SP-01-prd-and-backlog|sprint-plan]].
- **2026-10-07, active.** On host ADMIN, branch `modular`, `rollout.ps1` ran (flood_mapping_full paused, run locally since this session is the server). `graphhopper` needed a graph re-import first, rehearsed for the first time, because `US-051`'s `td_limit_cm` hints changed GraphHopper's internal profile fingerprint (not the app's own edge-based graph hash, so the published table stayed valid). Every check that does not need the DAG then passed: `scenario-check.sh` (32/32), the engine proof's `compare`/`crossings`/`departures`/`latency` against 24 real pairs on the deployed backend. Stories R6 (`US-051`), R7 (`US-052`), and R8 (`US-053`) moved to `Done` on this evidence. R9 (`US-054`) stays `Reviewed`: a quick attempt to drive the real no-route UI flow in a browser did not trigger routing via URL params, and needs a proper interactive pass. R10 (`US-055`) stays `In progress`: its own dependencies include R9 (not yet `Done`) and `US-045` (not yet `Done`, see [[EP-10-routing-first-consumer|routing-first-consumer-stories]] and `TODOS.md`), and the DAG-timing pieces are deferred to after Sprint 11 at the user's request, to be tested together.
- **2026-10-07, active.** R9 (`US-054`) moved to `Done`: drove the deployed frontend by hand (real keystrokes and `Enter`, URL params alone did not work), found a currently-blocked pair, and confirmed the alert's exact acceptance text in a browser against the real backend. R10 (`US-055`) now has only `US-045` left among its own dependencies, which is deferred with the rest of the DAG-timing work until after Sprint 11.
- **2026-10-09, active.** R10 (`US-055`) moved to `Done` at the user's request. Evidence: `us-055-rollout-results-check-output.png` (9 of 24 routes changed, median detour 0.94, 0 crossings, 6 latency cells within the factor), plus `US-045` (gap 2.69 to 3.91 minutes). The flag stays off at rest until the DAG runs on real rain.
