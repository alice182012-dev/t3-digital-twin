---
date_drafted: 2026-09-23
type: user-story
status: draft
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

Not started

## Acceptance criteria

Given GraphHopper already serves the `truck` profile, when `truck: {}` is added to the `profiles`
object in `floodmap/graphhopper-maps/config-local.js.example` and `flood-routing-frontend` is
rebuilt on the remote host, then the profile row shows four modes, and selecting truck returns a
route from the live backend.

## Known risk

`FloodStore` sends `vehicle_type` as `motorbike` with every route request, whatever profile is
selected. A truck route would therefore avoid roads by the motorbike depth limit (20 cm), not the
truck limit (35 cm) in `flood_utils.py`'s `VEHICLE_PROFILES`. The same mismatch already affects car
and foot routes. Tracked as [[flood-routing-vehicle-type-always-motorbike]]. Decide whether to fix it in this
story or in a separate one before the truck profile ships to real users.

[[frontend-polish]]'s Story 1 also fires one route request per mode, so a fourth mode adds a
fourth request per query.

## Status history

- **2026-09-23, draft.** Created from `artifacts/TODOS.md`'s "Still open" note on the `foot`
  profile blocker and [[graphhopper-backend]]'s Open items. Assigned to Sprint 4 at the user's
  request. No backend change is needed, since GraphHopper already serves the profile.

This is the simple story shape: one sprint, one objective. See [[user-story-types]] for the epic,
thematic, and SAFe shapes and when each one fits.
