---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[point-depth-lookup-backend]]", "[[sprint-plan]]"]
tags: [user-story, epic, frontend, sprint-3]
---

# Epic: frontend depth features built on `GET /flood/points`

The three [[flood-routing-mockup-frontend-gap]] goals that all read a single point's depth at a
single timestep, all served by [[point-depth-lookup-backend]]'s `GET /flood/points`. None of these
stories can start before that endpoint exists. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- **Story 1: Place-depth popup on map tap.**
  As a user exploring the map, I want to tap a point and see its current water depth, so I can
  judge conditions at a specific location, not just along a route.
  Given the app is open with a route already showing on screen (any two points, any mode), when the
  user taps a point on the map that isn't a query point, then a card opens at that point showing its
  name, its address, its coordinates (for example "20.992987, 105.773723"), and a "Water depth now:
  `N` cm" line, matching mockup screen 2b.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3
  (`GET /flood/points`), Story 4 (latency validation). Also needs a reverse-geocoding source for the
  place name and address. Check `AddressInputAutocomplete.tsx`'s geocoder first (see
  [[flood-routing-mockup-frontend-gap]]'s Dependencies and assumptions).

- **Story 2: Per-step depth in turn-by-turn instructions.**
  As a user following a route, I want to see the depth at each turn alongside its distance, so I
  know what to expect before I reach it.
  Given a route exists, when each turn-by-turn step in the expanded instructions list renders, then
  it shows its depth next to its distance on the same line ("320 m · 8 cm"), matching mockup screen
  2e.
  Priority: P0. Status: Not started. Estimate: S. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.

- **Story 3: Per-point depth badges along the route polyline.**
  As a user viewing a rendered route, I want to see depth badges at the points where depth changes
  along the route, so I can spot flooded segments on the map itself, not just in a list.
  Given a route exists, when the route renders on the map, then the map shows depth badges at
  points along the route polyline where the depth changes, matching the four badges in mockup screen
  2e (not fewer, and not one badge per turn regardless of whether depth changed there).
  Priority: P0. Status: Not started. Estimate: M. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.

## Status history

- **2026-09-23, draft.** Drafted from [[flood-routing-mockup-frontend-gap]]'s Goals 1, 4, and 5,
  after the popup's data source was corrected from `flood_road_values` to `GET /flood/points`.
- **2026-09-24, draft.** Story 1's acceptance now includes the coordinates line that mockup
  screen 2b shows. The popup's route button is a separate story in [[mockup-screen-coverage]].
