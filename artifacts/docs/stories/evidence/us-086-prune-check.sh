#!/usr/bin/env bash
# Evidence for US-086. Read-only. Shows the log of the first prune (run by hand in the worker on 2026-10-09,
# before it: 413 runs, 14,836,828 rows, 7,398 MB) and the table after it. Run from the Mac.
d() { docker --context remote-server "$@"; }
d exec airflow_new-airflow-worker-1 cat /tmp/prune-us086.log
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -c "select (select count(*) from flood_road_values) rows_left, (select count(distinct timestamp) from flood_road_values) runs_left, (select min(timestamp) from flood_road_values) oldest_run, (select max(timestamp) from flood_road_values) newest_run, (select count(*) from flood_road_file) file_rows"
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -c "select indexname from pg_indexes where indexname='idx_flood_values_file_id'"
