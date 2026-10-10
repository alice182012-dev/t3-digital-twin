---
date_drafted: 2026-10-10
type: user-story
us_id: "US-105"
title: "Decide what flood history the industry apps need"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
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

1. Answered by the product owner on 2026-10-10. The industries to prepare for are finance, urban planning, and agriculture. No application for them is built now. The platform is made ready so that a customer from any industry can start quickly.
2. The grain is one value per road piece and moment, as [[decision-log|D-028]] says. Finance and agriculture may ask about parcels and fields. An area-based history waits for a customer who needs it, and a new story adds it then.
3. Answered by [[decision-log|D-028]]. History keeps the latest forecast of each road piece and moment. It keeps no other forecast, so analyses of forecast error or lead time are out of scope.
4. Answered by the product owner on 2026-10-10: "dry".
   A piece with no row in `flood_road_values` was dry at every step of its run.
   This answers the piece-level case only.
   A moment with no run at all, such as a slot that the 5 mm/h gate skipped ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]), has no rows for any piece, so the answer does not tell a consumer whether that moment was dry or unknown.
   The spike states how a consumer tells that case apart.
5. Answered by the product owner on 2026-10-10: one year.
   History lasts one year, not the several years that [[decision-log|D-028]] sets.
   The answer sets the age at which old data is dropped, but not what history costs in rows.
   The spike still measures the real row count per day on the server and the compressed size on a real TimescaleDB server.
   The spike's `D-nnn` must say that it supersedes the retention target of [[decision-log|D-028]], which is one year by the product owner's answer.

**Sizing, read on the server on 2026-10-10.**

- `road_segment` has 35,652 pieces. The 48 runs in `flood_road_values` wet 3,615 distinct pieces. The newest run wet 2,864 pieces over 8 steps, which is 22,912 rows.
- A day has at most 96 moments. One row per piece and moment (latest forecast wins) is about 2,900 x 96 = 278,000 rows a day on a storm day. The ceiling, every piece wet all day, is 35,652 x 96 = 3.4 million rows a day.
- Keeping every forecast would be about 22,900 rows x 96 runs = 2.2 million rows a day. [[decision-log|D-028]] does not keep them.
- The row size (about 130 bytes with the primary key index) and the compression ratio (10 times) are estimates. The spike replaces both with measurements.
- Free disk is 100 GB on C: and 581 GB on D:. The `timescaledb-data` volume lives in Docker's disk image on C: ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).

Given the answers to the five sub-questions, when the spike ends, then the story holds the three industries, and a decision `D-nnn` in `decision-log.md` that names the store, the grain, how long data is kept, and how a consumer tells dry from unknown.
The decision also confirms or changes the proposed consumer rule of [[EP-21-industry-analysis-on-the-flood-data|EP-21]].

Dependencies: None.

## Status history

- **2026-10-10, draft.** Ready: the question is stated, it has an estimate, and the answer is a decision.
- **2026-10-10, industries named.** The product owner named finance, urban planning, and agriculture, and said the work prepares the platform and builds no industry application. Sub-questions 1 and 2 are answered.
- **2026-10-10, narrowed.** [[decision-log|D-028]] answered sub-question 3 and set the retention target of sub-question 5.
- **2026-10-10, In progress.** The product owner answered sub-question 4 ("dry") and sub-question 5 (one year), so all five sub-questions have an answer.
  The measurements and the spike's decision remain open.
- **2026-10-10, Reviewed.** The spike ends with the measurements in Evidence and details and the decision [[decision-log|D-032]].
  The product owner accepts it at review, and the status moves to `Done` then.

## Evidence and details

The spike ends with the answer in [[decision-log|D-032]].
The measurements were taken on 2026-10-10. The server is the source unless a point says otherwise.

1. `flood_road_values` holds 2,033,864 rows for 80 runs (`file_id`) and 3,884 distinct road pieces.
   Its forecast times run from 2026-10-09 22:30 to 2026-10-11 00:15, Vietnam time.
2. The table with its indexes is 1,274 MB, which is 656 bytes per row.
3. The newest run has 19,656 rows for 2,457 pieces over 8 steps.
4. The depth values are 151,584 rows at 0 m, 511,837 rows above 0 m and under 5 cm, and 1,370,443 rows at 5 cm or more.
5. The writer rule is in `scripts/flood_roads/flood_on_roads.py`, the wet CTE near line 159.
   A piece wet at any step of a run gets a row at every step, with depth 0 where it is dry.
   A piece wet at no step gets no row.
6. The latest-wins grain, one row per piece and moment, gives 319,573 rows.
   By local day, 2026-10-09 has 17,280 rows (6 moments), 2026-10-10 has 297,244 rows (91 moments, the replay storm day), and 2026-10-11 has 5,049 rows (2 moments, a partial day).
   The ceiling is 35,652 x 96 = 3,422,592 rows a day.
   This sample ordered runs by `file_id`, and the decision orders them by `issued_at`.
   Across the 80 runs, `file_id` order and `issued_at` order agree for 79 of 80 runs and disagree for one pair: `file_id` 523 has run timestamp 2026-10-10 19:00 but was written after `file_id` 522 (timestamp 20:15).
   The row count and the compression ratio do not depend on which run wins.
7. On a real TimescaleDB 2.30.1 server (`flood_metrics` database), I loaded the 319,573 rows into a scratch hypertable with the shape of `depth_history`.
   `valid_time` was converted from Vietnam time to UTC, the table had one chunk, and it was compressed with `segmentby` `segment_id` and `orderby` `valid_time`.
   Uncompressed it is 43 MB, about 141 bytes per row. Compressed it is 3,840 kB, a ratio of 11.4 against the estimate of 10.
   The scratch table was dropped, and `depth_history` still has 0 rows.
8. Projection for one year, from items 6 and 7.
   A storm day like 2026-10-10 is about 3.7 MB compressed, so 365 storm days are about 1.3 GB.
   The ceiling, every piece wet all day, is about 42 MB a day, about 15 GB a year.
9. The estimates of 130 bytes a row and a compression ratio of 10 in Sizing are replaced by items 7 and 8.

A spike records its measured result instead of a screenshot.
