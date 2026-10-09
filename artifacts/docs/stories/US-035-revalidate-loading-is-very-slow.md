---
date_drafted: 2026-09-29
type: user-story
us_id: "US-035"
story_label: "4"
epic: "[[EP-07-carried-over-backlog]]"
status: Done
priority: P3
estimate: S
sprint: 4
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Revalidate \"loading is very slow\""
---

# US-035 Revalidate "loading is very slow"

As a user opening the app, I want to know if loading is slow and why, so a real slowness gets its own
fix and a stale note gets closed.
Given the note dates from 2026-09-08, before the polygon tiles and the raster-first pipeline, when the
live app loads on a normal connection, then the time to the first map and the time to the flood layer
are measured, and the result either closes the item or becomes a blocker page with the measured cause.
Confirm first whether the note means the `SAMPLE_RATE=1` bottleneck in [[sample_rate_1_bottleneck]], which
is a pipeline speed and not a page load.
Also measure the routing panel's wait for a pair with no connection. On the live site on 2026-09-30, the panel
kept its grey loading bars for more than 9 seconds before the yellow "No safe route available" box appeared
([[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]]). Record the seconds per mode, and whether the four per-mode requests of
[[EP-02-frontend-polish|frontend-polish]] Story 1 add to it.
Priority: P3. Status: Done. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None.
Evidence: ![[us-035-loading-check-output.png|700]]
Details:
1. What: the live app's load and the wait for a no-connection pair were measured. The app does not load slowly, so the item is closed.
2. How: `evidence/us-035-loading-check.js` ran with `aside repl` against port 8082: 3 cold loads (cache off), 2 cold loads on emulated regular 4G (9 Mbit/s, 170 ms), and 6 loads of a pair with no motorbike or truck connection. Earlier runs the same day gave the same ranges.
3. Why: the note "loading is very slow" dates from 2026-09-08, before the polygon tiles and the raster-first pipeline. Its `SAMPLE_RATE=1` reading was a pipeline speed in the retired GeoJSON chain.
4. Effect: unthrottled, the first map shows in 0.7 to 1.5 s and the flood layer is complete in 2.0 to 3.2 s. On regular 4G the first map shows in 1.9 s and the flood layer is complete in 6.1 s. A cold load fetches a 1.6 MB bundle and 12 flood tiles of 3.2 MB in total, and a warm load takes about 0.1 to 0.3 s. The yellow "No safe route available" box appeared 1.5 to 2.6 s after page start. Each load sends 13 `/api/gh/route` requests that start within about 10 ms of each other, so they do not add up. The slowest took 0.35 to 1.54 s. The 9 to 20 s wait of 2026-09-30 did not appear in 17 loads. [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]] stays `monitoring`, and the client still has no timeout on `Api.route`. The numbers come from a Mac over the server network, not from a mobile phone.
