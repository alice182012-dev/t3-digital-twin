"""Airflow assets the core flood DAG publishes, for consumer DAGs to schedule on.

`9b_load_depth_raster` of `flood_mapping_full` emits FLOOD_DEPTH_RASTER when every timestep of a run is in
`flood_depth_raster_tile`. The event's `extra` is `{"run_ts": "<run_ts>"}`, the run name the contract tables key on
(artifacts/docs/concepts/core-output-contract.md, "Readiness"). Airflow puts the DAGs folder on `sys.path`, so a DAG
file imports this module as `core_assets`.

`3b_publish_depth_files` emits FLOOD_DEPTH_FILES once the depth folder of a run is complete and the archive step has
ended. Its `extra` is `{"run_ts": "<run_ts>", "depth_dir": "<folder of the depth_*.tif files>"}`. The files live on the
worker's disk, so a consumer reads them from `depth_dir` and must not delete them: `flood_tiles` owns the age-based
cleanup (core_paths.py).

`9c_build_edge_depth_table` of `routing_adapter` emits EDGE_DEPTH_ROWS once a run's rows are in `edge_depth` and its
registry row is in `edge_depth_run`. Its `extra` is `{"run_ts": "<run_ts>"}`. `flood_history` runs on it and copies the
run into TimescaleDB.
"""
from airflow.sdk import Asset


FLOOD_DEPTH_RASTER = Asset("flood_depth_raster_tile")
FLOOD_DEPTH_FILES = Asset("flood_depth_files")
EDGE_DEPTH_ROWS = Asset("edge_depth")
