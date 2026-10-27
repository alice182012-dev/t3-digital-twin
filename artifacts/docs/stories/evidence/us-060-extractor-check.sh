RUN=20260930T020000
RUN_DB='2026-09-30 02:00:00'
W=airflow_new-airflow-worker-1
P=airflow_new-storage-postgres-1
q() { docker --context remote-server exec $P psql -U minio_custom -d minio_custom -c "$1"; }
echo "Docker host: $(docker --context remote-server info --format '{{.Name}} ({{.OperatingSystem}})') at 100.67.84.55"
echo "1. extract_run.py $RUN, run inside $W"
docker --context remote-server exec $W python /opt/airflow/scripts/flood_metrics/extract_run.py $RUN
echo "2. segment count against the run's distinct geom_4326 values in flood_road_values"
q "select (select count(distinct segment_key) from flood_segment_metrics where run_ts='$RUN') as stored_segments,
 (select count(distinct geom_4326) from flood_road_values where timestamp='$RUN_DB') as run_distinct_geom,
 (select count(*) from flood_segment_metrics where run_ts='$RUN') as rows_stored,
 (select count(distinct vehicle_type) from flood_segment_metrics where run_ts='$RUN') as vehicle_types;"
echo "3. peak_depth_m against the largest depth in flood_road_values, three segments chosen by hand"
q "with src as (select md5(ST_AsEWKB(geom_4326)) k, max(road_name) road, max(depth) mx, count(*) steps from flood_road_values where timestamp='$RUN_DB' group by 1),
 pick as (
  (select 'deepest' as why, * from src order by mx desc limit 1)
  union all (select 'near 0.20 m (motorbike limit)', * from src order by abs(mx-0.2) limit 1)
  union all (select 'shallowest', * from src order by mx asc limit 1))
 select p.why, p.road, left(p.k,8) as key, p.steps, round(p.mx::numeric,6) as max_depth_in_source, round(m.peak_depth_m::numeric,6) as stored_peak_depth_m, (p.mx = m.peak_depth_m) as equal
 from pick p join flood_segment_metrics m on m.segment_key=p.k and m.run_ts='$RUN' and m.vehicle_type='motorbike';"
echo "4. all segments, not only three"
q "with src as (select md5(ST_AsEWKB(geom_4326)) k, max(depth) mx from flood_road_values where timestamp='$RUN_DB' group by 1),
 m as (select segment_key k, max(peak_depth_m) pk from flood_segment_metrics where run_ts='$RUN' group by 1)
 select count(*) segments, count(*) filter (where m.pk is not distinct from src.mx) equal, count(*) filter (where m.pk is distinct from src.mx) differ from src join m using(k);"
