---
date_drafted: 2026-09-24
type: user-story
us_id: "US-024"
story_label: "2"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Verify the first-load, empty-panel, and autofill screens against the mockup"
---

# US-024 Verify the first-load, empty-panel, and autofill screens against the mockup

As a product owner, I want screens 2a, 2c, and 2d checked against the approved mockup on the live
app, so the "already matched" claim in [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]] is confirmed, not
assumed.
Given the frontend is rebuilt and running on the remote host, when each screen is opened in a
1366x768 browser window, then screen 2a shows the "Search Floodmap" pill with Map on and Flood
off, screen 2c shows both empty inputs with the placeholder text, and screen 2d shows autofill
suggestions for a query such as "C5" and for "Hồ Gươm" with no results from outside Vietnam. Any
difference is logged as a new story or blocker.
Priority: P2. Status: Done. Estimate: S. Sprint: 3, last row (re-cut 2026-09-29). Dependencies: Sprint 3's UI stories, so one pass checks the finished screens. Closes the
`needs-revalidation` autofill item in `TODOS.md` and re-verifies the `vi` locale fix, which needs
a rebuild and redeploy.
Evidence: ![[live-2a-first-load-check.png|300]] ![[live-2c-empty-panel-check.png|300]] ![[live-2d-autofill-c5-check.png|300]] ![[live-2d-autofill-ho-guom-check.png|300]]
Mockup side: ![[mockup-2a-first-load.png|300]] ![[mockup-2c-empty-panel.png|300]] ![[mockup-2d-autofill.png|300]]
Details:
1. What: screens 2a, 2c, and 2d of the mockup were compared with the live app at `100.67.84.55:8082`, at 1366x768, and every difference was logged.
2. How: the mockup file was opened locally and each card captured. The live app was captured on first load, with the routing panel opened, and with "C5" and "Hồ Gươm" typed into From.
3. Why: to confirm that these screens match the approved design, not to assume it.
4. Effect: the autofill closes its `needs-revalidation` item. "Hồ Gươm" returns Hanoi results first and every result is in Vietnam, so the `vi` locale fix holds. The screens do not match on three counts, logged below. Screen 2a: the app opens in Flood mode, and the mockup opens with Flood off. `FloodStore.ts` sets that as a "demo default", and the user decided to keep it (D-008 in [[decision-log]]). Screen 2c: [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 3. Screen 2d: Story 4.
