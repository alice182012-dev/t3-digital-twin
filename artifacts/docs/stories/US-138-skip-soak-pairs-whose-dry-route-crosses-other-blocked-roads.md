---
date_drafted: 2026-10-13
type: user-story
us_id: "US-138"
title: "Skip soak pairs whose dry route crosses other blocked roads"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: routing, testing
source_ideas: []
related: ["[[graphhopper-backend]]", "[[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]]", "[[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]]", "[[decision-log|D-050]]"]
tags: [user-story]
---

# US-138 Skip soak pairs whose dry route crosses other blocked roads

As a developer, I want the soak `roads` check to judge only pairs where the flood changes the route at the picked piece, so a pair that fails shows a routing fault.

On 2026-10-13 three pairs failed because their dry route runs on other edges of 94 to 146 cm, far from the picked piece, so the flooded request finds no route and the promise of the piece cannot be seen ([[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]], [[decision-log|D-050]]).
The pick clears only about 170 m around the piece, and the route between the two neighbours is longer.
The story adds one rule: after the dry control, the check reads the edges of the run and step at or above the vehicle's limit, and it skips a `crosses` or `found` pair when the dry route runs within 6 m of one of them that is not the picked piece.
A `blocked` pair is not skipped by this rule: its promise holds whatever else is closed, and its dry route runs along the neighbouring edges of the same deep road (details item 3).
For a `found` pair it also skips when the dry route does not cross the picked piece.

Given the three pairs of 2026-10-13 (the truck on `116434665:2`, and the car and the truck on `400545823:1`), when the check runs at the pinned step, then each is skipped and none fails.
Given a pair whose dry route crosses no other blocked edge, then it is judged as before.
Given a run, then the JSON of the check counts the pairs skipped for this reason.

Dependencies: [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]] is `Done`.

## Status history

- **2026-10-13, draft.** Raised by the answer of [[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependency is `Done`, it fits one sprint, and its acceptance is a run of the check on the server. It is `Ready` and not `In progress`, because [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] fill the two places.
- **2026-10-13, Reviewed.** Built and run on the server. At the pinned step the check gives 0 failures, judges 7 blocked pairs, and skips the three pairs of [[decision-log|D-050]] (details items 1 to 4). The owner has not accepted it.
- **2026-10-13, Done.** The product owner accepted it on the written results of details items 1 to 5, including the narrowing of the rule to the `crosses` and `found` promises.

## Evidence and details

**Evidence:** the output of the check in details item 2. No screenshot.

**Details:**

1. `scripts/backend_soak/soak_checks.py` skips a pair after its dry control in two cases.
   First, when the dry route does not cross the picked piece (every promise, so `found` too). Second, for a `crosses` or `found` promise, when the dry route runs within 6 m (`OTHER_BLOCKED_TOL_M`) of an edge of the run and step at or above the vehicle's limit that is not the picked piece. One PostGIS query per pair finds it (`OTHER_BLOCKED_SQL`, `other_blocked_edge`), and the flooded request is not sent. A skipped row carries the reason "dry route runs on another blocked edge", and the JSON counts these rows in `skipped_other_blocked`.
   The connection stays open for the whole loop and closes in a `finally`, because fetching the edges up front would need every edge at or above each of the four limits.
2. Run on the server on 2026-10-13 with the parameters of the failing run (`--run 20261011T001500 --valid-time 2026-10-11T02:00:00+07:00 --per-bucket 4`, temporary `DEMO` row): 26 roads and 100 pairs. 8 `found` and 10 `crosses` pairs passed, 7 `blocked` pairs passed, and 0 failed. 20 `found`, 11 `crosses`, and 44 `blocked` pairs were skipped, 1 of them by the new rule. `blocked_unproven` is empty, there were 0 server errors, and the exit code is 0.
   The three pairs of [[decision-log|D-050]] are skipped: the truck on `116434665:2` by the new rule, and the car and the truck on `400545823:1` because the dry route does not cross the piece.
3. A first version applied the new rule to `blocked` pairs too. That gave 0 judged blocked pairs, all four vehicles `blocked_unproven`, and exit code 1, because the dry route of a blocked pair runs along the neighbouring edges of the same deep road. The rule now applies to `crosses` and `found` only (`needs_isolated_route`).
4. The tests: 56 pass without a database, and 65 pass against the scratch databases (`run_db_tests.py --only scripts/backend_soak`), including 5 new PostGIS tests of the query. The dataset databases did not change.
5. The check reads the same run and step for the query as for the routes, so a run with no `edge_depth` rows for that step skips no pair by this rule.

