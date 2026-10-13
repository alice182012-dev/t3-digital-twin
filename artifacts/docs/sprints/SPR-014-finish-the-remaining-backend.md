---
date: 2026-10-12
type: sprint
sprint_id: "SPR-014"
sprint: 14
start_date: 2026-10-12
end_date: 2026-10-25
status: active
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]", "[[decision-log|D-038]]", "[[decision-log|D-040]]"]
---

# SPR-014 Sprint 14: Finish the remaining backend

## Sprint goal

Finish the remaining backend: every backend story in the backlog is `Done`, starting with [[decision-log|D-038]] (every reader of flood depth reads the edge depth table, and the old sampler and `flood_road_values` are deleted).

Set by the product owner on 2026-10-12, who widened the first goal "Finish D-038" after the sprint had started ([[decision-log|D-041]]). The frontend stories of [[EP-19-frontend-against-the-mockup|EP-19]] are not part of it.

## Planning

- **Dates.** The sprint runs two weeks, from Monday 2026-10-12 to Sunday 2026-10-25. It started on the day [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] ended early, at the product owner's request ([[decision-log|D-040]]).
- **Velocity.** The last sprints gave 15, 25, and 10 points ([[Velocity]]), and the last one lasted one day. The forecast stays at 16 points, as the product owner set it for Sprint 13.
- **Picks.** Fourteen stories made 34 points, which is 18 over the forecast, and four stories added on 2026-10-13 make it 18 stories and 41 points, which is 25 over. The product owner chose this on 2026-10-12 ("finish all of the backend, add them all"), so the sprint is a stretch. A story that is not `Done` on 2026-10-25 leaves the sprint at the review, and the product owner decides what moves. Each pick is `Ready`. [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] is picked against the framework rule for a story that waits on an external event.

| Order | Story | Title | Estimate | Points | Depends on |
| ----- | ----- | ----- | -------- | ------ | ---------- |
| 1 | [[US-118-write-the-edge-depth-to-a-queryable-table\|US-118]] | Write the edge depth to a queryable table | M | 3 | none, in progress |
| 2 | [[US-106-keep-per-segment-depth-history-in-timescaledb\|US-106]] | Write per-segment depth history to TimescaleDB (part a) | M | 3 | `Done` |
| 3 | [[US-113-backfill-per-segment-depth-history\|US-113]] | Backfill per-segment depth history | S | 2 | US-106 |
| 4 | [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table\|US-120]] | Read the rain gate and the soak checks from the edge table | S | 2 | US-118 |
| 5 | [[US-121-read-the-flood-metrics-from-the-edge-table\|US-121]] | Read the flood metrics from the edge table | M | 3 | US-118 |
| 6 | [[US-122-point-depth-history-at-the-edge-table\|US-122]] | Point depth_history at the edge table | S | 2 | US-118, US-106, US-113 |
| 7 | [[US-123-delete-flood-on-roads-and-flood-road-values\|US-123]] | Delete flood_on_roads, road_segment, and flood_road_values | S | 2 | US-120, US-121, US-122 |
| 8 | [[US-128-run-the-test-suites-against-the-test-databases\|US-128]] | Run the test suites against the test databases | S | 2 | US-125 (`Done`) |
| 9 | [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf\|US-126]] | Rebuild the raster tiles and road values from the NetCDF | M | 3 | US-125 (`Done`) |
| 10 | [[US-110-decide-whether-pipeline-tables-leave-the-public-schema\|US-110]] | Decide whether pipeline tables leave the public schema (spike) | S | 2 | none |
| 11 | [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast\|US-111]] | Write the forecast mode status row (part one of the pinned demo flood) | S | 2 | none |
| 12 | [[US-129-pin-the-peak-step-of-the-demo-flood\|US-129]] | Pin the peak step of the demo flood | M | 3 | US-126 |
| 13 | [[US-130-serve-the-forecast-mode-and-read-the-pinned-step\|US-130]] | Serve the forecast mode and read the pinned step | M | 3 | US-111, US-129 |
| 14 | [[US-114-prove-the-real-rain-archive-and-measure-growth\|US-114]] | Prove the real-rain archive and measure growth | S | 2 | a real forecast above 5 mm/h |
| | | Total | | 34 | |

- **Why these.** They are every story of the backlog whose work is backend, after the split of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] (an L) into four parts. The frontend part, [[US-131-show-the-demo-flood-banner-and-the-pinned-frame|US-131]], and the stories of [[EP-19-frontend-against-the-mockup|EP-19]] stay in the backlog. [[US-098-show-the-recommended-route-and-the-through|US-098]] is left out too, because its backend ([[US-097-recommend-a-route-that-avoids-the-precaution|US-097]]) is `Done` and what remains is the route panel.
- **Risk.** [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] needs real rain above 5 mm/h, which is not expected, so it will probably leave the sprint at the review. The sprint holds 34 points against a forecast of 16, so more than one story may leave.
- **Work in progress.** At most two stories are `In progress` at once. Only [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is, on 2026-10-12.
- **Done outside the plan.** [[US-117-export-a-stable-key-with-each-graph-edge|US-117]], [[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]], [[US-124-save-the-storm-replay-results-and-derived-data|US-124]], [[US-125-restore-the-snapshot-into-test-databases|US-125]], and [[US-127-build-the-history-and-metrics-from-the-restored-road-values|US-127]] were done on 2026-10-12 before the picks widened. They have no `sprint`, and their points are not in [[Velocity]].
- **Open decisions.** None.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 14
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-10-25. Walk through each story that is `Done` by its evidence screenshot, and record the product owner's accept or reject.

- **Goal met:** yes or no, with one sentence.
- **Points delivered:** N of N forecast.
- **Not done:** each story that left the sprint, back to the backlog with `sprint` cleared.
- **Estimate misses:** each `Done` story whose size was clearly wrong, with the number it should have had (1, 2, 3, or 5). Check that the reference stories in [[scrum-framework]] still fit.

## Retrospective

Three bullets and one action. Check the last retrospective's action first.

- **Worked:**
- **Did not work:**
- **Action:** a story, a rule change, or an `L-nnn` lesson.

## Refinement for the next sprint

The top of the backlog after this review: the order, the stories split, and the questions to answer.

## Status history

- **2026-10-12, planning.** Created at the product owner's request, with the goal "Finish D-038". The product owner confirmed the goal the same day.
- **2026-10-12, active.** The product owner ended [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] early and started this sprint the same day, from 2026-10-12 to 2026-10-25 ([[decision-log|D-040]]). Seven stories are picked, with `sprint: 14`, and they make 17 points.
- **2026-10-12, active.** The product owner accepted [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], so it is `Done` (3 of 17 points). [[US-113-backfill-per-segment-depth-history|US-113]] and [[US-122-point-depth-history-at-the-edge-table|US-122]] no longer wait for it. The owner also accepted [[US-124-save-the-storm-replay-results-and-derived-data|US-124]], [[US-125-restore-the-snapshot-into-test-databases|US-125]], and [[US-127-build-the-history-and-metrics-from-the-restored-road-values|US-127]], which are outside the sprint and have no `sprint`.
- **2026-10-12, active.** The product owner widened the goal to "Finish the remaining backend" and asked to add every backend story ([[decision-log|D-041]]). Seven stories joined: [[US-128-run-the-test-suites-against-the-test-databases|US-128]], [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]], [[US-110-decide-whether-pipeline-tables-leave-the-public-schema|US-110]], [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], and three parts of the split [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] ([[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]], [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]]). The sprint has 14 picks and 34 points, 3 of them `Done`. The forecast stays at 16.
- **2026-10-13, active.** The server was reachable and the batch was deployed. The product owner accepted [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], [[US-120-read-the-rain-gate-and-soak-checks-from-the-edge-table|US-120]], [[US-121-read-the-flood-metrics-from-the-edge-table|US-121]], and [[US-122-point-depth-history-at-the-edge-table|US-122]], so they are `Done` and the sprint has 12 of 34 points done. [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]] and [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] stay `Reviewed`, and [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] is `In progress`. Later that day the owner unpaused `flood_mapping_full`, and a run left over from 2026-10-10 resumed and published a new run, which closed the prune check of [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]].
- **2026-10-13, active.** The product owner accepted [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]], so it is `Done`, and the sprint has 15 of 34 points done.
- **2026-10-13, active.** The product owner asked to bring [[US-132-let-the-worker-run-the-reader-role-script|US-132]], [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]], [[US-134-set-the-same-rain-gate-in-every-airflow-container|US-134]], and [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]] (7 points) into the sprint, which now holds 18 stories and 41 points. The sprint is a stretch, and a story that is not `Done` on 2026-10-25 leaves it.
- **2026-10-13, active.** [[US-132-let-the-worker-run-the-reader-role-script|US-132]], [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]], [[US-134-set-the-same-rain-gate-in-every-airflow-container|US-134]], and [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]] are `Reviewed` and wait for the owner. The check of US-133 found three failures, so [[US-136-explain-the-soak-failures-next-to-flooded-edges|US-136]] joined the backlog with no `sprint`. The owner paused `flood_mapping_full` after a run left over from 2026-10-10 made the standing-flood rule start two real simulations with no rain.
- **2026-10-13, active.** The product owner accepted [[US-132-let-the-worker-run-the-reader-role-script|US-132]], [[US-133-pick-soak-pairs-that-can-prove-a-blocked-edge|US-133]], [[US-134-set-the-same-rain-gate-in-every-airflow-container|US-134]], and [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]], so they are `Done` and the sprint has 22 of 41 points done.
- **2026-10-13, active.** The product owner accepted [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] on written results, so it is `Done`, and the sprint has 25 of 41 points done.
- **2026-10-13, active.** The product owner dropped the road-values part of [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] ([[decision-log|D-046]]) and rescoped [[US-113-backfill-per-segment-depth-history|US-113]] to the runs of `edge_depth` ([[decision-log|D-047]]). Both are `Reviewed` and wait for the owner's acceptance, and only [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `In progress`.
- **2026-10-13, active.** The product owner accepted [[US-113-backfill-per-segment-depth-history|US-113]] and [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]], so they are `Done`, and the sprint has 30 of 41 points done.
- **2026-10-13, active.** The code of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] is on `modular`, and the server steps wait for the end of the 50-run check of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]].
