#!/usr/bin/env bash
# Evidence for US-087. Run from the repository root on the Mac. It runs the test from the repository root with
# no PYTHONPATH, first with no DSN (it must skip, not raise), then on the server's PostGIS in a throwaway database.
d() { docker --context remote-server "$@"; }
W=airflow_new-airflow-worker-1
echo "--- no DSN, no PYTHONPATH, from the repository root"
python3 -I floodmap/graphhopper-flood-road/backend/test_flood_areas.py; echo "exit $?"
echo "--- real PostGIS (database floodtest_us087, dropped afterwards)"
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d postgres -c "CREATE DATABASE floodtest_us087"
d exec -u root $W sh -c 'rm -rf /tmp/us087; mkdir -p /tmp/us087 && chmod 777 /tmp/us087; mkdir -p /tmp/us087/floodmap/graphhopper-flood-road /tmp/us087/scripts'
d cp floodmap/graphhopper-flood-road/backend $W:/tmp/us087/floodmap/graphhopper-flood-road/backend >/dev/null
d cp floodmap/graphhopper-flood-road/scripts $W:/tmp/us087/floodmap/graphhopper-flood-road/scripts >/dev/null
d cp scripts/database $W:/tmp/us087/scripts/database >/dev/null
d exec $W sh -c 'cd /tmp/us087 && FLOOD_TEST_DSN="postgresql://minio_custom:$POSTGRES_PASSWORD@storage-postgres:5432/floodtest_us087" python3 floodmap/graphhopper-flood-road/backend/test_flood_areas.py; echo "exit $?"'
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d postgres -c "DROP DATABASE floodtest_us087"
d exec -u root $W rm -rf /tmp/us087
