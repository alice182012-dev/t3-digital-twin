---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-002", "US-003", "US-004", "US-005"]
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
tags: [user-story, epic, frontend, sprint-3]
---

# Epic: frontend depth features built on `GET /flood/points`

The three [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]] goals that all read a single point's depth at a
single timestep, all served by [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]'s `GET /flood/points`. None of these
stories can start before that endpoint exists. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- [[US-002-place-depth-popup-on-map-tap|US-002]] Place-depth popup on map tap. Story 1.
- [[US-003-per-step-depth-in-turn-by-turn|US-003]] Per-step depth in turn-by-turn instructions. Story 2.
- [[US-004-per-point-depth-badges-along-the-route|US-004]] Per-point depth badges along the route polyline. Story 3.
- [[US-005-tap-a-turn-step-to-highlight-its|US-005]] Tap a turn step to highlight its segment on the map. Story 4.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-01-frontend-depth-features-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-23, draft.** Drafted from [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]'s Goals 1, 4, and 5,
  after the popup's data source was corrected from `flood_road_values` to `GET /flood/points`.
- **2026-09-29, draft.** Story 4 added from the tap-a-turn-step item in `TODOS.md`, scheduled in Sprint 3 after Story 2.
- **2026-09-30, draft.** Added `frontend-place-depth-popup-wet-rebuilt.png`, a second wet-case screenshot the user took on the
  frontend rebuilt from the merged branch. The card at Đại lộ Thăng Long (Tây Mỗ, Hà Nội) shows the coordinates
  21.008917, 105.733807 and "Water depth as of 29/09/2026 16:45: 62 cm", and the legend reads "As of 29/09/2026 16:45".
  The image does not show the server address. The first wet-case image, `frontend-place-depth-popup-wet.png` (212 cm at
  21.005133, 105.757325, run 15:45), is unchanged. An earlier entry here said that image was never saved. That was wrong.
