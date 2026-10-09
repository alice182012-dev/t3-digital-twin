---
date_drafted: 2026-09-29
type: user-story
us_id: "US-064"
story_label: "9"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P1
estimate: S
sprint: 5
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Make the soak check fail when it cannot read the server"
---

# US-064 Make the soak check fail when it cannot read the server

As the engineer who owns routing, I want `run_soak.sh` to exit with 1 when a Docker call or a log read fails, so a Docker outage cannot look like a passing soak.
Given Docker on `remote-server` answers every call with HTTP 500, as it did on 2026-10-02 at 13:53 +07, when `run_soak.sh` runs, then it exits with 1 and names the call that failed. Given a log file with no request lines or no timestamps, when `soak_checks.py logs` reads it, then it exits with 1. Added during the work, because the script and [[graphhopper-backend]] already promised it: when a container started after the soak start, was OOM killed, or is not running, then it exits with 1.
Found: on 2026-10-02 at 13:53 +07 the script printed "0 requests, 0 5xx, 0 error lines" for all three logs and ended with "logs exit 0", because `run_logs` fails only on a 5xx or an error line, and `run_soak.sh` writes SSH errors into the log files. The `roads` check did exit with 1.
Dependencies: None. It needs no server, because the tests use empty files and a fake `docker` on the path.
Evidence: ![[us-064-soak-check-output.png|700]]
Details:
1. What: `run_soak.sh` exits with 1 when a Docker call fails, when a log has no timestamped line, and when a container started inside the soak window, was OOM killed, or is not running.
2. How: tests first (13 new, 42 in `scripts/backend_soak/`). `soak_checks.py logs` now fails a file with no timestamped line and prints its first line. A new `containers` command (`judge_containers`) compares each container's start time with the soak start as an instant. `run_soak.sh` counts failed `docker inspect` and `docker logs` calls and names each one. The tests run the script with a fake `docker` and `ssh` on the path.
3. Why: on 2026-10-02 at 13:53 +07 the old script printed "0 requests, 0 5xx, 0 error lines" and "logs exit 0" while Docker answered HTTP 500 on every call. The old script also never checked the container start times, although its header and [[graphhopper-backend]] said it did.
4. Effect: a replayed outage exits with 1 and lists five failed calls, and a healthy fake server exits with 0. `US-034` can no longer pass on an unreadable server. The real host is not tested. The exit status of the `ssh` and PowerShell filter is not checked, so a failed `ssh` shows up as a log with no timestamped line. The first run on the real server shows whether a healthy host passes.
