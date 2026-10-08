---
date: 2026-09-29
type: plan
status: active
plan_number: 3
start_date: 2026-11-16
end_date: 2026-12-13
tags: [user-story, sprint-plan, routing, graphhopper]
related: ["[[core-output-hygiene-stories]]", "[[rain-replay-test-environment-stories]]", "[[rain-replay-test-environment]]", "[[9c-sampling-step-runs-over-770-seconds]]", "[[routing-first-consumer-stories]]", "[[time-aware-routing-engine-stories]]", "[[edge-depth-table-stories]]", "[[time-aware-routing-engine]]", "[[sprint-plan-2]]", "[[sprint-plan]]", "[[carried-over-backlog]]", "[[routing-not-time-aware]]", "[[frontend-mockup-recheck-and-sprint-11-start]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[frontend-mockup-recheck-stories]]", "[[sprint-plan-4]]", "[[paper-handoff-routing-and-system]]", "[[schedule-routing-paper-experiments-and-move-frontend]]", "[[US-094-095-archive-and-netcdf-retirement-stories]]", "[[archive-3di-results-and-retire-netcdf-values]]"]
---

# Sprint plan 3: the engine in the backend, the advice, and the rollout

The last links of the sticky C-lite chain, plus one carried item. This plan follows [[sprint-plan-2]] (Sprints 5 to 8),
so its sprint numbers continue at 9. It covers four weeks (`.claude/CLAUDE.md`, rule 10). It depends on
[[sprint-plan-2]] finishing: Story R5 (the engine) and Story E5 (the Java reader) must be `Done` before Sprint 9.

## Why these four sprints

Four sprints because a plan covers four weeks. Sprints 9 and 10 hold the remaining engine work. Sprint 11 holds a
carried, dependency-free item and the routing-as-first-consumer stories. Sprint 12 finishes the routing work: the paper experiments, the rain replay environment, and core output hygiene. The frontend recheck moved to Sprint 13, the first sprint of [[sprint-plan-4]], on 2026-10-08.

Calendar, from `start_date` in the frontmatter:

| Sprint | Start | End | Actual start | Actual end |
| ------ | ----- | --- | ------------ | ---------- |
| 9 | 2026-11-16 | 2026-11-22 | 2026-10-05 |  |
| 10 | 2026-11-23 | 2026-11-29 | 2026-10-05 |  |
| 11 | 2026-11-30 | 2026-12-06 | 2026-10-07 |  |
| 12 | 2026-12-07 | 2026-12-13 |  |  |

- **Sprint 9** adds the other two profiles, the backend switch with its fallback, and the departure endpoint.
- **Sprint 10** shows the advice in the alert and rolls the engine out.
- **Sprint 11** makes routing the first consumer of an explicit core output contract ([[routing-first-consumer-stories]]).
- **Sprint 12** finishes the routing: it runs the four paper experiments ([[US-090-093-routing-paper-experiments-stories]]), builds the rain test environment ([[rain-replay-test-environment-stories]]), closes two core output gaps ([[core-output-hygiene-stories]]), and absorbs small slips. The frontend recheck ([[frontend-mockup-recheck-stories]]) and `US-033` are scheduled in [[sprint-plan-4]], because a plan covers four sprints and this one ends with Sprint 12.

The advice waits for the table because option C reads depth by edge id. That puts the "wait until" alert in Sprint 10,
later than an approach that joined route pieces by geometry would have. The user chose exactness over speed on
2026-09-29.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`. Each story carries the same
Status in its epic file. Update both together. A story reaches `Done` only with evidence and details in both places.

## Sprint 9: profiles, backend switch, and the departure endpoint

**Dates:** 2026-11-16 to 2026-11-22 (Monday to Sunday)

**Sprint goal:** all four modes route through the time-aware engine behind a flag with a safe fallback, and
`POST /route/departures` returns the earliest clear departure.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-052 | P0 | Integrate the engine into the backend with a flag and a fallback | M | [[time-aware-routing-engine-stories]] R7 | Stories R5, E5 (both from [[sprint-plan-2]]) | ![[us-055-engine-server-proof-2026-10-07.png]] | 1. Deployed, 24 real pairs, 37.5% changed, median detour 0.94, 0 crossings, 0 permission errors; checked 2026-10-07 on host ADMIN. | Done |
| US-051 | P1 | Add the `truck` and `foot` time-aware profiles | S | [[time-aware-routing-engine-stories]] R6 | Story R5 | ![[us-051-scenario-check-2026-10-07.png]] | 1. 32 of 32 scenario-check runs match on the deployed image, checked 2026-10-07 on host ADMIN. | Done |
| US-053 | P1 | Build `POST /route/departures` | M | [[time-aware-routing-engine-stories]] R8 | Stories E2, E3, E4, and this sprint's R7 | ![[us-055-engine-server-proof-2026-10-07.png]] | 1. 3 real trips answered correctly against the live table, checked 2026-10-07 on host ADMIN. | Done |

## Sprint 10: the advice in the alert, and the rollout

**Dates:** 2026-11-23 to 2026-11-29 (Monday to Sunday)

**Sprint goal:** the alert shows "wait until", the engine passes its checks on the server inside the latency
factor, and the flag goes on with evidence.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-054 | P1 | Show "wait until" in the no-route alert | S | [[time-aware-routing-engine-stories]] R9 | Story R8, and [[frontend-polish]] Story 4 ([[sprint-plan]] Sprint 3) | ![[us-054-wait-until-alert-browser-2026-10-07.png]] | 1. Exact acceptance text rendered in a browser against the real backend, checked 2026-10-07 on host ADMIN. | Done |
| US-070 | P1 | Stop a slow sampling step from holding the database | S | [[edge-depth-table-stories]] E8 | Story E3 | None yet | - | Reviewed |
| US-055 | P0 | Prove the engine on the server and roll it out | M | [[time-aware-routing-engine-stories]] R10 | Stories R6, R7, R9, E7. Gate cleared 2026-10-02: the user set the latency factor to 2 | None yet | - | In progress |
| US-094 | P1 | Archive `results_3di.nc` and a run record to D: when the pipeline reads real rain | M | [[US-094-095-archive-and-netcdf-retirement-stories]] 1 | None to build. Needs real rain to prove. Blocks `US-095` and `US-086` | None yet | - | Not started |

## Sprint 11: the routing output contract

**Dates:** 2026-11-30 to 2026-12-06 (Monday to Sunday)

**Sprint goal:** routing reads the core's output only through a stated, tested contract.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-071 | P1 | Write the output contract and a test that checks it against the live schema | M | [[routing-first-consumer-stories]] C1 | None | ![[us-071-live-schema-contract-2026-10-07.png]] | 1. Live schema matches the contract for 5 tables, checked 2026-10-07 on host ADMIN. | Done |
| US-072 | P1 | Run the routing backend on a read-only database role | S | [[routing-first-consumer-stories]] C2 | Story C1, and `US-055` for the server run | ![[us-072-reader-role-2026-10-07.png]] | 1. `routing_reader` reads 5 tables, writes nothing, 0 permission errors under soak; checked 2026-10-07 on host ADMIN. | Done |
| US-073 | P2 | Move the routing-owned tasks into their own DAG, triggered by the core's published output | M | [[routing-first-consumer-stories]] C3 | Story C1, and `US-055` for the server timing | None yet | - | Reviewed |
| US-074 | P2 | Give the vehicle thresholds one owner | S | [[routing-first-consumer-stories]] C4 | None | ![[us-074-vehicle-limit-owner-2026-10-07.png]] | 1. `VEHICLE_PROFILES` in `flood_utils.py` is the one owner, guard test ok 2026-10-07 on host ADMIN. | Done |
| US-075 | P2 | Fail a test when the backend reads a table outside the contract | S | [[routing-first-consumer-stories]] C5 | Story C1 | ![[us-075-contract-table-guard-2026-10-07.png]] | 1. Guard passes on the backend's 4 real tables, checked 2026-10-07 on host ADMIN. | Done |
| US-095 | P1 | Retire the `netcdf_values` ingest | M | [[US-094-095-archive-and-netcdf-retirement-stories]] 2 | `US-094` proven on real rain. The server drop needs the user's go | None yet | - | Not started |

## Sprint 12: finish the routing

**Dates:** 2026-12-07 to 2026-12-13 (Monday to Sunday)

**Sprint goal:** finish the routing: the paper experiments, the rain replay environment, and core hygiene. Each paper result names its storm, and the experiments read the replay data of `US-089`.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-091 | P1 | Measure how often a single-timestep route meets a closed road on arrival | M | [[US-090-093-routing-paper-experiments-stories]] 2 | `US-047`, `US-050`, `US-052` (all `Done`), the depth tables of the replay of `US-089`, and the server state proved by `US-055` | None yet | - | Not started |
| US-090 | P1 | Write the FIFO lemma and the correctness proof of the sticky-closure forward search | M | [[US-090-093-routing-paper-experiments-stories]] 1 | None | None yet | - | Not started |
| US-088 | P1 | Cut the Hanoi storm of 2026-09-16 and 2026-09-17 into a replay event | S | [[rain-replay-test-environment-stories]] 1 | None. Needs the Earthdata login on the Mac | None yet | - | In progress |
| US-089 | P1 | Start and stop a rain replay on the server with one command each | M | [[rain-replay-test-environment-stories]] 2 | None to build. `US-088` supplies the storm | None yet | - | Reviewed |
| US-092 | P2 | Test how the vehicle limits change the result | M | [[US-090-093-routing-paper-experiments-stories]] 3 | `US-091` (its harness and pair set). Moves to Sprint 13 if the harness slips | None yet | - | Not started |
| US-093 | P2 | Measure how often the sticky rule gives no route or a longer route than an arrival-only reference | S | [[US-090-093-routing-paper-experiments-stories]] 4 | `US-047`, `US-050` (both `Done`), the depth tables of the replay, and the sampler of `US-091` (copyable) | None yet | - | Not started |
| US-086 | P2 | Prune old rows of `flood_road_values` | S | [[core-output-hygiene-stories]] 1 | `US-073`, and `US-094` (the 24-hour prune is safe only if the archive works, D-017). The size reading is better after `US-089` | None yet | - | Not started |
| US-087 | P3 | Make `test_flood_areas.py` run without hand-set paths, and run it in CI | S | [[core-output-hygiene-stories]] 2 | None | None yet | - | Not started |

## Backlog


Nothing here has a sprint number.

| Item | Why it has no sprint | Linked risk |
| ---- | -------------------- | ----------- |
| Sweep alternative routes across departures | Build only if the timeline often says "blocked" while a detour exists. | [[departure-time-advice-research]], step 2 |
| Precompute per-run piece windows for the timeline | Build only if the request-time query proves slow. | [[departure-time-advice-research]] |
| Saved routes and push alerts | Need accounts and an alert channel, which do not exist. | [[departure-time-advice-research]] |
| Enable `osm_way_id` in the graph | A second route to the same key. Revisit only if edge geometry sampling proves wrong. | [[edge-depth-table]] |
| `US-061` Show the place name faster after a map tap ([[frontend-polish]] Story 7) | Lowest priority. The user said to tackle it later. | [[place-name-slow-after-map-tap]] |

Story R10 had a gate, and the user cleared it on 2026-10-02 by setting the latency factor to 2. The gates on Stories R5
and E7 were cleared the same day ([[sprint-plan-2]]).

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Sprint 12 holds four M and four S rows and is also the slip buffer. `US-088` and `US-089` started early, so the open work is smaller | A slip in Sprints 9 to 11 has little room | `US-087` (S, P3) is the first row to move to Sprint 13 of [[sprint-plan-4]], then `US-086` (S, P2). `US-088` and `US-089` (P1) stay, because the deferred DAG analysis needs them. The experiments `US-090` and `US-091` (P1) stay, because the user said to finish the routing first. Moving a row the user placed needs the user's go. |
| `US-092` reuses the harness and the pair set of `US-091` inside one week | A story that reads another story's output belongs in a later sprint (`.claude/CLAUDE.md`, rule 3). The user placed both in Sprint 12, so the rule bends | `US-091` builds the harness first, and `US-092` starts when the harness runs on one vehicle. If the harness is not working by the middle of the sprint, `US-092` moves to Sprint 13 of [[sprint-plan-4]], with the user's go. |
| The experiments need the replay data and the engine proof | `US-091` and `US-093` read depth tables, and the edge depth table keeps only the newest 3 runs (`EDGE_TABLE_KEEP_RUNS=3`). The 12-hour replay ends at 03:00 +07 on 2026-10-09, and `US-055` is still `In progress` | Copy the tables of the replay off the server before retention removes them, and record the run names in the result file. `US-055` already passed `compare`, `crossings`, `departures`, and `latency` on 2026-10-07. Only its DAG-timing pieces are open. |
| A result without a named storm is read as a measured rate | The paper would overstate what the model shows | Each story of [[US-090-093-routing-paper-experiments-stories]] names its storm and says the depths are 3Di output. The real 2026-09-16 replay is real rain. The 50 mm/h storm is synthetic. |
| `US-095` drops 2,428 MB of `netcdf_values` and cannot be undone, and `US-094` can be proven only on real rain, which the replay does not give | The drop could run before the archive holds a real storm, and a dry week would stall Sprint 11 | The drop needs `US-094` proven and the user's explicit go. If no real rain falls by the end of Sprint 11, `US-095` moves to the next plan, with the user's go, or the user accepts a one-off real-rain run as proof (open question 4 in [[US-094-095-archive-and-netcdf-retirement-stories]]). `US-094` is M and sits in Sprint 10 beside `US-055` (M) and `US-070` (S). |
| The proof of `US-094` waits for a real forecast above the 5 mm/h rain gate | `US-094`, `US-095` (Sprint 11), and `US-086` (Sprint 12) cannot close until it rains. A dry spell stops all three. | The user chose to wait, with no gate change and no override (2026-10-08). If no qualifying forecast arrives, move the three rows to the next plan or ask the user to change the proof. |
| Plan 2 slips, so Story R5 or E5 is not `Done` when Sprint 9 starts | Sprint 9 cannot start its rows | Sprint 12 absorbs a small slip. Beyond that, start a new plan and move rows. |
| The fallback is today's single-step model | A fallback response can still send a traveller into rising water | The response carries a flag and the frontend says "timing check unavailable". Track how often the fallback runs. |
| The chart and the engine show different depths | Two numbers for one route on one screen | Both sample the same tiles. Note the spacing difference in the chart's documentation. |
| The user had not set the latency factor | Closed on 2026-10-02. The factor is 2 | Story R10 passes when the p50 and p95 of each trip and vehicle stay within 2 times the baseline of Story R1. |

## Definition of done for a story

The same as [[sprint-plan-2]]: acceptance criteria pass on the server where they say so, tests pass, the concept page is
updated with `last_updated` bumped, and a screenshot or rendered output plus numbered details are recorded in the epic
file and in this plan.

## Status history

- **2026-09-29, active.** Split from the first draft of [[sprint-plan-2]], which had six sprints, so each plan covers four
  weeks. Sprints 9 and 10 moved here with the backlog and the plan-3 risks. The carried `DESIGN.md` row from [[sprint-plan]]
  is in Sprint 11, and Sprint 12 is spare.
- **2026-09-30, active.** Every row in the sprint tables now starts with an `Item` column that holds the story's ID (`US-nnn`).
- **2026-10-02, active.** `US-061` (show the place name faster after a map tap) is in the backlog table with no sprint, as P3. The user said to tackle it later.
- **2026-10-02, active.** The gate on `US-055` is cleared. The user set the latency factor to 2 times the baseline of `US-046`. No row of this plan has an open gate.
- **2026-10-05, active.** Sprint 9 started on 2026-10-05, 42 days before its planned start of 2026-11-16, at the user's request. Its rows are `US-052`, `US-051`, and `US-053`. The dependencies from [[sprint-plan-2]] are met: `US-050` (the engine) and `US-043` (the Java reader) are `Done`. The user wants every row of this plan built and tested before the engine goes to the server once, with no builds on the server until the 48-hour replay ends. Sprint 10 (`US-054`, `US-055`) keeps its place and starts when `US-053` is built, so its rows enter `TODOS.md` then (rule 9). No blocker stops Sprint 10, checked on 2026-10-05.
- **2026-10-05, active.** [[time-aware-routing-engine-stories]] Story R7 (`US-052`) moved from `Not started` to `Reviewed`. Built tests first (118 Java module tests and 27 Python tests, and the flag-on path in `test_server.py`). It stays `Reviewed` until the deployed image runs on the server in `US-055`. Plan: [[time-aware-backend-integration]].
- **2026-10-05, active.** [[time-aware-routing-engine-stories]] Story R6 (`US-051`) moved from `Not started` to `Reviewed`. `truck` (35 cm) and `foot` (40 cm) have `td_limit_cm` in `config.yml`, and `ScenarioReport` runs 32 scenarios for the four vehicles. 119 Java module tests and 27 Python tests pass. It stays `Reviewed` until the server run in `US-055`.
- **2026-10-05, active.** [[time-aware-routing-engine-stories]] Story R8 (`US-053`) moved from `Not started` to `Reviewed`. All three Sprint 9 rows are built and tested (Java 123 module tests, Python 30 + 21 + 27 tests, and `test_server.py` for the flag and the endpoint). They stay `Reviewed` until the server run in `US-055`. Sprint 10 starts next (`US-054`, `US-055`).
- **2026-10-05, active.** Sprint 10 started on 2026-10-05, 49 days before its planned start of 2026-11-23, because its dependency `US-053` is built (`Reviewed`) and the user wants everything built before the one test on the server. Its rows are `US-054` and `US-055`. `US-055` needs the 48-hour replay to end before its server run, since no image builds on the server until then. Sprints 9 and 10 stay open until the server proof. No blocker stops Sprint 11 (`US-033`), checked on 2026-10-05.
- **2026-10-05, active.** [[time-aware-routing-engine-stories]] Story R9 (`US-054`) moved from `Not started` to `Reviewed`. Built tests first in the frontend (25 new tests, 304 in all pass, `tsc` clean, production build compiles). It stays `Reviewed` until the alert is seen against the real backend in `US-055`. Plan: [[wait-until-alert]].
- **2026-10-05, active.** [[time-aware-routing-engine-stories]] Story R10 (`US-055`) moved from `Not started` to `In progress`. The proof tooling and the one-shot runbook are built and tested (`scripts/routing_proof/`, plan [[engine-server-proof-and-rollout]]). The evidence is one run of `rollout.ps1` on the server after the 48-hour replay ends, which is also the first run of that script. `US-052`, `US-051`, `US-053`, and `US-054` stay `Reviewed` until then.
- **2026-10-05, active.** New row `US-070` (Sprint 10, P1, S): task 9c ran over 770 s in one step during the replay. Blocker [[9c-sampling-step-runs-over-770-seconds]], case under rule 11: does not block build in the next sprint, so the fix was built here and Sprint 11 is not held. `ANALYZE` before sampling and a 120 s step limit, pushed as `5e358bf`, status `Reviewed` until the server shows the next 9c log. `US-045` and `US-055` read its result.
- **2026-10-06, active.** New rows `US-071` to `US-075` in Sprint 11, at the user's request: make routing the first consumer of an explicit core output contract, so the system is ready for other applications without building them ([[routing-first-consumer-stories]], plan [[routing-first-consumer-contract]]). Sprint 11 now holds one M carried row (`US-033`, P3) and five new rows (one M, four S), so it is fuller than the other sprints. If it slips, `US-033` (P3, no dependency) is the first to move to Sprint 12, which needs the user's go because the user placed it. `US-072` needs the server, so its evidence waits for `US-055`. No blocker stops Sprint 11, and the stories are not yet in `TODOS.md` because Sprint 11 has not started (rule 9).
- **2026-10-06, active.** `US-073` changed from a TaskGroup (S) to a separate `routing_adapter` DAG triggered by an asset event from `9b_load_depth_raster` (M), at the user's request. Sprint 11 now holds two M rows (`US-033`, `US-071`), one more M (`US-073`) and three S, so it is the fullest sprint. `US-033` (P3, no dependency) is still the first row to move to Sprint 12 if it slips, and that needs the user's go. The TaskGroup is the fallback if the asset trigger gives trouble. Plan: [[routing-first-consumer-contract]].
- **2026-10-07, active.** Sprint 11 started on 2026-10-07, 54 days before its planned start of 2026-11-30, at the user's request. Its rows are `US-033`, `US-071`, `US-072`, `US-073`, `US-074`, and `US-075`, and they entered `TODOS.md` (rule 9). No blocker stops any row, checked on 2026-10-07. `US-072` and `US-073` cannot reach `Done` before `US-055`, which waits for the replay to end at 00:00 +07 on 2026-10-08. A frontend recheck against the mockup found seven differences with no story ([[frontend-mockup-recheck-and-sprint-11-start]]). `US-033` extracts tokens from the shipped UI, so it should follow any story that changes the UI.
- **2026-10-07, active.** New rows `US-076` to `US-085` in Sprint 12, at the user's request: every difference of the frontend recheck becomes a story, and a browser comparison in Aside runs first ([[frontend-mockup-recheck-stories]]). Sprint 12 was empty, so the plan still has four sprints (rule 10). It now holds one M, seven S, and two XS rows, so it is full, and it is also the slip buffer. The first rows to move to the next plan are `US-083`, `US-082`, and `US-081`, which needs the user's go. The sprint is not started, so the rows are not in `TODOS.md` (rule 9). Decision D-010: the legend keeps "As of" and the "Powered by GraphHopper" line goes.
- **2026-10-07, active.** `US-033` (`DESIGN.md`) moved from Sprint 11 to the last place in Sprint 12, at the user's request, because it extracts tokens from the UI that `US-077` to `US-083` change. Sprint 11 now holds five rows (`US-071` to `US-075`), and Sprint 12 holds two M, seven S, and two XS rows. `US-033` left `TODOS.md`, because Sprint 12 has not started (rule 9).
- **2026-10-07, active.** Branch `modular` holds all five Sprint 11 rows, built and tested locally: `US-071` (contract page, live schema and key check, which passed on the server's backend container), `US-072` (read-only role, not yet run against the database), `US-073` (`routing_adapter` DAG on an asset event, serialized by Airflow 3.1.7 on the server, trigger and 9c timing not yet observed), `US-074` (one owner for the vehicle limits) and `US-075` (guard test on the backend's SQL). All five are `Reviewed`. None is `Done`: each lacks its evidence screenshot, and `US-072` and `US-073` also wait for `US-055` and the end of the replay at 00:00 +07 on 2026-10-08. The user wants everything built before any further 48-hour run, because a run is costly.
- **2026-10-07, active.** The user decided (D-011) to build all of Sprint 11 before the next server run and to deploy once. The order of the server work is in [[sprint-11-server-rollout]]. `US-071` to `US-075` and `US-051` to `US-055` close from that one deploy and one run of about one hour. A finding with no story: `flood_road_values` has no retention prune. It needs a story and a sprint from the user (rule 9).
- **2026-10-07, active.** The replay was still running at this check (42 of 48 hours, `flood_mapping_full` unpaused), so the user asked to hold off on `rollout.ps1` and anything that recreates `graphhopper` or `floodmap-backend`, while continuing read-only work. `US-072`'s steps 3 to 5 of [[sprint-11-server-rollout]] ran: `ROUTING_READER_PASSWORD` set in `.env`, the `routing_reader` role created (reads the 5 contract tables, confirmed on host ADMIN), and the `routing_adapter` Airflow pool created. `US-071`, `US-074`, and `US-075` need no rebuild, so their evidence was captured now and they moved to `Done` in `TODOS.md` and above. `US-072` and `US-073` still wait for `rollout.ps1`. A subagent checked `US-045` and `US-069` against the live replay: neither is ready to close. `routing_adapter` only started running 2 hours before the check, so 9c has one real data point (60.1 s build, 8.21 min past `3_calculate_depth`, over the 5-minute limit, but indistinguishable from the new DAG's cold start at n=1), and `table_timing.ps1` has no `ST_Value` spot-check. The 42-hour storage reading shows `flood_extent_polygon` and `edge_depth_tables` holding their retention caps, but `docker_data.vhdx` and `netcdf_values` are still growing, and no 24-hour reading exists to compare against. Both wait for the 48-hour mark and more `routing_adapter` runs; see `TODOS.md`.
- **2026-10-07, active.** `flood_mapping_full` paused (user's call, ahead of the natural 48-hour end), so `rollout.ps1` ran on host ADMIN against `modular`. `graphhopper` needed a graph re-import first (`US-051`'s profile fingerprint change; the app's own edge-based graph hash held, so the table stayed valid, see [[graph-reimport-procedure]]). Every check not needing the DAG then passed: `scenario-check.sh` (32/32), and the engine proof's `compare` (37.5% changed, median detour 0.94), `crossings` (0), `departures` (3/3), and `latency` (6/6 within 2x baseline) against 24 real pairs. `US-051`, `US-052`, `US-053`, and `US-072` moved to `Done` above. `US-054`'s browser check and `US-073`'s DAG-timing measurement, along with `US-045` and `US-069`, are deferred to after Sprint 11 at the user's request, to be tested together. `US-055` stays `In progress` pending those.
- **2026-10-07, active.** `US-054`'s browser check completed: drove the deployed frontend by hand (`type`/`Enter`, not URL params; needed a fresh clear-and-retype cycle per field) with a pair noted elsewhere as currently blocked, and the alert rendered the acceptance text exactly. `US-054` moved to `Done`. `US-055` now has only `US-045` left among its own dependencies, deferred with the rest of the DAG-timing work until after Sprint 11.
- **2026-10-07, active.** Four rows added to Sprint 12 at the user's request, from the log of 2026-10-07 and a new ask: `US-086` (prune `flood_road_values`, S, P2), `US-087` (run `test_flood_areas.py` in CI, S, P3), `US-088` (cut the storm of 2026-09-16/17 into a replay event, S, P1), and `US-089` (start and stop a replay with one command, M, P1). Sprint 12 now holds three M, ten S, and two XS rows, over the size of one week, so the move order is in the Risks table. No row was moved. The user asked to build `US-088` and `US-089` before Sprint 12 starts, so both are `In progress` while Sprint 12 has no actual start date, and neither is in `TODOS.md`, which holds only the current sprint (rule 9).
- **2026-10-07, active.** [[rain-replay-test-environment-stories]] Story 2 (`US-089`) moved from `In progress` to `Reviewed`. Built and merged into `modular`, 58 Python tests pass, `replay.ps1` not yet run on the server. `US-088` stays `In progress`: the NASA download hosts did not answer from the build session, so the user runs the download on the Mac.
- **2026-10-08, active.** `US-088` has its data and `US-089` has its first server run, both started before Sprint 12 begins. The event is `scripts/rain_events/hanoi_20260916_storm.csv` (12 hours, 53.88 mm, peak 8.73 mm/h), after the user decided that a replay runs 12 hours only (D-012 in [[decision-log]]). `replay.ps1 start` ran on the server and its read-back matched. Neither row is `Done`: `US-088` needs an evidence screenshot, and `US-089` needs `stop` and a screenshot. The user chose to start Sprint 12 on 2026-10-09, 59 days before its planned start of 2026-12-07, so its rows enter `TODOS.md` then and its Actual start is filled in then (rules 9 and 10).
- **2026-10-08, active.** The 12-hour replay on the server (first run 15:45 +07, last 03:00 +07 on 2026-10-09, 42 runs) serves the deferred analysis: `US-045`, `US-069`, `US-070`, and `US-073`. `US-069` cannot show its 24-hour to 48-hour comparison in 12 hours, so its pass condition needs the user's decision. This is not a blocker for Sprint 12.
- **2026-10-08, active.** Four new rows in Sprint 12, at the user's request ("From P1-P4 lets move them to sprint 12, and the front end can be sprint 13. We need to finish the routing first."): `US-090` (the FIFO lemma and proof, M, P1), `US-091` (the violation rate of single-timestep routes, M, P1), `US-092` (the vehicle limit sensitivity, M, P2), and `US-093` (the cost of sticky closure, S, P2), in [[US-090-093-routing-paper-experiments-stories]]. They come from the work items P1 to P4 of [[paper-handoff-routing-and-system]]. `US-092` reads the harness of `US-091` in the same sprint, which bends rule 3 at the user's placement, and the Risks table gives its fallback.
- **2026-10-08, active.** The backlog row "Measure how many routes arrival-only closure would change" is now `US-093` in Sprint 12, and it is removed from the backlog table. The row said it needed the engine shipped. The engine is deployed behind the flag (`US-052`, `Done`), so only the arrival-only search and the replay's depth tables are missing.
- **2026-10-08, active.** `US-076` to `US-085` (the frontend recheck, [[frontend-mockup-recheck-stories]]) moved from Sprint 12 to [[sprint-plan-4]], at the user's request. Sprint 13 is the first sprint of plan 4, because this plan ends with Sprint 12 and a plan covers four sprints (rule 10). The dependencies set the sprint of each row: see [[sprint-plan-4]]. Not in `TODOS.md`, so nothing to move there.
- **2026-10-08, active.** `US-033` (`DESIGN.md`, [[carried-over-backlog]] Story 2) moved from Sprint 12 to the next plan. It reads the UI that `US-077` to `US-083` finish, and the chain `US-076`, `US-077`, `US-082`, `US-083` fills Sprints 13 to 16 of [[sprint-plan-4]], so no sprint is left after `US-083`. It is listed under "Carried to plan 5" there. This goes against the wording of the user's decision (Sprint 13) and follows rule 3. The user is asked to confirm.
- **2026-10-08, active.** Sprint 12 now holds four M and four S rows: `US-090` to `US-093`, `US-088`, `US-089`, `US-086`, and `US-087`. `TODOS.md` still says the next sprint holds 15 rows. It is corrected in the same pass. Sprint 12 still starts on 2026-10-09 at the user's request, and its rows enter `TODOS.md` then (rule 9).
- **2026-10-08, active.** Two rows added at the user's request, from D-016 and D-018 in [[decision-log]]: `US-094` (archive `results_3di.nc` and a run record to D: with real rain, M, P1, Sprint 10) and `US-095` (retire the `netcdf_values` ingest, M, P1, Sprint 11, the user's choice). `US-094` is in Sprint 10 because `US-095` reads its output, and Sprint 10 is the earliest sprint before Sprint 11 (rule 3). This is a decision made by dependency, and the user can override it. `US-086` (Sprint 12) now depends on `US-094`, because its 24-hour prune is safe only if the archive works (D-017). Both rows enter `TODOS.md` now, because Sprints 9 to 11 are the current sprint. Source: [[US-094-095-archive-and-netcdf-retirement-stories]].
