#!/usr/bin/env bash
# Evidence for US-109. Run from the Mac after the analysis service is built and started, and screenshot the terminal.
# The write probes run inside a transaction that is rolled back, so the databases are left unchanged.
d() { docker --context remote-server "$@"; }
echo "== US-109 server check, $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M') +07"
echo "-- container"
d ps --filter name=analysis --format '{{.Names}}  {{.Status}}  {{.Ports}}'
echo "-- GET /health (newest run with all four outputs in flood_run_output)"
d exec airflow_new-analysis-1 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8020/health').read().decode())"
d exec -i airflow_new-analysis-1 python - <<'PY'
import os, psycopg2
def connect(host, db, user, password):
    c = psycopg2.connect(host=host, dbname=db, user=user, password=password)
    c.autocommit = False
    return c
def attempt(conn, sql, label):
    cur = conn.cursor()
    try:
        cur.execute(sql)
        result = "allowed"
    except psycopg2.errors.InsufficientPrivilege:
        result = "permission denied"
    conn.rollback()
    print(f"{label:62} {result}")
e = os.environ
reader = connect(e["POSTGRES_HOST"], e["POSTGRES_DB"], e["ANALYSIS_READER_USER"], e["ANALYSIS_READER_PASSWORD"])
owner = connect(e["POSTGRES_HOST"], e["POSTGRES_DB"], e["ANALYSIS_OWNER_USER"], e["ANALYSIS_OWNER_PASSWORD"])
ts = connect(e["TIMESCALE_HOST"], e["TIMESCALE_DB"], e["ANALYSIS_TIMESCALE_READER_USER"], e["ANALYSIS_TIMESCALE_READER_PASSWORD"])
print("-- permissions with the service's own credentials")
attempt(reader, "SELECT count(*) FROM flood_run_output", f"{e['ANALYSIS_READER_USER']}: read flood_run_output")
attempt(reader, "DELETE FROM flood_road_values WHERE false", f"{e['ANALYSIS_READER_USER']}: write flood_road_values")
attempt(owner, "CREATE TABLE analysis.us109_probe (x int)", f"{e['ANALYSIS_OWNER_USER']}: create a table in schema analysis")
attempt(owner, "CREATE TABLE public.us109_probe (x int)", f"{e['ANALYSIS_OWNER_USER']}: create a table in schema public")
attempt(ts, "SELECT count(*) FROM depth_history", f"{e['ANALYSIS_TIMESCALE_READER_USER']}: read depth_history")
attempt(ts, "DELETE FROM depth_history WHERE false", f"{e['ANALYSIS_TIMESCALE_READER_USER']}: write depth_history")
PY
echo "-- secrets in the container environment"
d exec airflow_new-analysis-1 sh -c 'printenv | cut -d= -f1 | grep -c -E "THREEDI|TOMORROW|MINIO|ORG_UUID" | sed "s/^/variables named THREEDI, TOMORROW, MINIO, or ORG_UUID: /"; printenv | cut -d= -f1 | grep -E "^(ANALYSIS|POSTGRES|TIMESCALE|HOST|PORT)" | sort | tr "\n" " "; echo'
echo "-- root Dockerfile and requirements.txt against main"
git diff --stat main -- Dockerfile requirements.txt | tail -1 | sed 's/^$/unchanged/'; [ -z "$(git diff main -- Dockerfile requirements.txt)" ] && echo "unchanged"
