#!/usr/bin/env bash
# Builds the edge depth table of one retained run on the server, inside the Airflow worker, publishes it, and checks
# it (US-041 and US-042).
#
# Run from the Mac, in the repo root, after the export is in place (java/time-aware-routing/export-edges.sh with
# EXPORT_DEST) and the server has pulled this branch (./scripts and ./dags are mounted into the Airflow containers):
#   scripts/edge_depth/server_check.sh                  # the newest run in flood_depth_raster_tile
#   RUN_TS=20261005T020000 scripts/edge_depth/server_check.sh
#
# The worker must mount the volume edge-depth-tables first (US-042): pull this branch on the server, then recreate
# the worker over SSH with `docker compose up -d --no-deps airflow-worker` in the repo folder.
#
# The DAG can stay paused. This runs the same build_edge_depth.py and publish_edge_depth.py that task 9c runs.
set -u

CONTEXT=${CONTEXT:-remote-server}
WORKER=${WORKER:-airflow_new-airflow-worker-1}
POSTGRES=${POSTGRES:-airflow_new-storage-postgres-1}
RUN_TS=${RUN_TS:-}
COUNT=${COUNT:-20}
EXPORT_DIR=${EXPORT_DIR:-/opt/airflow/data/mapping/graph_export}
TABLE_DIR=${TABLE_DIR:-/opt/airflow/edge_depth_tables}

d() { docker --context "$CONTEXT" "$@"; }

echo "== 0. The table folder (the volume edge-depth-tables) must exist and be writable by the Airflow user"
d exec "$WORKER" test -d "$TABLE_DIR" || {
    echo "$TABLE_DIR is not in the worker. Pull this branch on the server and recreate the worker (see the top of this script)."
    exit 1
}
if ! d exec "$WORKER" test -w "$TABLE_DIR"; then
    echo "Not writable by the Airflow user yet. Making it so (a new volume belongs to root):"
    airflow_uid=$(d exec "$WORKER" id -u | tr -d '\r')
    d exec -u 0 "$WORKER" chown -R "$airflow_uid:0" "$TABLE_DIR" || exit 1
fi
d exec "$WORKER" ls -ld "$TABLE_DIR"

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

echo "== 4. Build the table and publish it"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/build_edge_depth.py "$RUN_TS" \
    --export-dir "$EXPORT_DIR" --out-dir "$TABLE_DIR" --publish || { echo "BUILD FAILED"; exit 1; }
d exec "$WORKER" sh -c "ls -l $TABLE_DIR && echo '--- latest:' && cat $TABLE_DIR/latest"

echo "== 5. Spot check $COUNT edges against a direct ST_Value reading"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/spot_check.py "$TABLE_DIR/$RUN_TS.bin" --count "$COUNT"

echo "== 6. Freshness: do the export, graph_edge, and the latest table agree on one graph hash? (US-044)"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/check_tables.py --table-dir "$TABLE_DIR" --export-dir "$EXPORT_DIR" || exit 1
echo "-- the same check against a graph hash that is not the live one (it must say STALE and name both hashes):"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/check_tables.py --table-dir "$TABLE_DIR" --export-dir "$EXPORT_DIR" \
    --no-db --graph-hash 0000000000000000000000000000000000000000000000000000000000000000
[ $? -eq 1 ] || { echo "The stale case did not exit with 1."; exit 1; }

echo "== 7. Atomic publish and retention on this volume: a reader in its own process polls while 41 tables publish"
d exec "$WORKER" python /opt/airflow/scripts/edge_depth/publish_check.py --table-dir "$TABLE_DIR" || exit 1
d exec "$WORKER" sh -c "ls -la $TABLE_DIR"
