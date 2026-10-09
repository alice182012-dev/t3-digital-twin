---
date_drafted: 2026-10-07
type: user-story
us_id: "US-088"
story_label: "1"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P1
estimate: S
sprint: 12
subsystem: rain-replay
related: ["[[EP-13-rain-replay-test-environment]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Cut the Hanoi storm of 2026-09-16 and 2026-09-17 into a replay event"
---

# US-088 Cut the Hanoi storm of 2026-09-16 and 2026-09-17 into a replay event

As a tester, I want the real storm of 2026-09-16 and 2026-09-17 as an event file, so a replay exercises the roads
inside the flood model's border under a sharper storm than the October 2025 one.
Given NASA's GPM IMERG half-hourly Late Run data for the window, when the download and the area average run for the
model extent, then the result is `scripts/rain_events/hanoi_20260916_storm.csv` with the header
`offset_minutes,precipitation_mm_hr` and rows 30 minutes apart, committed to git. A line in the plan records the
source window, the total in millimetres, and the peak in millimetres per hour. The file loads with `load_event` and
`python3 scripts/rain_replay.py preview` lists its chains at the gate that the replay uses.
The tools are the three scripts under `test-code/rain input/` (git-ignored, on the user's Mac). They have the paths and
the dates of an earlier event written into them, so the story runs a copy with the new dates, and the copy goes in
`marie-curie/`. Use the Late Run (`GPM_3IMERGHHL`). The Final Run (`GPM_3IMERGHH`, the value in
`download_gpm_imerg.py`) is published 3.5 to 4.5 months late. A CMR query on 2026-10-07 for 2026-09-16T00:00Z to 2026-09-18T00:00Z returned 97 Late Run granules and 0 Final Run granules. The folder
`GPM_3IMERGHHL_07-...` that the earlier event used confirms the Late Run was the working choice.
The news reports of the storm give station totals (about 200 mm at the heaviest stations) and no time series. The
event file comes from the satellite series and not from those totals. IMERG averages a 0.1 degree grid over the
model extent, so its total is lower than a station's. The story records both numbers and does not scale the series
to match the stations.
Priority: P1. Status: Done. Estimate: S. Sprint: 12. Dependencies: A NASA Earthdata login in `~/.netrc` on the
Mac, and the Python packages the scripts import (`earthaccess`, `h5py`, `fiona`, `pyproj`, `numpy`), which the Mac
has. The story needs no server.
Evidence: None yet.

## Evidence and details

**Evidence:** None. Needs the Earthdata login on the Mac

**Details:**

![[us-088-event-check-output.png|120]]
