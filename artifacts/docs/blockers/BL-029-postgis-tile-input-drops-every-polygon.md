---
date_open: 2026-10-12
date_closed: 
type: blocker
status: open
severity: P3
subsystem: flood-extent
approaches_tried: 0
approaches_remaining: 2
tags: [blocker, flood-tiles, postgis, us-104, crs]
related: ["[[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]]", "[[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]]", "[[minio-flood-extent-pipeline]]", "[[decision-log|D-027]]", "[[2026-10-12]]"]
last_updated: 2026-10-12
---

# The postgis input of the flood tile build drops every polygon

## Description

With `FLOOD_TILES_INPUT=postgis`, the `flood_tiles` DAG exports each step from `flood_depth_raster_tile` with `raster_export.export_run`. The table holds the raster in EPSG:4326, so the exported `depth_*.tif` is in EPSG:4326.

The tile engine in `scripts/flood_extent/flood_extent.py` expects the source CRS (EPSG:3405, metres). Its `min_area` is 20 m², and `clean_multipolygon` compares it with the polygon area in the layer's own unit. On a degree raster every area is a tiny fraction of 1, so every polygon is smaller than `min_area`, and `clean` writes an empty `cleaned` layer.

GDAL then fails when it closes that layer, and `feature_count(self.cleaned)` reads a dataset that is `None`. Every step of the run fails with this error:

```
AttributeError: 'NoneType' object has no attribute 'GetLayer'
```

The `files` mode is not affected, because task 3 writes its files in EPSG:3405.

## Why this matters

[[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]] cannot compare the two modes as the branch ships them, because the `postgis` mode builds no tiles. A tile build that leaves the worker's disk, which a future 3D view or cost estimate may need, depends on a working `postgis` mode.

The live DAG runs in `files` mode, so no user sees this today. The failure appears only when someone sets `FLOOD_TILES_INPUT=postgis`.

## Approaches tried

None as a fix. The cause was found on 2026-10-12 during the US-104 measurement, on the run `20261010T041500` of the storm test dataset.

## Candidate approaches

| Option | What it does | Cost and risk |
| ------ | ------------ | ------------- |
| A. Warp the export to EPSG:3405 | `raster_export.export_run` warps each file with `gdal.Warp(dstSRS="EPSG:3405", resampleAlg="near")` before the build. | S. Adds about 8 s per run. The US-104 harness measured it. Resampling shifts band areas by up to about 1.5 percent and the tile count by 2 on the first run. |
| B. Make the engine CRS-aware | The engine converts `radius` and `min_area` to the raster's unit, or reprojects once inside `Pipeline`. | M. Touches the engine that the `files` mode also uses. |

A is the smaller change. B is the one that removes the assumption. [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]] found neither worth doing now.

## Decision and explanation

Pending, and not scheduled. [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]] measured on 2026-10-12 that the warp variant is 32 to 35 s slower per run than the `files` mode and fails the 1 percent area check, so [[decision-log|D-027]] keeps `files`. Nothing is blocked while the DAG runs in `files` mode. Fix this only when a host without the worker's disk needs the tile build.

## Related topics

- [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]]
- [[minio-flood-extent-pipeline]]
- [[decision-log|D-027]]

## Status history

- **2026-10-12, open.** Found while measuring US-104. The harness `marie-curie/us-104/bench_tiles.py` reproduces it on the first `postgis` build, and its warped variant builds tiles.
- **2026-10-12, open, P3.** US-104 answered with 5 paired runs and kept `files`, so the blocker no longer holds up a story. The severity went from P2 to P3.
- **2026-10-12, open, P3.** The owner archived [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]], so no story depends on a working `postgis` mode. The blocker stays open and unscheduled until a host without the worker's disk needs the tile build.
