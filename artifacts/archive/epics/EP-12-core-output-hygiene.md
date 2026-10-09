---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-086", "US-087", "US-101"]
status: draft
subsystem: core-output
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[core-output-contract]]", "[[EP-10-routing-first-consumer|routing-first-consumer-stories]]", "[[flood-on-roads]]", "[[graphhopper-backend]]", "[[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]", "[[2026-10-07]]"]
tags: [user-story, epic, retention, tests, sprint-12]
---

# Epic: core output hygiene

Two gaps found while building [[EP-10-routing-first-consumer|routing-first-consumer-stories]] on 2026-10-07. Neither blocks a build. Both are in
Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request. Each row carries Priority, Status, Estimate, Sprint, and
Dependencies, as an extension of the base Epic shape in [[user-story-types]]. A story reaches `Done` only with a
screenshot and numbered details, recorded here and in `sprint-plan-3.md`.

- [[US-086-prune-old-rows-of-flood-road-values|US-086]] Prune old rows of `flood_road_values`. Story 1.
- [[US-087-make-test-flood-areas-py-run-without|US-087]] Make `test_flood_areas.py` run without hand-set paths, and run it in CI. Story 2.
- [[US-101-keep-simulating-while-the-flood-still-stands|US-101]] Keep simulating while the flood still stands after the rain stops. Story 3, P0, blocker [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]].

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-12-core-output-hygiene-history|the archived history]]. This section keeps plan-level changes only.

- **2026-10-07, draft.** Written at the user's request, from findings 1 and 4 of the log of [[2026-10-07]]. Both
  findings were rechecked against the code before the stories were written. Finding 1 holds: no age-based prune
  exists. Finding 4 is narrower than logged: the test imports with the documented path and skips without a database.
  The next free ID was `US-086`.

- **2026-10-10, active.** `US-101` added as Story 3 (P0, Sprint 12) for [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]. It is a pipeline fault found in the second replay, not a hygiene gap, but it sits in this epic because it changes `flood_mapping_full`, the DAG this epic already edits.
