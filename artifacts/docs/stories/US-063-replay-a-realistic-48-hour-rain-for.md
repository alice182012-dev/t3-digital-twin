---
date_drafted: 2026-09-29
type: user-story
us_id: "US-063"
story_label: "8"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P2
estimate: S
sprint: 5
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak"
---

# US-063 Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak

As the pipeline owner, I want the pipeline to run a recorded rain event instead of a constant 50 mm/h, so the per-run timing and the 48-hour soak are measured under a load that happens in practice.
Given the hyetograph of the Hanoi rain of 2025-10-05 to 2025-10-08, when the pipeline replays its 48-hour window (2025-10-05T22:30Z to 2025-10-07T22:30Z, 246.8 mm, peak 56.48 mm/h) through `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START`, then each run reads the 2-hour lookahead of its own slot from the event, the rain gate skips the dry runs, and the other runs simulate until the window ends. At the 5 mm/h gate, 104 of the 192 runs simulate.
Priority: P2. Status: Done. Estimate: S. Sprint: 5 ([[SP-02-routing-engine-foundations|sprint-plan-2]]). Dependencies: None. Deployed and run on the server. Docker works again ([[2026-10-02-disk-cleanup-and-d-drive-move]]).
Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]]
Offline checks, done on 2026-10-02: `simulating_slots`, `chain_lengths`, and `describe` in `rain_replay.py`, and the command `python3 rain_replay.py preview EVENT START_UTC THRESHOLD`. Tests pin the counts the pipeline's own gate gives: 104, 156, 174, and 192 simulating runs at 5, 2, 1, and 0.01 mm/h, and chains of 26, 46, 10, 10, and 12 runs at 5 mm/h. A run cold-starts when the last simulating slot is more than 4 slots earlier. At 5 mm/h that gives 4 cold starts in 5 chains, and at 0.01 mm/h one, the first run. The report of Story 10 reads the same list.
Built on 2026-10-02: `scripts/rain_replay.py`, the event file `scripts/rain_events/hanoi_20251005_48h.csv`, and the two variables in `compose.yml` and `.env.example`. Tests first (9 in `scripts/test_rain_replay.py`, 2 in `test/test_flood_rain_gate.py`).
Evidence: ![[us-063-rain-replay-server-check.png|700]]
Details:
1. What: the replay ran on the server from 2026-10-02T09:00:00Z and completed 137 of the window's 192 slots before an unrelated incident cut it off. Every one of the 137 read the right event file and start time and gated correctly.
2. How: `dag_run` on `airflow_new-airflow-postgres-1` counts 137 runs of `flood_mapping_full` between 2026-10-02T09:00:00Z and 2026-10-04T09:00:00Z (136 `success`, 1 `failed`). The first run's log holds `🧪 Replaying /opt/airflow/scripts/rain_events/hanoi_20251005_48h.csv from 2026-10-02T09:00:00Z` and `Rain gate: max=1.10 mm/h, threshold=0.01 mm/h, intervals=9`. The run at the event's recorded peak (`scheduled__2026-10-03T09:30:00+00:00`, 16:30 +07) logs `Rain gate: max=56.48 mm/h`, matching the plan's prediction. All 137 completed runs took the `1_trigger_simulation` branch; the server's 0.01 mm/h gate never found a dry slot, so the dry-skip branch was never exercised live, though it is covered by the offline tests above.
3. Why: `US-037`'s retest and `US-034`'s soak both need a load that happens in practice, not a constant test rain.
4. Effect: the window did not finish. The last run (`scheduled__2026-10-03T19:00:00+00:00`) started on time but did not end until 2026-10-04T17:31:38Z, caught in the unrelated disk-full incident ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]), and the chain stopped there instead of reaching the 192nd slot (2026-10-04T09:00:00Z). `US-037` and `US-034` both need the fuller window and stay open until `scripts/pipeline_margins/report.py` and `run_soak.sh` run against it, or the window is replayed again.
5. Judgment call: this story's acceptance criteria describe the replay's behavior (read the lookahead, gate correctly, simulate until the window ends), not a run count, and that behavior held for every one of the 137 slots that ran, cut short only by an infra incident outside this story's logic. Closed as `Done` on that basis. Flagged for the human to confirm, since the criteria leave open whether a full 192-run window is required.
