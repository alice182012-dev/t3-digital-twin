# Project file reorganization

Cleanup of dead and duplicate paths in the repo root, decided with the user
2026-09-23. Scope is intentionally narrow: only items confirmed dead or
duplicated are touched. Airflow-native dirs (`dags/`, `scripts/`, `config/`,
`plugins/`, `data/mapping/*`) and everything bind-mounted by `compose.yml`
stay in place, since moving them means editing two mount lists and every
hardcoded path in the DAGs and scripts for no functional gain.

## Decisions

1. **`docker-compose.yaml` (root): delete.** Superseded by `compose.yml`,
   which is the only compose file the READMEs and this repo's own setup
   instructions reference. `docker-compose.yaml` predates the minio and
   floodmap services and doesn't have the GraphHopper `-o` graph-cache fix
   from commit `9ff0ff9`, so keeping it around risks someone running the
   stale stack by mistake.
2. **`data/output_depths/` and `data/output_geojsons/` (top-level):
   delete.** Orphaned duplicates of `data/mapping/output_depths/` and
   `data/mapping/output_geojsons/`, which are the ones the active pipeline
   writes to (`LOCAL_GEOJSON_DIR` in `compose.yml` points at
   `data/mapping/output_road_geojson`, in the same tree). `data/` is
   gitignored, so this is a local-disk-only cleanup with no git history
   impact.
3. **`floodmap/valhalla-flood-road-test/`: delete.** Explicitly marked
   retired in `compose.yml`'s comments (superseded by the GraphHopper
   backend); still recoverable from git history if ever needed.
4. **`einstein/`: left as-is.** Confirmed as an intentional experimental
   research folder, not dead weight.
5. **`state/`: left as-is.** Referenced by hardcoded paths in
   `flood_mapping_dag.py`, `flood_forecast_state_test_dag.py`,
   `calculate_depth_manual_test_dag.py`, and `test_dag.py`. Moving it means
   editing DAG code; out of scope for a path-cleanup pass.

## Verification

- `git status` clean of the deleted paths (both are gitignored or
  untracked-by-mount, so no git changes expected beyond
  `docker-compose.yaml`'s removal).
- `compose.yml` still builds and boots after the purge-and-recreate, since
  nothing it references was touched.
