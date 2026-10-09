---
date_open: 2026-09-30
date_closed: 2026-09-30
type: blocker
status: resolved
severity: P3
subsystem: floodmap-backend
approaches_tried: 2
approaches_remaining: 0
tags: [blocker, backend, tests, raster, gdal]
related: ["[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[EP-06-raster-first-pipeline|raster-first-pipeline-stories]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-30
---

# test_server.py fails its tile-edge depth check on a clean HEAD

## Description

`floodmap/graphhopper-flood-road/backend/test_server.py` stops at its "edge of two tiles" check for
`GET /flood/points`:

```
AssertionError: ('edge of two tiles', {..., 'status': 'wet', 'depth_m': 794.9500122070312}, 788.940002441406)
```

The same failure happens on a clean copy of `HEAD` (checked with `git archive HEAD`), so no change of
2026-09-30 caused it. The corner-of-four-tiles check before it passes. The script stops at the failed
assertion, so the checks after it never run: an outside-raster point answering `no_data`, the 404 for a
run without that time, and the parameter validation loop.

Run with `GDAL 3.12.3` on a Mac against a throwaway `postgis/postgis:15-3.4` on the server.

## Cause

The test's reference point is not exactly on a pixel boundary. `tile_edge_lonlat(warped_tif, 2, 0.5)`
returns `105.84819099100002, 21.02903917251974`, which maps to column 511.9999999999655 and row
127.99999999999137 of the reprojected grid. The two tools break that near-tie differently.

| Tool | Pixel it reads | Value |
| ---- | -------------- | ----- |
| `gdallocationinfo` (the test's reference) | column 511, row 127 (rounds down) | 788.94 |
| `GET /flood/points` (PostGIS `ST_Value`) | column 512, row 128 | 794.95 |

The grid adds 0.01 per column and 6.00 per row, so 794.95 is 788.94 + 6.01, which is exactly the pixel one
column and one row further.

The endpoint does not follow one rule. The subagent that worked on the fix measured the other edge point,
the corner of four tiles: it sits at column 256.00000000006 and row 255.99999999998, and the endpoint reads
pixel (256, 255), which is the floor of both values and matches `gdallocationinfo`. So one point reads the
higher pixel and the other the lower one, even though the corner's row is 1.7e-11 below its boundary and the
edge's row is 8.6e-12 below. PostGIS's own arithmetic has noise, and no rule (floor, round, or "higher
index") explains both. An earlier version of this page said the endpoint follows a "higher index" rule. That
was wrong for the corner.

This is diagnosed from the numbers, not from a second environment. It is not checked whether an older
GDAL computes exactly 512.0 and so makes the check pass.

## Why this matters

- **Production:** no effect. A user's tap is an arbitrary float, and a tie on a boundary changes the answer
  by one pixel of about 10 m.
- **Regression coverage:** with this GDAL, `test_server.py` cannot end green, and it hides the checks after
  the failed one. It is the regression pass for `server.py`'s HTTP surface
  ([[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 1), so it should not be a check people learn to ignore.
- **Sprint 3:** blocks nothing. No Sprint 3 story depends on it. The changes to `server.py` this sprint
  (the route error shape and `POST /flood/profile`) have their own tests, `test_route_error.py`,
  `test_flood_profile.py`, and `test_flood_forecast.py`, and passed live checks.
- **Later:** the backend soak story ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 3, Sprint 5) wants a
  trustworthy regression pass, so it should be fixed before then.

## Approaches tried

### Approach 1: one reference per edge point (2026-09-30, rejected)

A subagent first read the pixel at `round(col), round(row)` for both points. That broke the corner check by one
row, so it used `gdallocationinfo` for the corner and the rounded pixel for the edge. `test_server.py` passed,
but only because of today's float noise, so another GDAL or PostGIS could flip it. Reworked before landing.

### Approach 2: accept the four pixels around the boundary (2026-09-30, landed)

`pixels_around_boundary` reads the 2x2 window around `(round(col), round(row))`, and the test requires the
endpoint's float32 value to be one of the four, with the four distinct. Landed as `03f7aa6` after review, and
rerun green against a fresh throwaway PostGIS: `test_server.py` exits 0 with every check run, and
`test_route_error.py`, `test_flood_profile.py`, and `test_flood_forecast.py` still pass.
![[test-server-tile-edge-fixed-output.png|420]]

## Candidate approaches

1. **Accept the four pixels around the boundary.** In `test_server.py`, for each edge point, require the
   endpoint's value to equal, as float32, one of the four pixels that touch the boundary
   (columns c-1 and c by rows r-1 and r, with c and r the rounded pixel coordinates), and check that those
   four values are distinct. Either neighbor is a correct answer on a boundary, and any other pixel or
   `no_data` still fails. One rule for both points, so a different GDAL cannot flip it. XS.

   Tried first and rejected: reading `round(col), round(row)` for both points broke the corner check, and
   special-casing each point with a different reference passes only because of today's noise.
2. **Move the reference point off the boundary.** Nudge it half a pixel into the intended pixel. Simple,
   but the check then no longer covers a point on a tile edge. Not recommended.
3. **Pin GDAL.** Not worth it for a test.

## Decision and explanation

Under rule 11 of `.claude/CLAUDE.md`, a blocker that does not block further build is fixed by a subagent
while the next work continues. This one does not block Sprint 4: none of its stories reads
`test_server.py`. It would matter to the Sprint 5 backend soak, so it is fixed now, well before that.
Approach 2 landed. The rule was checked on GDAL 3.12.3 with PostGIS 15-3.4 only.

## Concerns

The fix was built and checked on one GDAL and PostGIS pair. If the check fails on another pair, the fix
is in the choice of reference pixels, and the endpoint needs no change.

## Related topics

- [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]

## Status history

- **2026-09-30, open.** Found while running `test_server.py` after adding `POST /flood/profile`. Confirmed on
  a clean copy of `HEAD`. Cause diagnosed from the pixel values above. Not scheduled: it blocks nothing in
  Sprint 3, and the sprint is still to be chosen.
- **2026-09-30, open.** Rule 11 applied: does not block further build, so a subagent fixes it (see Decision and explanation). Story 6 of [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]].
- **2026-09-30, open.** The first subagent attempt showed the endpoint follows no single tie rule (see Description). Corrected the cause and changed approach 1 to accepting the four pixels around the boundary. The subagent redoes the fix that way.
- **2026-09-30, resolved.** Approach 2 landed as `03f7aa6` and reran green. Not pushed yet.
