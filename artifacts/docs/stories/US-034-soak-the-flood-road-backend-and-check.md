---
date_drafted: 2026-09-29
type: user-story
us_id: "US-034"
story_label: "3"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P2
estimate: M
sprint: 5
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Soak the flood-road backend and check it against known answers"
---

# US-034 Soak the flood-road backend and check it against known answers

As the engineer who owns routing, I want the GraphHopper flood-road backend to run for a 48-hour soak and
to route correctly on roads with a known water depth, so more load does not land on an unproven service.
Given the regression tests in `test_flood_areas.py` and `test_server.py` already pass, when the backend
serves the live app for 48 hours, then the container logs show no unexplained 5xx responses in that
period, and for each road in a fixed set, `POST /route` blocks every vehicle whose depth limit the road's
depth exceeds and routes the others. The limits are in `flood_utils.py`: motorbike 20 cm, car 30 cm,
truck 35 cm, and foot 40 cm. The set is built from real roads in `flood_road_values` whose depth lies
between two limits, as the 2026-09-28 overpass did (`way/776941610#3`, 20.2 cm). The expected result of
each road comes from the limits, not from another backend.
Dependencies: None. The user set the soak
length to 48 hours on 2026-10-01. The comparison with the earlier Valhalla backend is dropped (see the last
history entry).
Test points: inside the model border (`.claude/CLAUDE.md`).
Soak window: 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07, the 48 hours of the replay of Story 8. The first window (2026-10-02 00:45 +07 to 2026-10-04 00:45 +07) is void. The user stopped the pipeline on 2026-10-02, because the constant 50 mm/h test rain is not a real event, and the Docker daemon on the server returned HTTP 500 at 13:53 +07. Docker works again, and every container was recreated at about 15:00 ([[2026-10-02-disk-cleanup-and-d-drive-move]]). The new window is the 48 hours of the replayed rain event of [[EP-07-carried-over-backlog|carried-over-backlog]] Story 8 (`US-063`). It starts with the replay at 16:00 +07, which needs the DAG unpaused by about 15:55 +07.
Tooling: `scripts/backend_soak/` (29 tests). `run_soak.sh` is the verdict. It exits with 0 only if no container restarted, no log has a 5xx response or an error line, and no known-answer check failed. See "Soak and known-answer check" in [[graphhopper-backend]].
Interim of the void window, 2026-10-02 03:13 +07 (2 hours 28 minutes in): the logs since 00:45 hold 2,422 requests on `floodmap-backend` (1,981 with 200 and 441 with 400), 308 on the frontend, and 0 responses with 5xx and 0 error lines in all three containers. The known-answer check on the 03:00 run covered 23 roads and 92 pairs of road and profile. It passed 86, skipped 6, and failed none, and all 40 blocked promises held.
To finish: after 2026-10-04 16:00 +07, run `sh scripts/backend_soak/run_soak.sh 2026-10-02T16:00:00+07:00`. If it exits with 0, render its output as the evidence image and set the story to `Done`. If it does not, log the failure as a blocker.
Details (closed on 137 runs, 2026-10-05):
1. What: the soak is closed on the 137 runs of the replay that ran, not on the full 48 hours. The user decided this on 2026-10-05 to move on to Sprint 6.
2. How: the replay of `US-063` ran from 2026-10-02 16:00 +07 and stopped at 137 of 192 runs when the 2026-10-04 disk-full incident cut it. The first run on the real host (2026-10-02, 16:11 +07) passed the container check and the known-answer check (14 roads, 56 checks). The end check of `run_soak.sh` over the window was not run.
3. Why: the user judged 137 runs enough of a pattern, and wanted to start Sprint 6.
4. Effect: Sprint 6 can start. The 48-hour clean-logs result is not proven, and the story has no screenshot of an end check. Evidence waived by the user. The storage check `US-069` still reads the running replay. Flagged for the human to confirm.

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed. It also said: status "Done (closed 2026-10-05 on 137 runs, evidence waived by the user)".
