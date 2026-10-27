---
date: 2026-10-01
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, frontend, accessibility, us-032, sprint-4]
related: ["[[EP-07-carried-over-backlog|carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[2026-10-01]]", "[[EP-05-mockup-screen-coverage|mockup-screen-coverage]]"]
---

# Plan: US-032 keyboard and screen reader access

## Context

`US-032` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 1, Sprint 4, S, P2) asks that the Map or Flood toggle, the route tabs, and the flood legend work by keyboard and screen reader. It waited for the Sprint 3 UI stories, which are done, so it checks the final components.

## Facts that shape the design

Read on 2026-10-01 in `floodmap/graphhopper-maps/src`.

1. `MapModeToggle.tsx` already has `aria-pressed` on two native buttons, so Enter and Space work. The buttons are 82 px square.
2. `RouteTabs` in `sidebar/RoutingResults.tsx` already has `role="tablist"`, `role="tab"`, and `aria-selected`. It lacks arrow-key movement and roving `tabindex`. The tabs are about 27 px tall (`.routeTab` in `RoutingResult.module.css`).
3. Legend contrast already passes for the title and the "Updated" line (`#6b7280` on `#fff`, 4.83:1). The band labels set no color and inherit one.
4. Computed contrast ratios: inactive tab 5.56:1, inactive tab on hover 4.99:1, active tab 8.46:1.

## Decisions already made

1. The arrow-key rule is a pure function, `routeTabKeyTarget(key, activeIndex, count)`, so it is tested with literal values. Arrow keys wrap, and Home and End go to the first and last tab. Selection follows focus.
2. Tabs get `min-height` and `min-width` of 44 px. The legend band labels get an explicit color, so their contrast does not depend on inheritance.
3. A CSS contrast test reads the module files and fails if a pair drops under 4.5:1.

## Steps

1. A subagent builds the change in its own worktree, tests first (rule: `pstack:poteto-mode`, Feature).
2. The lead reviews the diff and cherry-picks it.
3. A preview build on the server checks the change in a browser: Tab and arrow keys on the route tabs, Enter and Space on the toggle, tab height of at least 44 px.
4. The user pushes and deploys, then a live check and a screenshot close the story.

## Status history

- **2026-10-01, active.** Plan written. Step 1 started.
- **2026-10-01, active.** Steps 1 and 2 done. The subagent was stopped partway, so the lead finished the legend color, the contrast test, and the checks, and cherry-picked 7 commits (`f44f776` to `26034f1`). 279 tests pass and `tsc` is clean. Step 3 (preview build and browser check) is next. It needs the branch on the server, which needs a push.
- **2026-10-01, active.** Step 3 done. The branch is pushed (`26034f1`) and the server checkout is fast-forwarded. A preview image built from it runs as `floodmap-frontend-preview` on port 8083 against the real backend. In gstack's headless browser (Aside's `aside` command is not on PATH here), a foot route from 20.9850, 105.7100 to 21.0150, 105.7900 showed 3 tabs, each 44 px tall. ArrowRight moved the selection and focus 1, 2, 3 and wrapped to 1. ArrowLeft wrapped to 3. Home and End went to the first and last tab. Only the selected tab had `tabindex` 0, and Tab left the tab strip for the next control. Enter on Map and Space on Flood flipped `aria-pressed`. Screenshot: `frontend-route-tabs-keyboard-preview-check.png`. Step 4 (deploy and live check) is next.
- **2026-10-01, done.** Step 4 done. The user pushed and deployed, and the live site at port 8082 passed the same checks as the preview (`frontend-route-tabs-keyboard-live-check.png`). The preview container is removed. The story is `Done`.
