---
date_drafted: 2026-09-24
type: user-story
us_id: "US-026"
story_label: "4"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P3
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Match the autofill rows to screen 2d"
---

# US-026 Match the autofill rows to screen 2d

As a user typing a place, I want each suggestion to show the place name and its district on one line, so I can tell places apart quickly.
Given "C5" is typed into an input, when the suggestions show, then each row has a pin icon, the name in bold, and its district at the right edge, as in the mockup's four rows.
The live rows show a bold name with the full address on a second line, up to six rows, and no pin icon. The results themselves are correct: all are in Vietnam, and "Hồ Gươm" ranks the Hanoi lake first.
Priority: P3. Status: Done. Estimate: S. Sprint: 3 (moved from Sprint 4 by the user on 2026-09-30). Dependencies: None.
Evidence: ![[frontend-autofill-rows-live-check.png|420]] ![[frontend-autofill-rows-preview-check.png|420]]
Details: On the live site "C5" gives six rows, each with a pin, the bold name, and an area at the right edge ("Định Công", "Cầu Giấy", "Nghĩa Đô"). Some areas come in English from Photon ("Tu Liem Ward", "Yen Hoa Ward"). Deployed with `7fb4266`. Checked on a preview build first, then on the live site. Frontend and backend deployed on 2026-09-30.
