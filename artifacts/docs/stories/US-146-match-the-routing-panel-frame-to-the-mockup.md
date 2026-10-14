---
date_drafted: 2026-10-13
type: user-story
us_id: "US-146"
title: "Match the routing panel frame to the mockup"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
kind: story
priority: P2
estimate: M
sprint: 15
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-146 Match the routing panel frame to the mockup

As a user planning a route, I want the routing panel to look like the approved design, so the app reads as one product and not as the stock GraphHopper card.

Difference `N3` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The panel is the stock GraphHopper card: a settings gear, "Add location", "Settings", "GPX", and "Details". The mockup (screens 2c to 2e) has a full-height white panel of about 460 px, a black pill on the selected mode with a white icon, a close X at the right, rounded input boxes joined by a dotted connector, and no gear, "Add location", or "Settings" link.

Given the empty routing panel at 1366x768, when it opens, then it matches screen 2c: the four mode icons with the selected one in a black pill, a close X, two rounded input boxes with the dotted connector, and no other controls.
Given a route result, then the same frame holds around the chart and the steps of screen 2e.
Given the removed controls, then each one either has a replacement the owner approved or is recorded as dropped in this story.
Given the panel, then a keyboard user can still reach every remaining control, and the close X has an accessible name.

The story estimate is M. If the match of the input boxes and the removal of the stock controls grow, split the second part before the sprint holds it.

Dependencies: [[US-079-name-the-page-floodmap-and-remove-the|US-079]] removes the "Powered by" line, so the panel match starts after it. The owner decides which stock controls (settings, GPX, details, custom model) stay.
Evidence: see below.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started with no other story in progress, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server, the owner's decision on each removed control, and the owner's acceptance. It is close to screens 2c and 2e but not pixel for pixel (detail 4).

## Evidence and details

Empty panel: ![[local-empty-panel.jpg|420]]
Route result: ![[local-route-result.jpg|420]]
Mobile, unchanged: ![[local-mobile.jpg|420]]

1. What: on the desktop layout the routing panel is a full-height white panel 460 px wide with a 1 px right border. The four mode icons have the minutes under them, the selected mode is a black pill with a white icon, and a thin close X sits at the right. Two 46 px input boxes with a 6 px radius are joined by a hollow circle, three dots, and a red pin. A route result keeps the frame: black and white route pills, a flat chart with dark bars and a green "now" bar, and a "Steps" list with the distance and the depth right-aligned. The tabs and the chart stay fixed and the steps scroll.
2. How: `LargeScreenLayout` in `floodmap/graphhopper-maps/src/App.tsx` passes a `framed` prop to `RoutingProfiles`, `Search`, and `RoutingResults`, and `AddressInput` and `Instructions` get it from those. `MobileSidebar` and `SmallScreenLayout` do not pass it, so the mobile layout keeps its stock controls (checked in a 400 px iframe). The chart is restyled in `DepthForecastChart.tsx` and its CSS for every layout. Grid column 1 is now 460 px. The whole jest suite (346 tests) and `tsc --noEmit` pass on the merged tree. No test was added, because the work is CSS and markup without a pure helper.
3. Removed from the desktop panel, hidden by markup and not deleted (the code stays and the mobile layout still shows them). Each is recorded here as dropped until the owner approves a replacement or asks to bring it back:
   1. The custom model toggle (the gear). It opened the custom model editor box, which nothing on the desktop can open now.
   2. "Add location". It added a via point. Via points from the URL still render.
   3. The "Settings" and "Close" link. It opened the settings box with the distance units, the GPX export options, and the draw-areas toggle.
   4. The GPX button. It downloaded the route as a GPX file.
   5. The "Details" button. It expanded the route statistics (ascend, descend, road class) and the turn instruction toggle. The desktop now always shows the instruction list, and the statistics are unreachable.
   6. The summary row with "14 min / 1.9 km" and the elevation hint. The time and distance now sit in the chart header, so with no depth chart the distance does not show. The tab detail still shows time and depth.
   7. The small grey close cross, replaced by the new X.
4. What still differs from the mockup: the mode icons are the stock glyphs and not the mockup's outline icons, the font is the stock family, the step turn icons are the stock images and the first row has a green pin where the mockup has a black one, the mockup's bold deepest depth in a step is missing, the red limit line and its label ([[US-081-draw-a-second-dashed-line-for-the|US-081]]) and the "Route avoids flooded areas" note are not in the mockup, the route pill carries the time and depth that the mockup does not show ([[US-082-show-the-travel-time-and-the-maximum|US-082]]), the Elevation widget still overlays the bottom of the steps ([[US-147-remove-the-elevation-widget-from-the-route-view|US-147]]), the current-location icon still shows in a focused empty input, and the stock route hint buttons still render.
5. Side effects: `Instructions` now reads "35 m · depth 8 cm" in every layout, including mobile, and `DepthForecastChart` is restyled in every layout.
6. Keyboard: the Tab order follows the DOM (four mode buttons, the close X, two inputs, route tabs, step rows), and the X has `aria-label="Close routing panel"`. A real Tab key press was not tried.
7. Not checked: 1366x768 (the Aside window was 1440x900), a route with a full five-bar chart and several tabs, and a real window narrower than 44rem.
8. Left for `Done`: the server rebuild, a server screenshot, and the update of [[floodmap-frontend]].
