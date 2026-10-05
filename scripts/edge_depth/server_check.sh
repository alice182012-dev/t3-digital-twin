#!/usr/bin/env bash
# Builds the edge depth table of one retained run on the server, inside the Airflow worker, and checks it (US-041).
#
# Run from the Mac, in the repo root, after the export is in place (java/time-aware-routing/export-edges.sh with
# EXPORT_DEST) and the server has pulled this branch (./scripts and ./dags are mounted into the Airflow containers):
#   scripts/edge_depth/server_check.sh                  # the newest run in flood_depth_raster_tile
#   RUN_TS=20261005T020000 scripts/edge_depth/server_check.sh
#
# The DAG can stay paused. This runs the same build_edge_depth.py that task 9c runs.
set -u

CONTEXT=${CONTEXT:-remote-server}
WORKER=${WORKER:-airflow_new-airflow-worker-1}
POSTGRES=${POSTGRES:-airflow_new-storage-postgres-1}
RUN_TS=${RUN_TS:-}
COUNT=${COUNT:-20}
EXPORT_DIR=${EXPORT_DIR:-/opt/airflow/data/mapping/graph_export}
TABLE_DIR=${TABLE_DIR:-/opt/airflow/data/mapping/edge_depth}

d() { docker --context "$CONTEXT" "$@"; }

echo "== 1. Pick the run"
echo "retained runs, newest first:"
d exec "$POSTGRES" psql -U minio_custom -d minio_custom -At \
    -c "select run_ts, count(distinct valid_time_utc) as steps from flood_depth_raster_tile group by run_ts order by run_ts desc limit 4"
if [ -z "$RUN_TS" ]; then
    RUN_TS=$(d exec "$POSTGRES" psql -U minio_custom -d minio_custom -At \
        -c "select max(run_ts) from flood_depth_raster_tile")
fi
[ -n "$RUN_TS" ] || { echo "No run in flood_depth_raster_tile."; exit 1; }
echo "using run $RUN_TS"

echo "== 2. The export folder"
d exec "$WORKER" sh -c "ls -l $EXPORT_DIR && cat $EXPORT_DIR/graph.json" || {
    echo "No export in $EXPORT_DIR. Run java/time-aware-routing/export-edges.sh with EXPORT_DEST first."
    exit 1
}

echo "== 3. Create the tables (the DAG does this in task 0b)"
d exec "$WORKER" python /opt/airflow/scripts/database/create_graph_edge_table.py || exit 1

echo "== 4. Build the table"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/build_edge_depth.py "$RUN_TS" \
    --export-dir "$EXPORT_DIR" --out-dir "$TABLE_DIR" || { echo "BUILD FAILED"; exit 1; }
d exec "$WORKER" ls -l "$TABLE_DIR"

echo "== 5. Spot check $COUNT edges against a direct ST_Value reading"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/spot_check.py "$TABLE_DIR/$RUN_TS.bin" --count "$COUNT"
