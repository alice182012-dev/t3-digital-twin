---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-13-rain-replay-test-environment]]"]
---

# EP-13-rain-replay-test-environment: archived story-level history

Lines moved out of the Status history of [[EP-13-rain-replay-test-environment]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-10-07, active.** `US-088` and `US-089` started at the user's request, before Sprint 12 starts. For `US-088`, the copies of the two scripts are in `marie-curie/us-088/` (`download.py`, `build_hyetograph.py`), and the download did not run. This session reached CMR but timed out on `urs.earthdata.nasa.gov` and `disc.gsfc.nasa.gov`, the login and download hosts, so it could not fetch a granule. The user runs `python3 download.py`, then `python3 build_hyetograph.py`, in that folder on the Mac. `US-089` is built in a separate worktree.
- **2026-10-08, active.** Decision from the user: a replay tests for 12 hours only, to save 3Di compute cost. `US-088`'s event file is the wettest 12 hours (24 steps of 30 minutes) of the 2026-09-16 to 2026-09-18 series, not the full storm. `marie-curie/us-088/build_hyetograph.py` now cuts that window and writes `hanoi_20260916_storm.csv`. The download did not run in this session: `urs.earthdata.nasa.gov` returned "No route to host" from the build session again, so the user runs `python3 download.py`, then `python3 build_hyetograph.py`, in that folder. The cut keeps the sharpest part of the storm, so the peak stays at the full-storm value and the total can be lower.
- **2026-10-08, active.** `US-088` data is in. The download ran on the Mac with an `EARTHDATA_TOKEN`, because `urs.earthdata.nasa.gov` is unreachable from the Mac and the server (the netrc login failed with "No route to host"; `cmr` and `data.gesdisc` answer). 97 Late Run granules, 2026-09-16T00:00Z to 2026-09-18T00:00Z. Full series: 84.95 mm total, peak 8.73 mm/h (area mean over the model extent). The 12-hour event `scripts/rain_events/hanoi_20260916_storm.csv` runs 2026-09-16T16:00Z to 2026-09-17T03:30Z: 53.88 mm, peak 8.73 mm/h, 24 rows. At the gate of 5 mm/h, `rain_replay.py check` lists 42 of 46 runs in 2 chains. The area mean is far below the station totals (about 200 mm), as the story expected, and was not scaled. Not committed yet.
- **2026-10-09, active.** `US-088` is `Done`. Evidence: `us-088-event-check-output.png` (24 rows, 53.88 mm, peak 8.73 mm/h, preview 42 runs in 2 chains, file tracked in git). The server ran 45 simulating runs, 3 more than the preview, and the cause is not yet checked.
