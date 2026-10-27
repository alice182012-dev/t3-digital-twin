---
date_open: 2026-09-23
date_closed: 2026-09-28
type: blocker
status: resolved
severity: P2
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, frontend, mobile, flood-legend]
related: ["[[EP-02-frontend-polish|frontend-polish]]", "[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]"]
last_updated: 2026-09-28
---

# Mobile search panel covers the flood legend

## Description

On a phone-width screen, the search panel at the top of the map covers the top of the flood legend.
`floodmap/graphhopper-maps/src/floodmap/FloodLegend.module.css` positions the legend with
`position: absolute; top: 30px; right: 30px`, and the mobile search panel is drawn over that
corner.

The delegate that built [[EP-02-frontend-polish|frontend-polish]]'s Story 2 saw this in a browser at 390 by 844 pixels,
against a stub backend with eight depth bands. With the panel collapsed, the legend title and the
first bands are hidden, and the list starts partway down. With the panel expanded, only the last
band ("> 60 cm") and the "Updated" line are visible.

Story 2 adds the "Updated" line, which makes the legend one line taller. Whether the overlap
existed before that line is not established, because nobody compared the legend with and without
it. The taller legend covers more of the bands than before, or the same amount, but not less.

## Why this matters

A user reading the map on a phone cannot see which color means which depth. The legend is the only
key for the flood layer, so the overlap makes the map harder to read exactly where flood mode is
most likely to be used.

## Approaches tried

### Approach 1

Candidate 2 from Decision and explanation: move the legend to the bottom right on mobile instead of
top right, via a `@media (max-width: 44rem)` override in `FloodLegend.module.css` (`top: auto;
bottom: 30px;`), mirroring `MapModeToggle`'s existing `position: absolute; bottom: 30px; left: 30px`
on the same breakpoint. Desktop is untouched.

Reproduced first: at 390x844 with the search panel in its expanded (inputs-visible) state, only the
legend's last two bands and the "Updated" line peeked out below the opaque search panel; the title
and first five bands were fully hidden behind it, matching the bug's original report. Verified live
on the server after deploy (`main` at `e5b155a`): the legend now renders fully at the bottom right,
title through all seven bands plus the "As of" line, with no overlap with the search panel or with
`MapModeToggle`'s bottom-left Map/Flood toggle. Desktop, checked at 1440x900, is unchanged: the
legend still renders top right exactly as before.

Not separately verified: the collapsed search-pill state (`MobileSidebar.tsx`'s `isSmallSearchView`,
which needs a resolved route on a short viewport to trigger). Not needed for this fix, since bottom
positioning is independent of the search panel's height or state in either direction, unlike the
original bug, which was.

## Decision and explanation

Candidate 2, done (see Approaches tried). Two original candidates, for the record:

1. Anchor the legend below the mobile header, so its `top` offset accounts for the panel's height.
   This needs the panel height at runtime, since the expanded panel is taller than the collapsed
   one. Not chosen: no existing mechanism in this codebase measures the panel's runtime height
   (`.smallScreenMapOptions`'s own below-the-header placement relies on a zero-height grid row that
   only works because its own content is short; it would collide with a card as tall as the legend).
2. Move the legend on mobile to the bottom of the map, above the results sheet, where nothing
   overlaps it. Chosen. This avoids measuring the panel but changes where users look for the legend,
   and the approved mockup places it at the top right (see Concerns).

## Concerns

The mockup (screens 2b and 2e) shows the legend at the top right, so this fix departs from it on
mobile. Accepted: this project's own mobile-priority stance treats mobile fidelity to the desktop
mockup as secondary to desktop, which is unchanged. `MapModeToggle` already uses the same
viewport-anchored bottom positioning technique on mobile, so this isn't a new pattern in the
codebase. A route's results sheet (`.smallScreenFooter`, grid row 4) could in principle grow tall
enough to reach the legend's `bottom: 30px` zone, the same latent risk `MapModeToggle` already
carries on its own bottom-left corner; not fixed here, since it's a pre-existing pattern this fix
follows rather than a regression it introduces.

## Related topics

- [[EP-02-frontend-polish|frontend-polish]], Story 2
- [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]

## Status history

- **2026-09-23, open.** Logged at the user's request after the delegate that built Story 2
  reported the overlap. Confirmed in its mobile screenshots (`mobile.png` and `mobile-open.png` in
  its untracked `marie-curie/profile-times-stub/` folder). Not yet known whether the overlap
  predates the "Updated" line.
- **2026-09-28, resolved.** Shipped Approach 2: moved the legend to bottom-right on mobile (`main` at
  `e5b155a`). Reproduced the original bug live first, then verified the fix live on both mobile
  (390x844, full legend visible, no overlap) and desktop (1440x900, unchanged).
