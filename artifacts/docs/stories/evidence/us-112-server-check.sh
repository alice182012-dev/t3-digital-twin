#!/usr/bin/env bash
# Evidence for US-112. Read-only. Run from the Mac and screenshot the terminal.
d() { docker --context remote-server "$@"; }
echo "== US-112 server check, $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M') +07"
echo "-- server checkout"
ssh -o ConnectTimeout=15 tecotec@100.67.84.55 'cd C:\Users\TECOTEC\airflow_new; git log --oneline -1; Select-String -Path .env -Pattern "^EDGE_TABLE_KEEP_RUNS=" | ForEach-Object { ".env: " + $_.Line }' 2>&1
echo "-- worker (task 9c runs here)"
d exec airflow_new-airflow-worker-1 sh -c 'echo "EDGE_TABLE_KEEP_RUNS in the worker: $EDGE_TABLE_KEEP_RUNS"; echo "files in the volume: $(ls /opt/airflow/edge_depth_tables | grep -c "\.bin$")"; echo "latest names: $(cat /opt/airflow/edge_depth_tables/latest)"; ls /opt/airflow/edge_depth_tables | grep "\.bin$" | tr "\n" " "; echo'
echo "-- the engine and the backend read the same volume"
d exec airflow_new-graphhopper-1 sh -c 'echo "files seen by graphhopper: $(ls /tables | grep -c "\.bin$"), latest: $(cat /tables/latest)"'
d exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/edge_depth/check_tables.py 2>&1 | tail -1
echo "-- the two pages state the same count"
grep -n "EDGE_TABLE_KEEP_RUNS\|newest 8 tables" artifacts/docs/concepts/core-output-contract.md artifacts/docs/concepts/edge-depth-table-format.md | sed "s/^artifacts\/docs\/concepts\///" | cut -c1-140
echo "-- the 58 storm-replay edge files are kept in the test dataset"
d exec airflow_new-airflow-worker-1 sh -c 'echo "files in snapshot/edge_depth: $(ls /opt/airflow/data/testdata/storm-2026-10-10/snapshot/edge_depth | wc -l)"'
