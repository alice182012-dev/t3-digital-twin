---
date_drafted: 2026-10-13
type: user-story
us_id: "US-138"
title: "Skip soak pairs whose dry route crosses other blocked roads"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Ready
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
The story adds one rule: after the dry control, the check reads the edges of the run and step at or above the vehicle's limit, and it skips the pair when the dry route runs within 6 m of one of them that is not the picked piece.
For a `found` pair it also skips when the dry route does not cross the picked piece.

Given the three pairs of 2026-10-13 (the truck on `116434665:2`, and the car and the truck on `400545823:1`), when the check runs at the pinned step, then each is skipped and none fails.
Given a pair whose dry route crosses no other blocked edge, then it is judged as before.
Given a run, then the JSON of the check counts the pairs skipped for this reason.

Dependencies: [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]] is `Done`.

## Status history

- **2026-10-13, draft.** Raised by the answer of [[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependency is `Done`, it fits one sprint, and its acceptance is a run of the check on the server. It is `Ready` and not `In progress`, because [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] fill the two places.

## Evidence and details

Fill this when the story reaches `Done`.
