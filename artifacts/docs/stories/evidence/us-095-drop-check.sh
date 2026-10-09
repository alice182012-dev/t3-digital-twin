#!/usr/bin/env bash
# Read-only check of the netcdf tables on the server after the drop of US-095. Run from the Mac.
set -u
d() { docker --context remote-server "$@"; }
echo "captured: $(date '+%F %T %z') on $(hostname -s), reading server 100.67.84.55"
echo "git on server: $(ssh tecotec@100.67.84.55 'cd C:\Users\TECOTEC\airflow_new; git log --oneline -1' 2>&1 | tr -d '\r')"
echo "DAG tasks of flood_mapping_full: $(d exec airflow_new-airflow-scheduler-1 airflow tasks list flood_mapping_full 2>/dev/null | grep -vE 'alembic|Warning|^$' | tr '\n' ' ')"
echo "timescaledb flood_metrics tables: $(d exec airflow_new-timescaledb-1 psql -U flood_metrics -d flood_metrics -At -c "select string_agg(relname, ', ' order by relname) from pg_class where relkind='r' and relnamespace='public'::regnamespace")"
echo "timescaledb flood_metrics size:   $(d exec airflow_new-timescaledb-1 psql -U flood_metrics -d flood_metrics -At -c "select pg_size_pretty(pg_database_size('flood_metrics'))")"
echo "timescaledb netcdf jobs:          $(d exec airflow_new-timescaledb-1 psql -U flood_metrics -d flood_metrics -At -c "select count(*) from timescaledb_information.jobs where hypertable_name='netcdf_values'")"
echo "storage-postgres netcdf* tables:  $(d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select count(*) from pg_class where relname like 'netcdf%'")"
echo "minio_custom size:                $(d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -c "select pg_size_pretty(pg_database_size('minio_custom'))")"
