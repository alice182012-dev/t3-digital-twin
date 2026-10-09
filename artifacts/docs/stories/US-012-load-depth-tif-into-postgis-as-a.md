---
date_drafted: 2026-09-23
type: user-story
us_id: "US-012"
story_label: "2"
epic: "[[EP-03-point-depth-lookup-backend]]"
status: Done
priority: P0
estimate: M
sprint: 1
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
---

# US-012 Load `depth.tif` into PostGIS as a raster

As the point-depth lookup endpoint, I want each timestep's `depth.tif` available as a PostGIS
raster, so I can answer an arbitrary-point depth query without reading the file from disk per
request.
Given a completed run and the `postgis_raster` extension enabled on `storage-postgres`, when the
raster-load step runs for that run's `depth.tif`, then querying the raster table for that
`valid_time` returns a non-null raster whose extent matches the source file.
`scripts/flood_extent/raster_load.py` reprojects each `depth_*.tif` from EPSG:3405 to EPSG:4326
with `gdal.Warp`, then loads it into `flood_depth_raster` (`run_ts`, `valid_time_utc`, `rast`)
with `ST_FromGDALRaster`. `scripts/database/create_flood_depth_raster_tables.py` creates the
table, and `dags/flood_mapping_dag.py`'s `9b_load_depth_raster` task runs beside
`9_build_flood_tiles`. The loader sets `postgis.gdal_enabled_drivers = 'GTiff'` per session,
because PostGIS disables every GDAL driver by default. `ST_Value` at one spot-checked point
matched the source pixel of a real 9901x5656 `depth.tif` to float32 precision. Shipped in commit
`118e04a`.
Priority: P0. Status: Done. Estimate: M. Sprint: 1. Dependencies: None.
Evidence: ![[depth-raster-postgis-load.png|420]]
Details:
1. What: each timestep's `depth.tif` becomes a row in `flood_depth_raster`.
2. How: `raster_load.py` reprojects EPSG:3405 to EPSG:4326 and loads it with `ST_FromGDALRaster`, in DAG task `9b_load_depth_raster`.
3. Why: a point lookup needs the exact pixel.
4. Effect: unblocks `GET /flood/points`. On the server, the row for run `20260924T153638` matches the source file's size and corner. The DAG task has not run there yet.
