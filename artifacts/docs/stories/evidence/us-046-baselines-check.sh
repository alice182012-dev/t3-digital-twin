cd "$(git rev-parse --show-toplevel)" || exit 1
D="docker --context remote-server"
echo "Docker host: $(ssh -o ConnectTimeout=30 tecotec@100.67.84.55 hostname | tr -d "\r") (context remote-server), run from $(hostname)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. graph of hanoi-model-area.osm.pbf (GraphHopper startup line, container airflow_new-graphhopper-1)"
$D logs --since 2026-09-24T08:38:00Z --until 2026-09-24T08:42:00Z airflow_new-graphhopper-1 2>&1 | grep -oE "edges: [0-9,]+\([0-9A-Z]+\), nodes: [0-9,]+\([0-9A-Z]+\)" | head -1
echo
echo "2. pinned image and the source revision it was built from"
$D inspect -f 'running image: {{.Config.Image}}' airflow_new-graphhopper-1
echo "source: GraphHopper commit d7dc1b069d2d091c7cfdc007d99d1765c82e618d (com/graphhopper/gitinfo in the jar, read 2026-10-01)"
echo
echo "3. step length and count of one real run (run_ts 20261002T023000, flood_depth_raster_tile)"
$D exec airflow_new-storage-postgres-1 psql -U minio_custom -d minio_custom -At -F ' | ' -c "select count(distinct valid_time_utc) || ' steps, ' || min(valid_time_utc) || ' to ' || max(valid_time_utc) || ' UTC, ' || round((extract(epoch from (max(valid_time_utc) - min(valid_time_utc))) / 60 / (count(distinct valid_time_utc) - 1))::numeric) || ' minutes apart' from flood_depth_raster_tile where run_ts = '20261002T023000'"
echo
echo "4. POST /route latency, ms, p50 / p95 of 30 requests per cell (scripts/backend_soak/soak_checks.py latency)"
echo "   run inside airflow_new-floodmap-backend-1, 2026-10-02 02:39 to 02:49 +07, 12 CPUs, load average 9.7 before and 10.4 after"
echo "   flood run 20261002T023000, valid time 2026-10-02T02:30:00+07:00. Raw JSON: evidence/us-046-latency-raw.json"
python3 scripts/backend_soak/soak_checks.py latency-table artifacts/docs/user-stories/evidence/us-046-latency-raw.json
