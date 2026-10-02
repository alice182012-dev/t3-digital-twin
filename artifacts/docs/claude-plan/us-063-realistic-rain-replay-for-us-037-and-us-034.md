---
date: 2026-10-02
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, pipeline, rain, us-037, us-034, us-063, sprint-5]
related: ["[[carried-over-backlog]]", "[[sprint-plan-2]]", "[[sprint-plan]]", "[[us-037-narrow-the-per-run-critical-path]]", "[[map-shows-forecast-not-now]]", "[[3di-simulation-orchestration]]", "[[graphhopper-backend]]", "[[2026-10-02]]"]
---

# Plan: replay a realistic 48-hour rain for US-037 and US-034

## Context

`US-037` passed on 2026-10-02 with a constant test rain of 50 mm/h (`FLOOD_TEST_RAIN_MM_HR`). The user stopped the pipeline the same day, because a rain that never changes and never stops is not a real event. The tile build grew about 0.6 minutes per run under it, so that pass only covers the first hour of an extreme storm. The `US-034` soak started under the same rain, so its window is void.

The user supplied a real event, the Hanoi rain of 2025-10-05 to 2025-10-08, and asked to cut it to 48 hours and run both stories under it.

## Source and unit

The source is `hyetograph_20251005_20251008.csv` in `test-code/Test event/recreate event 20251007/rain input/gpm-to-csv/`. It has 131 half-hour rows with UTC timestamps and two rate columns. `precipitation_mm_per_30min` is the column of the file the user first named (`Rainfall_event_20251005-08 copy.csv`), and `precipitation_mm_hr` is exactly twice that column on every row. The pipeline takes mm/h, so the replay reads `precipitation_mm_hr`.

- Total rain: 250.7 mm.
- Peak: 56.48 mm/h at 2025-10-06T23:00Z.

## The 48-hour window

The window that holds the most rain starts at 2025-10-05T22:30Z and ends at 2025-10-07T22:30Z. It keeps 246.8 mm of the 250.7 mm, starts at 0.65 mm/h, and ends at 0.005 mm/h. The cut drops 3.9 mm of light rain from the two ends.

## Gate effect

A run skips as a dry cycle unless any 15-minute rate in its 2-hour lookahead reaches `FLOOD_RAIN_THRESHOLD_MM_HR`. The server's `.env` sets the gate to 0.01 mm/h, so all 192 runs in the window simulate as one chain. At the compose default of 5 mm/h, 104 of the 192 runs simulate. At 2 mm/h, 156 simulate, and at 1 mm/h, 174. The plan keeps the server's 0.01 mm/h. It is the configuration the server already runs, and a continuous chain gives the heaviest load for the retest and keeps the hotstart chain. The risk is the 3Di session limit.

## Design

The data shape is one table of `(offset_minutes, mm_per_hour)` rows, step 30 minutes, offset 0 at a start time the operator sets.

1. `scripts/rain_replay.py` is a pure module. `cut_window` cuts the source rows to a window and rebases the offsets. `load_event` reads the cut file. `replay_intervals` returns the 15-minute interval list in the same shape `build_fixed_rain_intervals` returns, so nothing downstream changes.
2. Each interval takes the rate of the last sample at or before its start (the 30-minute rate holds for both of its 15-minute intervals). Offsets before 0 and after the last sample give 0 mm/h.
3. `create_simulation.get_rain_forecast` reads two new variables. `FLOOD_TEST_RAIN_CSV` is the event file and `FLOOD_TEST_RAIN_START` is the UTC start, aligned to a 15-minute slot. Setting only one, or setting either together with `FLOOD_TEST_RAIN_MM_HR`, raises an error, so a half-set test cannot run silently on live Tomorrow.io data.
4. The event file is `scripts/rain_events/hanoi_20251005_48h.csv`. It lives under `scripts/`, which the server pulls with git and mounts into the containers. `data/` is ignored by git and would not reach the server.

## Work that needs no server

The user keeps the server untouched for now, although Docker works again. Everything in this list runs on the Mac, with tests first.

1. `US-063`, schedule preview. Add `simulating_slots` to `scripts/rain_replay.py`. It lists the 192 slots of the window that pass the rain gate and marks each slot that starts a new chain after a dry gap. A test pins 104, 156, and 174 simulating runs at 5, 2, and 1 mm/h, and chains of 26, 46, 10, 10, and 12 runs at 5 mm/h. The user reads the list to choose the replay start and to see which slots to watch.
2. `US-064`, a soak check that fails loudly. Today `run_logs` exits with 0 for a log with no requests, and `run_soak.sh` writes SSH errors into the log files. Tests first: an empty log, a log of SSH error text only, and a fake `docker` on the path that exits with 1. Then `run_logs` exits with 1 for a log with no request lines or no timestamps, and `run_soak.sh` exits with 1 and names the failed call.
3. `US-065`, a margin report for every run. Move `run_margins.sh` from `marie-curie/us-037/`, which git does not track, to `scripts/pipeline_margins/`. Write `report.py` to read its rows and the slot list of step 1. It prints the run count, the worst, median, and best margin, the late runs, the missing runs, and the slope of the margin per run inside each chain. It exits with 0 only if no run is late and none is missing. The fixture is the four runs of 2026-10-02 (+1.9, +4.1, +2.7, +2.4 minutes).
4. Server runbook. Write the exact commands for the later server steps, in the PowerShell form the lesson [[recreate-remote-services-on-the-remote-host]] requires, and do not run them. The steps are `git pull` on the server, the three variables in `.env`, `docker compose up -d --no-deps` for the worker, unpausing `flood_mapping_full`, and the two verdict commands.
5. Local commits in small units, when the user asks: the replay module and event file, the compose and `.env.example` change, the soak fix, the margin report, and the vault edits. Nothing is pushed.

## Work that waits for the server

- Set the replay start in `.env`, recreate the worker, and unpause `flood_mapping_full`.
- Run the 48 hours, then the margin report for `US-037` and `run_soak.sh` for `US-034`.
- Capture the evidence screenshots, taken on the server as the acceptance criteria say.
- Check that the log line `Replaying` appears, and that the run at the peak slot reads 56.48 mm/h.

## Decisions the user owes

None of these needs the server.

1. The margin by which step 1 must publish before it becomes now. `US-037` names none, and the retest needs a pass mark. A positive margin is the current reading.
2. The rain gate for the replay. The plan keeps 5 mm/h. Lower values simulate more runs (156 at 2 mm/h and 174 at 1 mm/h) and add flood area to every run.
3. The replay start time, on a 15-minute slot. The suggestion is the first slot at least 30 minutes after the worker is recreated.
4. The refresh interval for `US-062`. The research recommends keeping 15 minutes and showing the age of the map.
5. Three gates of [[routing-not-time-aware]] that stay open: the sticky-from-departure wording for `US-050`, the build-time limit for `US-045`, and the latency factor for `US-055`. Also whether a trip that ends between minute 105 and minute 120 of a run returns `unknown`.

## Offline work from later sprints

These need no server, but they belong to Sprint 6 or later. Pulling one forward is the user's call.

- `US-049`, the Java module skeleton, the image, and the CI job. The Maven build and the LM admissibility unit test can run on the Mac. The image part needs Docker, which this project runs on the server only.
- A sticky routing check of the real GraphHopper response against the offline checker of `US-047`. It needs a recorded response, which the server must produce.

## Checks while the replay runs

The user runs these from the repository root on the Mac. All of them only read.

1. **Run report, every few hours.** It lists every late run and every run that should have simulated and did not. A failed run counts as missing. Read the lines "late runs" and "missing runs", and the exit code.
   ```
   sh scripts/pipeline_margins/run_margins.sh 250 | python3 scripts/pipeline_margins/report.py --event scripts/rain_events/hanoi_20251005_48h.csv --start 2026-10-02T09:00:00Z --threshold 0.01 --since "10-02 16:00"
   ```
2. **Backend soak, once a day.** Expect exit code 0. It adds a little test traffic to the soak window.
   ```
   sh scripts/backend_soak/run_soak.sh 2026-10-02T16:00:00+07:00
   ```
3. **Peak, 2026-10-03 after 16:35 +07.** The slot of 16:30 +07 is offset 1470 minutes, the peak of the event. Expect `Rain gate: max=56.48 mm/h`. This is the evidence for `US-063` that the replay reaches the server's gate. The same command on the 16:00 slot of 2026-10-02 printed `max=1.10 mm/h` on 2026-10-02.
   ```
   docker --context remote-server exec airflow_new-airflow-worker-1 sh -c 'grep -h -o "Rain gate: max=[0-9.]* mm/h" /opt/airflow/logs/dag_id=flood_mapping_full/run_id=scheduled__2026-10-03T09:30:00+00:00/task_id=0_check_forecast_rain/attempt=1.log'
   ```
4. **End of the window, after 16:00 +07 on 2026-10-04.** Run check 1 with `--until "10-04 15:45"` and check 2. Both exit with 0 for `US-037` and `US-034` to reach `Done`. Then render each output as the evidence image and fill the Details. Also delete `dags/zz_cold_start_probe_dag.py` on the server, which the user approved on 2026-10-02 for after the test. It is an unscheduled probe with 0 runs, and `./dags` is mounted into the containers, so the deletion waits for the end of the window.

If a run fails, read its `1_trigger_simulation` log first. An HTTP 429 means the 3Di organisation has no free session.

## Checks

- `US-037` passes when every simulated run in the window publishes step 1 before it becomes now, and the worst margin is recorded. The earlier pass counted four runs. This one counts all 192.
- `US-034` passes when `run_soak.sh` exits with 0 at the end of the 48 hours.

## Open items

- Docker on the server returned HTTP 500 on 2026-10-02 at 13:53 +07. A stopped `com.docker.service` caused it, and it works again. The log [[2026-10-02-disk-cleanup-and-d-drive-move]] records 18 healthy services at 15:09 +07. This session did not recheck the server. No step on the server runs before the user's go.
- That session recreated every container, moved `./data` and the `airflow-logs` volume to `D:\airflow_new_data\` (`DATA_HOST_PATH` and `AIRFLOW_LOGS_HOST_PATH`), and replaced the `mc` download in `minio-init`. Before the replay, check whether `flood_mapping_full` is still paused, and whether the server's `.env` has the two new path variables. The replay file lives under `scripts/`, which that move does not touch.
- A run cold-starts when the last simulating slot is more than 4 slots earlier, because each run saves states valid 1 and 2 slots later and a run hotstarts from a state at most 2 slots old. At the server's 0.01 mm/h only the first run cold-starts. At 5 mm/h, 4 of the 5 chains would start cold and lose the water the earlier burst built.
- The replay does not cover the 3Di organisation's session limit (HTTP 429), which hit once on 2026-10-01. A 192-run window may hit it again.

## Status history

- **2026-10-02, active.** Written after the user stopped the pipeline and gave the hyetograph. The unit was first read as mm/h from the file named in the request, which was wrong. The source file's own columns show mm per 30 minutes, so the replay uses `precipitation_mm_hr`.
- **2026-10-02, active.** Planned again at the user's request, with no server access. The run counts were corrected from 98 to 104 of 192 at 5 mm/h, using the pipeline's own gate. Added the schedule preview to `US-063`, two new stories (`US-064`, `US-065`), a runbook step, and the list of decisions the user owes.
- **2026-10-02, active.** Docker is back, per [[2026-10-02-disk-cleanup-and-d-drive-move]]. The server steps still wait for the user's go. Added the effects of the storage move to the open items.
- **2026-10-02, active.** Deployed. The user pushed `c3d398e` and ran the pull and the worker recreate on the server at 15:20 +07. A read-only check showed the worker with `FLOOD_TEST_RAIN_CSV`, `FLOOD_TEST_RAIN_START=2026-10-02T09:00:00Z`, an empty `FLOOD_TEST_RAIN_MM_HR`, and the gate at 0.01 mm/h. The files are in the container, the replay reads 0.65 mm/h at the 09:00Z slot, the DAG has 0 import errors, and `flood_mapping_full` is paused. The first run needs the unpause at about 15:55 +07. The gate of 0.01 mm/h, found on the server, changes the run count from 104 to 192.
- **2026-10-02, active.** The schedule preview (item 1) and the margin report (item 3, `US-065`) are done and committed. Run on the real rows of the 50 mm/h storm, the report shows the margin to the end of the tile task at +2.3 minutes in the 01:00 hour, +0.5 in the 02:00 hour, and -0.7 or lower from 03:00. Items 2 (`US-064`) and 5 (local commits) are done. Item 4, the runbook, is replaced by the commands that ran on the server at 15:20 +07.
- **2026-10-02, active.** Added the checks the user runs while the replay runs, with their commands and times. The peak command was tested on the 16:00 slot of 2026-10-02.
- **2026-10-02, active.** The evidence scripts for the end of the test are written and dry-run (`us-034-soak-check.sh`, `us-037-replay-check.sh`, `us-063-replay-check.sh` in `artifacts/docs/user-stories/evidence/`). The user decided not to change the retry setting of the trigger task. The first run of `run_soak.sh` on the real host passed its container check and its known-answer check.
- **2026-10-02, active.** The user approved the cleanup of the server's untracked items. The log of 2026-09-22 comes into git, the duplicate experiment folder is deleted, and the probe DAG is deleted after the window ends (step 4 above).
