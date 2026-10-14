---
date_drafted: 2026-10-13
type: user-story
us_id: "US-149"
title: "Match the autofill rows to the mockup"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
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

As a user typing a destination, I want each suggestion to look like screen 2d, so I can see which part of the name I typed.

Difference `N7` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
Screen 2d shows one line per row: an outline pin icon, the name with only the matched part in bold, and the district at the right edge. The live app already has that structure. The gaps are the bold part, the row size, and the weight of the rest of the name.

Given the query "C5" in the destination box, when the suggestions show, then only the matched "C5" is bold, the rest of the name has regular weight, the district sits at the right edge in grey, and the row size matches screen 2d.
Given a query with diacritics ("Hoàn Kiếm"), then the rows keep their diacritics and the order of the backend, and the matched part is bold.
Given a keyboard user, then the arrow keys and Enter still choose a row, and each row has an accessible name that holds the name and the district.

Dependencies: None.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.
- **2026-10-14, owner answer.** Follow screen 2d. The story is rewritten to the real gaps (bold only the matched part of the name, the row size, regular weight for the rest). The branch `us-149-two-line-rows-unmerged` is not used. A worker builds it from `modular`.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started after [[US-085-time-out-a-route-request-in-the|US-085]] was `Reviewed`, within the limit of two.
- **2026-10-14, Blocked (resolved).** A worker built the story as written (two lines, no pin icon) and found that it contradicts the mockup. Screen 2d (`mock-2d.jpg`) shows one line per row, a small outline pin icon, the name with only the matched part in bold, and the district at the right edge. The live app already has that structure (`live-2d.jpg`). The change is kept unmerged on the branch `us-149-two-line-rows-unmerged`. The owner decides what the story asks for. See the questions in [[TODOS]].
- **2026-10-14, In progress.** The story is rewritten to the real gaps after the owner's answer. A worker builds it.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.

## Evidence and details (update 2026-10-14)

![[compare-2d-autofill.jpg|420]]

1. What: the rows follow screen 2d. Each row is 36 px with a 16 px outline pin in grey, the name at 13 px with only the matched part in bold (weight 600), and the district at the right edge in grey. The list fills the panel width right under the input section.
2. How: `matchedPrefix.ts` finds the matched prefix and ignores case and diacritics, so "hoan kiem" bolds "Hoan Kiem" in "Hoan Kiem Ward". The name keeps the backend's characters, the order, the keyboard use, and the click selection. Each row has an `aria-label` of "name, district", and the pin is `aria-hidden`. Tests: `matchedPrefix.test.ts` (6) and `AddressInputAutocomplete.test.tsx` (3).
3. Evidence: `evidence/US-149/` holds `follow-2d-autofill.jpg`, `compare-2d-autofill.jpg` (mock panel beside live panel), and `local-autofill-hoan-kiem.jpg`.
4. Not checked: the mobile layout and a real Tab-key pass. The mock's names ("C5 Giảng Võ") differ from the backend's ("C5" with a district), so the text cannot match.
5. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows the autofill rows for "Giang Vo" with the matched prefix in bold, a pin icon on each row, and the district on the right. Screenshot: `evidence/server-check-2026-10-14/server-autofill.jpg`. The owner accepted the story on 2026-10-14.
