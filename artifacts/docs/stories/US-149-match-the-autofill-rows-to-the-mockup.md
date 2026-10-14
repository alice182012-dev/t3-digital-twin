---
date_drafted: 2026-10-13
type: user-story
us_id: "US-149"
title: "Match the autofill rows to the mockup"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Blocked
kind: story
priority: P3
estimate: S
sprint: 15
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-149 Match the autofill rows to the mockup

As a user typing a destination, I want each suggestion on two lines, with the name and then the district, so I can tell apart places that share a name.

Difference `N7` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The rows are one line with a pin icon, the name in bold, and the district at the right edge. The mockup (screen 2d) shows the name on the first line and the district on the second, with no icon. A query like "C5" gives six rows that differ only by the district.

Given the query "C5" in the destination box, when the suggestions show, then each row has the name on the first line and the district on the second line, with no pin icon, as in screen 2d.
Given a query with diacritics ("Hoàn Kiếm"), then the rows keep their diacritics and the order of the backend.
Given a keyboard user, then the arrow keys and Enter still choose a row, and each row has an accessible name that holds the name and the district.

Dependencies: None.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started after [[US-085-time-out-a-route-request-in-the|US-085]] was `Reviewed`, within the limit of two.
- **2026-10-14, Blocked.** A worker built the story as written (two lines, no pin icon) and found that it contradicts the mockup. Screen 2d (`mock-2d.jpg`) shows one line per row, a small outline pin icon, the name with only the matched part in bold, and the district at the right edge. The live app already has that structure (`live-2d.jpg`). The change is kept unmerged on the branch `us-149-two-line-rows-unmerged`. The owner decides what the story asks for. See the questions in [[TODOS]].
