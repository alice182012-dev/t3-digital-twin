---
date_open: 2026-09-23
date_closed: 
type: blocker
status: open
severity: P2
subsystem: floodmap-frontend
approaches_tried: 0
approaches_remaining: 2
tags: [blocker, frontend, mobile, flood-legend]
related: ["[[frontend-polish]]", "[[flood-routing-mockup-frontend-gap]]"]
last_updated: 2026-09-23
---

# Mobile search panel covers the flood legend

## Description

On a phone-width screen, the search panel at the top of the map covers the top of the flood legend.
`floodmap/graphhopper-maps/src/floodmap/FloodLegend.module.css` positions the legend with
`position: absolute; top: 30px; right: 30px`, and the mobile search panel is drawn over that
corner.

The delegate that built [[frontend-polish]]'s Story 2 saw this in a browser at 390 by 844 pixels,
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

None yet.

## Decision and explanation

Pending. Two candidate fixes, neither tried.

1. Anchor the legend below the mobile header, so its `top` offset accounts for the panel's height.
   This needs the panel height at runtime, since the expanded panel is taller than the collapsed
   one.
2. Move the legend on mobile to the bottom of the map, above the results sheet, where nothing
   overlaps it. This avoids measuring the panel but changes where users look for the legend, and
   the approved mockup places it at the top right.

## Concerns

The mockup (screens 2b and 2e) shows the legend at the top right, so either fix departs from it on
mobile. Check the fix at 390 by 844 pixels with the panel collapsed and expanded, and with the
maximum number of bands.

## Related topics

- [[frontend-polish]], Story 2
- [[flood-routing-mockup-frontend-gap]]

## Status history

- **2026-09-23, open.** Logged at the user's request after the delegate that built Story 2
  reported the overlap. Confirmed in its mobile screenshots (`mobile.png` and `mobile-open.png` in
  its untracked `marie-curie/profile-times-stub/` folder). Not yet known whether the overlap
  predates the "Updated" line.
