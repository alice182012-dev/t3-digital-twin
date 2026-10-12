#!/usr/bin/env bash
# Evidence for US-117. Read-only. Run from the Mac and screenshot the terminal.
d() { docker --context remote-server "$@"; }
echo "== US-117 server check, $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M') +07"
echo "-- server checkout"
ssh -o ConnectTimeout=15 tecotec@100.67.84.55 'cd C:\Users\TECOTEC\airflow_new; git log --oneline -1' 2>&1
echo "-- the live graph has the way id"
d exec airflow_new-graphhopper-1 curl -s http://localhost:8989/info | python3 -c 'import json,sys; i=json.load(sys.stdin); print("profiles:", ",".join(p["name"] for p in i["profiles"]), "| osm_way_id in encoded_values:", "osm_way_id" in i["encoded_values"])'
echo "-- the export of the graph"
d exec airflow_new-airflow-worker-1 sh -c 'cat /opt/airflow/data/mapping/graph_export/graph.json; head -n 3 /opt/airflow/data/mapping/graph_export/edges.csv | cut -c1-90'
echo "-- graph_edge holds one key per edge"
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -c "select count(*) as edges, count(edge_key) as keys, count(distinct edge_key) as distinct_keys, count(distinct split_part(edge_key, ':', 1)) as ways from graph_edge"
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -c "select edge_id, edge_key from graph_edge order by edge_id limit 3"
echo "-- the edge depth tables still match the graph"
d exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/edge_depth/check_tables.py 2>&1 | tail -1
