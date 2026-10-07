"""Airflow assets the core flood DAG publishes, for consumer DAGs to schedule on.

`9b_load_depth_raster` of `flood_mapping_full` emits FLOOD_DEPTH_RASTER when every timestep of a run is in
`flood_depth_raster_tile`. The event's `extra` is `{"run_ts": "<run_ts>"}`, the run name the contract tables key on
(artifacts/docs/concepts/core-output-contract.md, "Readiness"). Airflow puts the DAGs folder on `sys.path`, so a DAG
file imports this module as `core_assets`.
"""
from airflow.sdk import Asset


FLOOD_DEPTH_RASTER = Asset("flood_depth_raster_tile")
