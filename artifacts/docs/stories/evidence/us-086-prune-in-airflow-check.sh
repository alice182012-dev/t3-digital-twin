#!/usr/bin/env bash
# Read-only check for US-086: the prune task ran inside Airflow and the table holds only the last 24 hours. Run from the Mac.
set -u
d() { docker --context remote-server "$@"; }
echo "captured: $(date '+%F %T %z') on $(hostname -s), reading server 100.67.84.55"
echo "prune_flood_road_values task runs in Airflow (state, count): $(d exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -At -F ' ' -c "select state, count(*) from task_instance where dag_id='routing_adapter' and task_id='prune_flood_road_values' group by state" | tr '\n' ';')"
echo "last run log:"
d exec airflow_new-airflow-worker-1 sh -c 'f=$(ls /opt/airflow/logs/dag_id=routing_adapter/run_id=asset_triggered__2026-10-09T17*/task_id=prune_flood_road_values/attempt=1.log | tail -1); grep -E "Deleted [0-9]+ runs" "$f" | sed "s/.*event\":\"//; s/\",\"logger.*//"'
echo "flood_road_file runs left: $(d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select count(*) || ' runs, oldest ' || min(timestamp) || ', newest ' || max(timestamp) from flood_road_file")"
echo "flood_road_values size:    $(d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select pg_size_pretty(pg_total_relation_size('flood_road_values')) || ', ' || count(*) || ' rows' from flood_road_values")"
