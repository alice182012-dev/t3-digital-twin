---
date_drafted: 2026-10-07
type: user-story
us_id: "US-076"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P1
estimate: M
sprint: 
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Compare the live app with the mockup in Aside at 1366x768"
---

# US-076 Compare the live app with the mockup in Aside at 1366x768

As a product owner, I want the live app and the mockup captured side by side, so the spacing, color, and type are checked and not only the text.
Given the live app and the mockup file, when each of screens 2a to 2f and the two states the mockup lacks (no route, and "wait until") is opened in Aside at 1366x768, then each pair is saved as a screenshot, and every difference is logged as a row of this epic or as a blocker.
A difference that [[frontend-mockup-recheck-and-sprint-11-start]]
already lists (G1 to G7) is marked with its ID, not logged twice.
Dependencies: None.
It reads best after `US-055`, so the flag is on and the "wait until" alert is real.
Evidence: None yet.

## Status history

- **2026-10-10, estimate S to M.** Compared with US-024 (S for three screens).
  This story covers six screens and two missing states, so it is about three times that, with a screenshot pair for each.
