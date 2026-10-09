---
date_drafted: 2026-09-23
type: user-story
us_id: "US-022"
us_ids: ["US-022"]
status: done
subsystem: floodmap-frontend
sprint: 4
source_ideas: []
related: ["[[SP-01-prd-and-backlog|sprint-plan]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[graphhopper-backend]]", "[[BL-001-graphhopper-vehicle-profile-rejection|graphhopper-vehicle-profile-rejection]]"]
tags: [user-story, frontend, sprint-4]
---

# Show the truck routing profile in the frontend

## User story (US-022)

As a truck driver planning a route through a flood-prone area, I want to choose the truck profile,
so I get a route that respects the depth a truck can pass, not one planned for a car or a
motorbike.

## Priority

P2

## Estimate

S

## Status

Done

## Acceptance criteria

Given GraphHopper already serves the `truck` profile, when `truck: {}` is added to the `profiles`
object in `floodmap/graphhopper-maps/config-local.js.example` and `flood-routing-frontend` is
rebuilt on the remote host, then the profile row shows four modes, and selecting truck returns a
route from the live backend.

## Evidence

![[frontend-truck-profile.png|420]]

Rendered UI captured 2026-09-29 15:09 (UTC+7) on `100.67.84.55:8082` at 1366x768, on the run
`20260929T150000`: the profile row shows four modes with a travel time under each, truck is
selected and bold, and the route is 918 m. The depth chart also renders again on this fresh run.

## Details

1. What: `truck: {}` in the `profiles` object of `config-local.js.example`, so the profile row
   offers four modes.
2. How: the Dockerfile copies the example file to `config-local.js`, so rebuilding
   `flood-routing-frontend` and recreating it on the server (`--no-deps`) picks the change up.
   The served `/config.js` lists `truck`. The icon and label already existed in the frontend.
3. Why: GraphHopper already serves `truck`, and a truck driver needs a route that respects the
   truck's depth limit.
4. Effect: a truck route returned 801 m against 773 m for a car on the same pair. The known risk
   in the first draft is gone: [[BL-005-flood-routing-vehicle-type-always-motorbike|flood-routing-vehicle-type-always-motorbike]] is resolved, so a
   truck route uses the truck limit of 35 cm. The per-mode travel time row now sends four requests
   per query. On two of five pairs tried under the current test flood, car and foot found a
   route and truck did not. The cause is not investigated. It may be the 35 cm limit, the truck
   profile's own road restrictions, or both.

[[EP-02-frontend-polish|frontend-polish]]'s Story 1 also fires one route request per mode, so a fourth mode adds a
fourth request per query.

## Status history

- **2026-09-23, draft.** Created from `artifacts/TODOS.md`'s "Still open" note on the `foot`
  profile blocker and [[graphhopper-backend]]'s Open items. Assigned to Sprint 4 at the user's
  request. No backend change is needed, since GraphHopper already serves the profile.

- **2026-09-29, draft.** Done. Added `truck: {}` to `config-local.js.example`, rebuilt and recreated
  `flood-routing-frontend` on the server, and confirmed four modes in the live UI with a truck route
  of 918 m. Evidence saved as `frontend-truck-profile.png`.

This is the simple story shape: one sprint, one objective. See [[user-story-types]] for the epic,
thematic, and SAFe shapes and when each one fits.
