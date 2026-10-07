---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-076", "US-077", "US-078", "US-079", "US-080", "US-081", "US-082", "US-083", "US-084", "US-085"]
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[sprint-plan-3]]", "[[frontend-mockup-recheck-and-sprint-11-start]]", "[[mockup-screen-coverage]]", "[[flood-routing-mockup-frontend-gap]]", "[[frontend-polish]]", "[[map-shows-forecast-not-now]]", "[[route-panel-stuck-on-loading-bars]]", "[[decision-log]]"]
tags: [user-story, epic, frontend, mockup, sprint-12]
---

# Epic: frontend recheck against the mockup

The stories of [[mockup-screen-coverage]], [[frontend-polish]], and [[frontend-depth-features]] built the six screens of
`artifacts/raw/frontend-mockups/Flood Routing Mockups v2.dc.html`. The recheck of 2026-10-07 found seven differences
that none of those stories records, and one open blocker with no story. The evidence for each is in
[[frontend-mockup-recheck-and-sprint-11-start]]. This epic turns every one of them into a story, and all of them are in
Sprint 12 of [[sprint-plan-3]], at the user's request.

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`sprint-plan-3.md`. A UI story takes its screenshot from the running UI. Test points stay inside the model border
(`.claude/CLAUDE.md`). Story 1 runs first, because its screenshots show which of the other differences are visible at
1366x768.

- **Story 1 (US-076): Compare the live app with the mockup in Aside at 1366x768.**
  As a product owner, I want the live app and the mockup captured side by side, so the spacing, color, and type are
  checked and not only the text.
  Given the live app and the mockup file, when each of screens 2a to 2f and the two states the mockup lacks (no
  route, and "wait until") is opened in Aside at 1366x768, then each pair is saved as a screenshot, and every
  difference is logged as a row of this epic or as a blocker. A difference that [[frontend-mockup-recheck-and-sprint-11-start]]
  already lists (G1 to G7) is marked with its ID, not logged twice.
  Priority: P1. Status: Not started. Estimate: S. Sprint: 12. Dependencies: None. It reads best after `US-055`, so the
  flag is on and the "wait until" alert is real.
  Evidence: None yet.

- **Story 2 (US-077): Match the depth chart columns and the route tab text to screen 2e.**
  As a user comparing routes, I want the chart to show the next hours at a glance and each tab to name its road, so I
  read the chart and the tabs the way the approved design shows them.
  Given a route with a depth forecast, when the chart renders, then it shows 5 columns that are 30 minutes apart (every
  second 15-minute step), only full hours are labelled, and the "now" column is the latest step at or before now, in
  green, with the dashed line at its depth. Given a route with a road description, when the tabs render, then each tab
  reads "Via `road`", and a tab with no unique description still reads "Route N".
  The pipeline publishes 15-minute steps, so the chart takes every second step. The PRD decision of 2026-09-23 ("30
  minutes, matching the mockup") stays true for the chart.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12. Dependencies: Story 1 (screenshots of the chart and the
  tabs). Covers G1 and G3.
  Evidence: None yet.

- **Story 3 (US-078): Show the place names on the start and destination pins.**
  As a user looking at a route, I want the pins to carry their names, so I know which end is which without reading the
  panel.
  Given a route whose start and destination have names, when the map renders, then each pin shows its name next to it,
  as in screen 2e ("GO Thăng Long", "FPT Shop"). A point with only coordinates shows no label.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12. Dependencies: Story 1. Covers G2.
  Evidence: None yet.

- **Story 4 (US-079): Name the page "Floodmap" and remove the "Powered by GraphHopper" line and its links.**
  As a user, I want the page to carry the product's name, so the tab and the shared link do not say GraphHopper.
  Given the app is open, when the tab, the empty panel, and the settings box render, then the page title and
  `og:title` read "Floodmap", the empty panel has no "Powered by GraphHopper" line, and the settings box has no
  links to `graphhopper.com` (info, imprint, privacy, terms). `og:url` and `og:image` no longer point at
  `graphhopper.com`. `NOTICE.md` and `LICENSE.txt` stay in the repository, and the OpenStreetMap attribution on the
  map stays.
  GraphHopper Maps is Apache 2.0 (`NOTICE.md`). That license does not require a badge in the UI. It does require the
  license and notice files to stay with the code. The settings box links to `graphhopper.com` pages for info,
  imprint, privacy, and terms. They describe GraphHopper GmbH's service and not this app, so they go too.
  Decided by the user on 2026-10-07: delete "Powered by" if possible, and delete the settings links
  ([[decision-log]] D-010).
  Priority: P3. Status: Not started. Estimate: XS. Sprint: 12. Dependencies: None. Covers G4.
  Evidence: None yet.

- **Story 5 (US-080): Keep "As of" and bring the `US-007` record in line.**
  As a maintainer, I want the written criteria and the screenshot of the legend to match the label, so the record does
  not say "Updated" when the app says "As of".
  Given the legend in flood mode, when it renders, then it reads "As of `time`" for a step at or before now and
  "Forecast for `time`" for a later step, as `timestepLabel.ts` does. The criteria of [[frontend-polish]] Story 2
  (`US-007`) say the same, and its screenshot is retaken from the live app.
  Decided by the user on 2026-10-07: keep "As of" ([[decision-log]] D-010). This settles the legend part of
  [[map-shows-forecast-not-now]]. The blocker stays `monitoring` for the pipeline delay.
  Priority: P3. Status: Not started. Estimate: XS. Sprint: 12. Dependencies: None. Covers G5.
  Evidence: None yet.

- **Story 6 (US-081): Draw a second dashed line for the selected mode's depth limit.**
  As a user who drives a motorbike, a car, or a truck, I want the chart to show my vehicle's limit, so I see when the
  route depth crosses it.
  Given a route and a selected mode, when the chart renders, then a second dashed line marks that mode's limit in
  centimetres, labelled, and it moves when the user selects another mode. The limits come from one owner (`US-074`).
  Priority: P3. Status: Not started. Estimate: S. Sprint: 12. Dependencies: Story 2, and `US-074` for the limits.
  Covers the first "Try next" line of the mockup (G6).
  Evidence: None yet.

- **Story 7 (US-082): Show the travel time and the maximum depth on each route tab.**
  As a user choosing between routes, I want each tab to show its time and its deepest water, so I pick one without
  opening each.
  Given a route with alternatives, when the tabs render, then each tab shows the road name, the travel time, and the
  maximum depth along that route in centimetres.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 12. Dependencies: Story 2 (the tab text). The depth comes from
  `POST /flood/profile` for each alternative, so check the cost of one request per tab first. Covers the second "Try
  next" line (G6).
  Evidence: None yet.

- **Story 8 (US-083): Build a mobile version of screen 2e.**
  As a user on a phone, I want the route result, the chart, and the steps to fit a 390 px screen, so I can use the app
  where I am.
  Given a viewport of 390x844, when a route result is open, then the profile row, the tabs, the chart, and the steps
  are all reachable without horizontal scroll, the legend is not covered, and the touch targets are at least 44 px.
  The mockup has no mobile design, so the story starts with a layout the user approves.
  Priority: P3. Status: Not started. Estimate: M. Sprint: 12. Dependencies: Stories 2, 3, and 7, so the layout covers the
  final components. Covers the third "Try next" line (G6).
  Evidence: None yet.

- **Story 9 (US-084): Design the no-route and "wait until" states, then match the UI to the design.**
  As a product owner, I want the two states the mockup lacks to have an approved design, so the wording and layout are
  a choice and not an accident.
  Given the yellow "No safe route available" box and the alert of `US-054`, when the user has approved a design for
  each state, then the UI matches it at 1366x768 and at 390x844, and a screenshot of each state is saved.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12. Dependencies: Story 1, and `US-055`, so the "wait until"
  text comes from the real backend. Covers G7.
  Evidence: None yet.

- **Story 10 (US-085): Time out a route request in the client.**
  As a user on a slow connection, I want a route request to end with a message, so the panel does not show loading bars
  for ever.
  Given a route request that gets no answer, when it has waited longer than a limit the story sets from the numbers of
  `US-035`, then the request is cancelled, the panel shows a retry message, and the loading bars stop. A request that
  answers in time is not affected.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12. Dependencies: None.
  Blocker tracking: [[route-panel-stuck-on-loading-bars]]
  Evidence: None yet.

## Status history

- **2026-10-07, draft.** Written from the recheck of the frontend against the mockup. The user asked for every candidate to
  become a story in the sprint after Sprint 11, and for a browser comparison in Aside in the same sprint. The third
  candidate of the plan (the "Try next" lines) became three stories (6, 7, and 8), and the legend and "Powered by" questions
  became Stories 4 and 5 after the user's decisions (D-010).
