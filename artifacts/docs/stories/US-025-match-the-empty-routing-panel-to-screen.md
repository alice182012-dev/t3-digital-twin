---
date_drafted: 2026-09-24
type: user-story
us_id: "US-025"
story_label: "3"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P3
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Match the empty routing panel to screen 2c"
---

# US-025 Match the empty routing panel to screen 2c

As a first-time user, I want the empty panel to read like the approved design, so it tells me what to type.
Given the routing panel is opened with no points, when it renders, then the inputs read "Choose starting point, or click on the map" and "Choose destination", and the mode row lists car, motorbike, walking, and truck in that order.
The live panel differs in these ways: the placeholders read "From" and "To", the modes run motorbike, car, truck, walking with motorbike selected, and it also shows a settings gear, "Add location", "Settings", and "Powered by GraphHopper", which the mockup does not. Whether to keep those extras is a product call.
Dependencies: None.
Evidence: ![[frontend-empty-panel-live-check.png|420]] ![[frontend-empty-panel-preview-check.png|420]]
Details: On the live site (2026-09-30) both hints and the mode order show as specified, with motorbike selected. Checked on a preview build first, then on the live site. Frontend and backend deployed on 2026-09-30.
