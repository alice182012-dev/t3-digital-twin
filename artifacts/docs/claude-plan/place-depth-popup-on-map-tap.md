---
date: 2026-09-29
type: plan
status: done
tags: [plan, frontend, popup, flood-points, geocoding]
related: ["[[frontend-depth-features]]", "[[frontend-todos-and-backend-dependencies]]", "[[point-depth-lookup-backend]]", "[[flood-routing-mockup-frontend-gap]]", "[[flood-points-connection-per-request]]", "[[mockup-screen-coverage]]"]
---

# Place-depth popup on map tap

Builds [[frontend-depth-features]] Story 1 (todo 3 in [[frontend-todos-and-backend-dependencies]]). Mockup
screen 2b: a card at the tapped point with the place name, address, coordinates, and a bold "Water
depth now: N cm" line.

## What the code check found

- **A plain click already opens the context menu.** `ContextMenu.tsx` registers `singleclick`, so a
  click sets a start, destination, or via point. The PRD said only right-click opens it. That was
  wrong.
- **There is no reverse geocoder.** `GET /geocode` is forward only (`q`), and `reverseGeocode` in
  `Api.ts` is a POI search by text and bounding box. Photon serves `/reverse?lat=&lon=`, and it
  returned "Ngõ 93 Phố Đại Linh, Dai Mo Ward, Hanoi" for the mockup's coordinates.
- **`GET /flood/points` needs `run`.** Without it the endpoint resolves the newest run overall and
  answers 404 when that run lacks the step. Each timestep already carries its `run`, so the popup
  sends both.

## Decisions

| Question | Decision | Why |
| -------- | -------- | --- |
| What does a plain click do? | In Flood mode it opens the popup. In Map mode it opens the context menu as before. Right-click and long touch always open the menu. | The mockup title is "Flood on", and a depth line means nothing without the flood layer. Map mode keeps click-to-set-start. |
| Where does the place name come from? | A new `GET /places/reverse?lat=&lon=` that calls Photon `/reverse` and reuses `_normalize_feature` (Vietnam filter, name fallback, address). | One normalized shape with `search_places`, and no change to the forward `/geocode` contract. |
| How is "now" worded? | "Water depth now" when the step is at or before now and within 45 minutes. "as of `time`" when older. "Forecast for `time`" when it is in the future. | The map can fall back to a future step or show a stale one, and "now" would then be wrong ([[map-shows-forecast-not-now]]). |
| Route button on the card? | Not in this story. | It is [[mockup-screen-coverage]] Story 1 (todo 6). |

## Data shape

```
DepthReading = wet { depthCm } | dry | no_data | unavailable
PlaceLookup  = loading | ready { place: Place | null, depth: DepthReading }
```

`unavailable` covers a failed request and a missing timestep. It reads as "Water depth unavailable",
never as 0 cm.

## Workstreams

| Stream | Files | Depends on |
| ------ | ----- | ---------- |
| Backend reverse lookup | `backend/place_search.py`, `backend/server.py`, `backend/test_place_search.py` | none |
| Depth text and response parsing (pure) | `src/floodmap/placeDepth.ts`, `test/floodmap/placeDepth.test.ts` | none |
| Popup and click wiring | `src/floodmap/PlaceDepthPopup.tsx` and its CSS, `src/layers/ContextMenu.tsx`, `src/App.tsx` | the two above |

Shared writes are `ContextMenu.tsx` and `App.tsx`, so they serialize after the pure pieces.

## Verification

Backend tests pass without network. Frontend jest runs inside the image's build stage, since jest is
not installed on the Mac. Live check on the server: in Flood mode, click a point, then screenshot the
card. Check a wet point, a dry point, and a point in Map mode (context menu still opens).

## Status history

- **2026-09-29, active.** Plan written after reading `ContextMenu.tsx`, `place_search.py`,
  `flood_points.py`, and the mockup. Architect skipped: one small component and one endpoint, and the
  shapes are fixed above. Implemented directly, since this session does not spawn subagents unasked.
- **2026-09-29, done.** Built and deployed (`floodmap-backend` and `flood-routing-frontend` recreated with
  `--no-deps`). Backend: `reverse_place` in `place_search.py` with a shared `_photon_features` helper, the
  `/places/reverse` route, and three tests in `test_place_search.py`. Frontend: `placeDepth.ts`,
  `PlaceDepthPopup.tsx` and its CSS, `ContextMenu.tsx` (an `onPlaceClick` prop), `App.tsx`. Checks: `tsc`
  clean and 22 jest suites (207 tests) pass, run on the server in the build image with the source mounted.
  Live: wet point 205 cm (endpoint 2.048 m), dry point 0 cm, popup with a route on screen, Map mode keeps
  the menu. Screenshots are `frontend-place-depth-*.png` under `docs/user-stories/evidence/`.

## Open items

- The address includes the postcode and country ("Đại lộ Thăng Long, Tây Mỗ, Hà Nội, 12008, Việt Nam"),
  where the mockup shows "Nam Từ Liêm, Hà Nội". `_address` in `place_search.py` is shared with the search
  results, so trimming it changes both.
- Photon returns the nearest OSM object, so a tap in an open field can name a building 50 m away. The
  coordinates line always shows the tapped point.
- The place lookup takes about 1.1 to 1.4 s and calls an outside service on every tap.
- The route button on the card is todo 6. The concurrent-tap latency check
  ([[point-depth-lookup-backend]] Story 4) has not run.
- The depth line loads independently of the place name. The ordering was not observed on screen. A capture
  half a second after the click showed both still loading.
- Building on the server over SSH fails on the Docker credential helper (`A specified logon session does not
  exist`), as in earlier deploys. Tests run there with `docker run` on the existing build image and the
  source bind-mounted, and images are built with `docker --context remote-server compose build` from the Mac.
