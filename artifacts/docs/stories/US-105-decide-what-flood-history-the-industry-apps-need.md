---
date_drafted: 2026-10-10
type: user-story
us_id: "US-105"
title: "Decide what flood history the industry apps need"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: spike
priority: P1
estimate: S
sprint: 
subsystem: analysis, timescaledb
source_ideas: []
related: ["[[core-output-contract]]", "[[timescaledb-schema]]", "[[flood-on-roads]]"]
tags: [user-story, spike]
---

# US-105 Decide what flood history the industry apps need

As the product owner, I want to know which history each industry application needs, so I can order the stories that store it.

**Question.**
Which history must the pipeline keep for the industry applications, at what grain, for how long, and in which store?

**Timebox.**
Half a sprint.
The spike works in `marie-curie/` and measures on the server.

**Sub-questions.**

1. Which industries come first, and what question does each ask of the data? The product owner names at least three niches. The spike lists the data each one reads.
2. What is the grain: one value per road piece per step, the raster, or the polygons?
3. Does history keep only the latest forecast of each moment, or every forecast? A run starts every 15 minutes and forecasts about 2 hours ahead, so one moment has several forecasts. `depth_history` has one row per segment and moment, so it keeps one. Analyses of forecast error or lead time need all of them.
4. Does a missing row mean dry or unknown? `flood_road_values` has no row for a piece that was dry at every step of a run.
5. How long must history last, and what does that cost in rows? The product owner wants several years and accepts one month, the retention of 3Di results, as a fallback. The spike measures the real row count per day on the server and the compressed size on a real TimescaleDB server, then checks the target against the sizing below.

**Sizing, read on the server on 2026-10-10.**

- `road_segment` has 35,652 pieces. The 48 runs in `flood_road_values` wet 3,615 distinct pieces. The newest run wet 2,864 pieces over 8 steps, which is 22,912 rows.
- A day has at most 96 moments. One row per piece and moment (latest forecast wins) is about 2,900 x 96 = 278,000 rows a day on a storm day. The ceiling, every piece wet all day, is 35,652 x 96 = 3.4 million rows a day.
- Keeping every forecast is about 22,900 rows x 96 runs = 2.2 million rows a day.
- The row size (about 130 bytes with the primary key index) and the compression ratio (10 times) are estimates. The spike replaces both with measurements.
- Free disk is 100 GB on C: and 581 GB on D:. The `timescaledb-data` volume lives in Docker's disk image on C: ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).

Given the answers to the five sub-questions, when the spike ends, then the story holds a table of niche, question, and data needed, and a decision `D-nnn` in `decision-log.md` that names the store, the grain, which forecasts are kept, how long, and how a consumer tells dry from unknown.
The decision also confirms or changes the proposed consumer rule of [[EP-21-industry-analysis-on-the-flood-data|EP-21]].

Dependencies: None. The product owner's list of niches is an input.

## Status history

- **2026-10-10, draft.** Ready: the question is stated, it has an estimate, and the answer is a decision.

## Evidence and details

Fill this when the spike ends.
A spike records its measured result instead of a screenshot.
