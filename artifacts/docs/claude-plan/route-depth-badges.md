---
date: 2026-09-30
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [frontend, backend, sprint-3, depth-badges]
related: ["[[EP-01-frontend-depth-features|frontend-depth-features]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[US-001-depth-forecast-chart|depth-forecast-chart]]"]
---

# Per-point depth badges along the route

Story: [[EP-01-frontend-depth-features|frontend-depth-features]] Story 3. Mockup screen 2e shows four white pills on the route,
each with a dot in the depth-band color and text such as "8 cm", "22 cm", "5 cm", and "0 cm". The pills
mark where the depth changes, and they are not one per turn.

## Data shape

The backend returns one depth per sample along the route. The frontend turns samples into badges.

- `POST /flood/profile` takes `points` (`[lon, lat]` list), `valid_time`, and `run`. It resamples the
  route with the same rule as `POST /flood/forecast` (every 25 m, at most 200 samples) and reads
  `flood_depth_raster_tile` for that one timestep. It returns `{"samples": [{"lon", "lat", "depth_m"}]}`.
  `depth_m` is `null` outside the raster, and 0 for a dry or NoData pixel, as in the forecast.
- `depthBadges(samples)` in the frontend returns `{lon, lat, depthCm, bandId | null}` in route order.

## Badge rule

1. Each sample gets a level: the display band of its depth (see `depthScale.ts`), or "under 5 cm".
   Samples outside the raster are skipped.
2. Consecutive samples with the same level form a run.
3. A run shorter than 2 samples (about 50 m) is dropped unless it is deeper than both neighbors,
   because a short deep stretch is what a driver needs to know.
4. Neighboring runs with the same level merge.
5. A route with one run of "under 5 cm" gets no badges, because dry everywhere is not a change.
6. At most 6 badges. Above that, keep the first run, the last run, and the deepest of the rest.
7. A badge sits at its run's deepest sample and shows that depth. A run under 5 cm sits at its middle
   sample and reads "0 cm" when dry or "< 5 cm" when it has a trace.

## Steps

1. Backend: tests first, then `flood_profile.py` and the `/flood/profile` route in `server.py`.
2. Frontend: tests first for `depthBadges`, then the hook, the overlay component, and the wiring in `App.tsx`.
3. Check the profile against a hand calculation from `flood_depth_raster_tile`.
4. Preview build on the server against a preview backend, then deploy after the user approves.

## Status history

- **2026-09-30, active.** Plan written before code.
- **2026-09-30, active.** Built. Backend tests (`test_flood_profile.py`) and frontend tests (`depthBadges.test.ts`) written first. A preview build on the server showed 6 badges on a 6.4 km route. One bug found and fixed on the way: a `MapPopup` that unmounts leaves React removing a node OpenLayers moved, which blanks the app, so the badges use six always-mounted slots. Waiting for approval to deploy.
- **2026-09-30, done.** Deployed at `1b80cc3` and checked on the live site. Follow-up if wanted: space nearby badges by screen distance, since stretches about 100 m apart overlap at wide zoom.
