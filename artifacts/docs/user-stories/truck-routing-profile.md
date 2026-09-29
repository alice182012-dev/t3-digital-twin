---
date_drafted: 2026-09-23
type: user-story
status: done
subsystem: floodmap-frontend
sprint: 4
source_ideas: []
related: ["[[sprint-plan]]", "[[frontend-polish]]", "[[graphhopper-backend]]", "[[graphhopper-vehicle-profile-rejection]]"]
tags: [user-story, frontend, sprint-4]
---

# Show the truck routing profile in the frontend

## User story

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

Rendered UI captured 2026-09-29 18:06 UTC in a headless browser at 1366x768, opened on
`100.67.84.55:8082` (the address bar is not in the image). The map legend reads "As of 29/09/2026 16:45".
The profile row shows four modes with a travel time under each: motorbike 2 min, car 2 min, truck 2 min,
and foot 14 min. Truck is selected and bold. The route from 21.025, 105.755 to 21.03, 105.762 is 1.7 km
and 2 min, and the panel says "Route avoids flooded areas". The live route API returned 1,694 m and 141 s
for the same pair with the truck profile.

## Details

1. What: `truck: {}` in the `profiles` object of `config-local.js.example`, so the profile row
   offers four modes.
2. How: the Dockerfile copies the example file to `config-local.js`, so rebuilding
   `flood-routing-frontend` and recreating it on the server (`--no-deps`) picks the change up.
   The served `/config.js` lists `truck`. The icon and label already existed in the frontend.
3. Why: GraphHopper already serves `truck`, and a truck driver needs a route that respects the
   truck's depth limit.
4. Effect: a truck route returned 801 m against 773 m for a car on the same pair. The known risk
   in the first draft is gone: [[flood-routing-vehicle-type-always-motorbike]] is resolved, so a
   truck route uses the truck limit of 35 cm. The per-mode travel time row now sends four requests
   per query. On two of five pairs tried under the current test flood, car and foot found a
   route and truck did not. The cause is not investigated. It may be the 35 cm limit, the truck
   profile's own road restrictions, or both.

[[frontend-polish]]'s Story 1 also fires one route request per mode, so a fourth mode adds a
fourth request per query.

## Status history

- **2026-09-23, draft.** Created from `artifacts/TODOS.md`'s "Still open" note on the `foot`
  profile blocker and [[graphhopper-backend]]'s Open items. Assigned to Sprint 4 at the user's
  request. No backend change is needed, since GraphHopper already serves the profile.

- **2026-09-29, draft.** Done. Added `truck: {}` to `config-local.js.example`, rebuilt and recreated
  `flood-routing-frontend` on the server, and confirmed four modes in the live UI with a truck route
  of 918 m. Evidence saved as `frontend-truck-profile.png`.
- **2026-09-30, draft.** The screenshot named above was never saved, and the 918 m route it described was not
  recorded anywhere else. Saved a new capture as `frontend-truck-profile.png` from the frontend rebuilt on the merged
  branch: four modes, truck selected, a 1.7 km route. The Evidence paragraph now describes this image.

This is the simple story shape: one sprint, one objective. See [[user-story-types]] for the epic,
thematic, and SAFe shapes and when each one fits.
