---
date: 2026-10-01
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, frontend, performance, us-035, sprint-4]
related: ["[[carried-over-backlog]]", "[[sprint-plan]]", "[[2026-10-01]]", "[[route-panel-stuck-on-loading-bars]]", "[[sample_rate_1_bottleneck]]"]
---

# Plan: US-035 revalidate "loading is very slow"

## Context

`US-035` ([[carried-over-backlog]] Story 4, Sprint 4, S, P3) asks whether the live app loads slowly and why. The note is from 2026-09-08, before the polygon tiles and the raster-first pipeline. It also asks for the routing panel's wait on a pair with no connection, which was 9 seconds or more on 2026-09-30 ([[route-panel-stuck-on-loading-bars]]). The result closes the item or opens a blocker with a measured cause.

## Facts that shape the design

1. The vault does not say who wrote the 2026-09-08 note or what it meant. The old `SAMPLE_RATE=1` bottleneck ([[sample_rate_1_bottleneck]]) was a pipeline speed in the GeoJSON chain, which was retired. So this plan measures the page load and treats the pipeline reading as closed.
2. The live app is `http://100.67.84.55:8082`. Test points stay inside the model border (`.claude/CLAUDE.md`).
3. The panel waits for both route requests of a pair (a fast one and one for alternatives), and the per-mode travel times send one request per profile ([[frontend-polish]] Story 1).

## Decisions already made

1. Use Aside (the user's browser, `aside repl`), one flow per script, three runs per measurement so a single slow run shows.
2. The measurements are read-only. No form is submitted.

## Steps

1. Measure the load: time to the first map tiles and to the flood layer, from navigation timing and resource timing.
2. Measure the no-connection wait per mode (car, motorbike, foot, truck): time from page load to the yellow "No safe route available" box, and the duration of each `/route` request.
3. Decide: close the item if the numbers are acceptable, or open a blocker with the measured cause.
4. Record numbers, a screenshot, and details in the sprint plan, the epic, and the log.

## Status history

- **2026-10-01, active.** Plan written. Aside is running. Step 1 started.
- **2026-10-01, done.** Steps 1 to 4 done. The load and the no-connection wait were measured with Aside against port 8082 (`us-035-loading-check.js`). Nothing is slow, so the item closed without a blocker.
