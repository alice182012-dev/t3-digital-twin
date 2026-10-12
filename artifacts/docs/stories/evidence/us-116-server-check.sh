#!/usr/bin/env bash
# Evidence for US-116. Read-only. Run from the Mac and screenshot the terminal. It shows the server checkout, the
# rebuilt backend, the run registry with its forecast times, the routing_reader grant, and /flood/areas for
# run=latest against the newest and the older run at the times both cover.
d() { docker --context remote-server "$@"; }
echo "== US-116 server check, $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M') +07"
echo "-- server checkout"
ssh -o ConnectTimeout=15 tecotec@100.67.84.55 'cd C:\Users\TECOTEC\airflow_new; git log --oneline -1' 2>&1
echo "-- backend container"
d ps --filter name=floodmap-backend --format '{{.Names}}  {{.Status}}  created {{.CreatedAt}}'
d exec airflow_new-floodmap-backend-1 sh -c 'echo "reads as: $POSTGRES_USER"; grep -c forecast_times /app/backend/flood_areas.py | sed "s/^/lines with forecast_times in flood_areas.py: /"'
echo "-- run registry (flood_road_file)"
d exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -c "select count(*) runs, count(forecast_times) with_forecast_times, min(array_length(forecast_times,1)) min_times, max(array_length(forecast_times,1)) max_times, count(*) filter (where feature_count = 0) dry_runs from flood_road_file"
echo "-- routing_reader and /flood/areas, run=latest against the pinned runs"
d exec -i airflow_new-floodmap-backend-1 python - <<'PY'
import hashlib, json, os, urllib.request
import psycopg2
c = psycopg2.connect(host=os.environ["POSTGRES_HOST"], dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
c.autocommit = True
cur = c.cursor()
cur.execute("select count(*) from flood_road_file")
print(f"routing_reader SELECT on flood_road_file: {cur.fetchone()[0]} rows")
try:
    cur.execute("delete from flood_road_file where false")
    print("routing_reader DELETE: allowed (bad)")
except psycopg2.errors.InsufficientPrivilege:
    print("routing_reader DELETE: permission denied")

def res(**q):
    url = "http://127.0.0.1:8010/flood/areas?" + "&".join(f"{k}={v}" for k, v in q.items())
    feats = json.load(urllib.request.urlopen(url))["features"]
    digest = hashlib.md5(json.dumps(sorted(json.dumps(f["geometry"], sort_keys=True) for f in feats)).encode()).hexdigest()[:6]
    return len(feats), digest

print("time (+07)           vehicle    latest        newest 00:15  older 00:00   latest=newest")
bad = 0
for h, m in [(0, 15), (0, 30), (0, 45), (1, 0), (1, 15), (1, 30)]:
    t = f"2026-10-11T{h:02d}:{m:02d}:00"
    for vt in ("motorbike", "car"):
        a, b, o = (res(valid_time=t, vehicle_type=vt, run=r) for r in ("latest", "2026-10-11T00:15:00", "2026-10-11T00:00:00"))
        bad += a != b
        mark = "  (runs differ)" if b != o else ""
        print(f"{t}  {vt:9}  {str(a):12}  {str(b):12}  {str(o):12}  {a == b}{mark}")
print("mismatches:", bad, "| a time no run covers:", res(valid_time="2026-10-12T09:00:00", vehicle_type="motorbike", run="latest")[0], "features")
PY
