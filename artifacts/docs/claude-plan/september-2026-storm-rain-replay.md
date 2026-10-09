---
date: 2026-10-07
type: plan
branch: modular
status: active
tags: [plan, rain, replay, sprint-11, us-045, us-069, us-073]
related: ["[[us-063-realistic-rain-replay-for-us-037-and-us-034]]", "[[sprint-11-server-rollout]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]]"]
---

# Plan: replace the rain replay with the Hanoi storm of 2026-09-16 to 09-17

## Context

`US-045`, `US-069`, `US-073`'s DAG-timing measurement, and the final confirmation of `US-070` all need the core DAG to run under real rain for a while longer, after Sprint 11. The replay in `.env` (`hanoi_20251005_48h.csv`, `FLOOD_TEST_RAIN_START=2026-10-05T17:00:00Z`) is wall-clock anchored and its 48-hour window ends 2026-10-07T17:00Z, about 5 hours after this plan was written — too little time left to unpause and get a clean reading, and not raining live right now either. The user asked to mirror a real September 2026 Hanoi storm instead of the October 2025 one, specifically the 2026-09-16/17 event, not the whole month's 14 rainy days.

## Research: the 2026-09-16/17 Hanoi storm

A severe storm hit Hanoi overnight 2026-09-16 into the morning of 2026-09-17, part of a wider northern Vietnam flooding event.

- Rainfall across the city generally ranged **80 to 160 mm**, with the highest station totals **166 to 199 mm**: Dong Bong 1 (Tu Liem) 199 mm, Hai Ba Trung 188 mm, **Tay Mo 177.3 mm**, and Cau Giay-area stations 166 to 175.4 mm.
- **Tay Mo and Tu Liem are inside the flood model's border** (lon 105.7015 to 105.7971, lat 20.9754 to 21.0269, per this project's `CLAUDE.md`), so this event's heaviest rain fell inside the area the model actually covers — a better match than the October 2025 event for exercising the roads this project routes on.
- The rain was driven by southeasterly wind convergence from the surface to about 5,000 m altitude, falling overnight and producing street flooding reported by 6 a.m. on 09-17 (water close to 1 m deep in places).
- Wider event: parts of northern Vietnam saw over 50 cm in places; the event killed several people and submerged thousands of homes, concentrated in Ninh Binh and Thanh Hoa as well as Hanoi.
- For scale against the existing replay: the October 2025 event (`hanoi_20251005_48h.csv`) totals 250.7 mm over 48 hours with a peak of 56.48 mm/h. This September event is a similar total (roughly 200 mm at the heaviest stations) concentrated into a single overnight period of perhaps 8 to 12 hours rather than spread over 48, so its peak intensity is almost certainly well above 56.48 mm/h — a sharper, more extreme storm than what has been tested so far.

Sources:
- [Nearly 200mm of rain triggers widespread flooding in Hanoi — VietnamNet](https://vietnamnet.vn/en/nearly-200mm-of-rain-triggers-widespread-flooding-in-hanoi-2556078.html)
- [Heavy rain and floods in northern Vietnam submerge homes and disrupt economy — AP via CP24](https://www.cp24.com/news/world/2026/09/17/heavy-rain-and-floods-in-northern-vietnam-submerge-homes-and-disrupt-economy/)
- [Major flood threat develops after up to 1,321 mm of rain in Vietnam — The Watchers](https://watchers.news/2026/09/16/major-flood-threat-develops-after-up-to-1-321-mm-52-inches-of-rain-in-vietnam/)
- [Deadly floods strike Viet Nam: 16,000 homes submerged, 4 dead — The Vietnamese Magazine](https://thevietnamese.org/2026/09/deadly-floods-strike-viet-nam-16000-homes-submerged-4-dead/)

No minute-by-minute gauge series came from these sources (news reports give station totals, not a time series). The existing replay's source hyetograph (`hyetograph_20251005_20251008.csv`) came from a GPM-satellite-to-CSV tool under `test-code/`, which is git-ignored and local-only — it was never on this server and isn't on `modular`. The user will pull a real time series for the 2026-09-16/17 window with that same tool, on their own Mac, rather than this session approximating one from the news totals.

## Design: same shape as `US-063`'s replay, new source file

Nothing in `scripts/rain_replay.py` or `create_simulation.py` needs to change — the replay mechanism already takes any `(offset_minutes, mm_per_hour)` CSV via `FLOOD_TEST_RAIN_CSV` and any UTC start via `FLOOD_TEST_RAIN_START` ([[us-063-realistic-rain-replay-for-us-037-and-us-034]]). This is a new event file, not new code.

1. On the Mac, run the GPM-to-CSV tool for a window covering 2026-09-16 into 2026-09-17, cut to the period with the most rain (mirroring `cut_window`'s approach: drop light rain at both ends, keep the core event). Given the event is concentrated overnight rather than spread over 48 hours, the cut window likely wants to be shorter than the October replay's 48 hours — long enough to cover the full storm plus some lead-in/lead-out, short enough that the DAG doesn't run dry for hours before or after the rain. Decide the exact cut once the real series is in hand.
2. Save the result as `scripts/rain_events/hanoi_20260916_storm.csv` (same two-column shape as `hanoi_20251005_48h.csv`: `precipitation_mm_hr`, offset in minutes), with a header comment recording the source window and total/peak, matching the existing file's style.
3. Commit the new CSV under `scripts/rain_events/` (tracked by git, unlike `test-code/`), and push to `alice` so the server can pull it.
4. On the server: set `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START` in `.env` to the new file and a near-future 15-minute slot, recreate the worker (`--no-deps`), confirm the worker reads the new file and start with no import errors (same check as `us-063`'s status history), then unpause `flood_mapping_full`.
5. Run long enough to close the deferred items: a few hours at minimum for `US-073`'s trigger/timing and `US-070`'s confirmation (several `routing_adapter` runs), and however long the user wants for a cleaner `US-069` storage reading. `US-069`'s original "stops growing between hour 24 and hour 48" condition needs sustained running close to that length to mean anything, given `netcdf_values`'s 48-hour time-based retention.

## What this session did, and what's left on the Mac

Done here (host ADMIN, branch `modular`): the research above, and this plan. Nothing in `.env` or `scripts/rain_events/` changed on the server — the current October 2025 replay config is untouched, so nothing breaks if the user's Mac work takes a while.

Left for the user, on the Mac: run the GPM tool, produce and commit the new CSV, decide the exact cut window and how long to run it, then hand the server steps (3 and 4 above) back to a session running on the server (or run them over SSH from the Mac per `CLAUDE.md`'s Case 1).

## Status history

- **2026-10-07, active.** Plan written after the user asked to mirror a real September 2026 storm (not the full month) because the current replay's window ends in about 5 hours and nothing is raining live right now. Research found the 2026-09-16/17 Hanoi storm, with its heaviest rain at stations inside the flood model's border. The user will source the real time series via the GPM-to-CSV tool on their own Mac rather than this session approximating one.
