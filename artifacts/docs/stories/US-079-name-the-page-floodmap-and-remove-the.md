---
date_drafted: 2026-10-07
type: user-story
us_id: "US-079"
story_label: "4"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P3
estimate: XS
sprint: 
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Name the page \"Floodmap\" and remove the \"Powered by GraphHopper\" line and its links"
---

# US-079 Name the page "Floodmap" and remove the "Powered by GraphHopper" line and its links

As a user, I want the page to carry the product's name, so the tab and the shared link do not say GraphHopper.
Given the app is open, when the tab, the empty panel, and the settings box render, then the page title and `og:title` read "Floodmap", the empty panel has no "Powered by GraphHopper" line, and the settings box has no links to `graphhopper.com` (info, imprint, privacy, terms).
`og:url` and `og:image` no longer point at `graphhopper.com`.
`NOTICE.md` and `LICENSE.txt` stay in the repository, and the OpenStreetMap attribution on the map stays.
GraphHopper Maps is Apache 2.0 (`NOTICE.md`).
That license does not require a badge in the UI.
It does require the license and notice files to stay with the code.
The settings box links to `graphhopper.com` pages for info, imprint, privacy, and terms.
They describe GraphHopper GmbH's service and not this app, so they go too.
Decided by the user on 2026-10-07: delete "Powered by" if possible, and delete the settings links ([[decision-log]] D-010).
Dependencies: None.
Covers G4.
Evidence: None yet.
