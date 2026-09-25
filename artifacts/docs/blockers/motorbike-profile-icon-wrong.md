---
date_open: 2026-09-26
date_closed: 2026-09-26
type: blocker
status: resolved
severity: P3
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, frontend, routing-profile, icon]
related: ["[[flood-routing-vehicle-type-always-motorbike]]", "[[truck-routing-profile]]", "[[fifteen-minute-cycle-tiles-and-histogram]]"]
last_updated: 2026-09-26
---

# The motorbike routing profile shows the wrong icon

## Description

The user reported on 2026-09-26, while checking the new depth chart on the live frontend, that the icon for the
bike profile is wrong. Their second screenshot, with the route panel open, confirms it: the first profile tab,
the selected one, shows a circle with the number 1 where a motorbike icon belongs. The car and foot tabs show
their own icons.

The cause is in the code. The deployed `config-local.js.example` defines the profiles `motorbike`, `car`,
and `foot`. `findIcon` in `floodmap/graphhopper-maps/src/sidebar/search/routingProfiles/profileIcons.ts` looks the
profile name up in a table keyed `car`, `bike`, `motorcycle`, `scooter`, and others. There is no `motorbike` key, and
`findIcon` only falls back to a base key when the name starts with `<key>_`. `RoutingProfiles.tsx` (lines 81 to
88 and `getIcon`) then treats `motorbike` as a custom profile with an unknown icon. It draws the
question-mark icon and adds a running number, which is the "1" in the screenshot. The icons `motorcycle.svg` and
`scooter.svg` exist but are never used for this profile.

## Why this matters

The motorbike is the default vehicle for this project. The routing limit that applies to it is 20 cm
([[flood-routing-vehicle-type-always-motorbike]]). A question mark or a pedal-bike icon on the default profile makes
the profile picker harder to trust for the people the app is built for.

## What is unknown

1. Which icon the design wants for the motorbike, `motorcycle.svg` or `scooter.svg`. The mockup
   (`artifacts/raw/mockups`) is the source to check.
2. Whether the numbered fallback should still appear for any future profile without an icon, or whether a
   missing icon key should fail a test instead.

## Approaches tried

### Approach 1

Added `motorbike: MotorcycleIcon` to the `icons` table in `profileIcons.ts`, plus a test that fails when a profile in
`config-local.js.example` resolves to the question-mark icon. Deployed at `a107c78`. The user confirmed the icon on the live page.

## Decision and explanation

Mapped `motorbike` to `MotorcycleIcon` in `profileIcons.ts` (`7290847`). The mockup (screen 2b) uses a two-wheel motorbike glyph
with equal wheels, which matches `motorcycle.svg`, not the scooter.

## Related topics

- [[flood-routing-vehicle-type-always-motorbike]]
- [[truck-routing-profile]], which adds another profile that needs an icon key check

## Status history

- **2026-09-26, open.** Logged at the user's request. The lookup in `profileIcons.ts` was the suspected source.
- **2026-09-26, open.** Confirmed by the user's screenshot of the open route panel: the motorbike tab is a numbered
  question-mark fallback. `RoutingProfiles.tsx` adds the number for profiles with no icon key.
- **2026-09-26, monitoring.** Fixed in `7290847` on branch `fifteen-minute-cycle`: `motorbike` now maps to
  `motorcycle.svg`, the glyph the mockup uses (screen 2b), and a test fails when a configured profile has no icon.
  Deployed to the frontend container at `a107c78`. Waiting for the user to confirm on the live page.
- **2026-09-26, resolved.** The user confirmed the motorcycle icon on the live page after the frontend was recreated at `a107c78`.
