#!/bin/bash
# Prints, for the last N runs of flood_mapping_full, each task's duration and the margin of step 1.
# Step 1 becomes "now" at slot + 15 min. The margin is that moment minus the end of 9_build_flood_tiles.
# A negative margin means the tile publishes after step 1 is already now.
# Usage: run_margins.sh [N]   (default 8). Needs the remote-server docker context.
# For the 48-hour replay use N=250. Only runs with state success appear, and a dry-cycle run has empty fields.
# Feed the output to report.py.
N=${1:-8}
P=airflow_new-airflow-postgres-1
docker --context remote-server exec $P sh -c "psql -U \"\${POSTGRES_USER:-airflow}\" -d \"\${POSTGRES_DB:-airflow}\" -At -F ' ' -c \"
with runs as (
  select run_id, logical_date, start_date from dag_run
  where dag_id='flood_mapping_full' and state='success' order by start_date desc limit $N
), t as (
  select r.run_id, r.logical_date,
    max(case when ti.task_id='1_trigger_simulation' then extract(epoch from ti.end_date-ti.start_date) end)/60 trigger,
    max(case when ti.task_id='3_calculate_depth' then extract(epoch from ti.end_date-ti.start_date) end)/60 depth,
    max(case when ti.task_id='9b_load_depth_raster' then extract(epoch from ti.end_date-ti.start_date) end)/60 raster,
    max(case when ti.task_id='9_build_flood_tiles' then extract(epoch from ti.end_date-ti.start_date) end)/60 tiles,
    max(case when ti.task_id='9_build_flood_tiles' then ti.end_date end) tiles_end
  from runs r join task_instance ti on ti.run_id=r.run_id and ti.dag_id='flood_mapping_full'
  group by r.run_id, r.logical_date
)
select to_char(logical_date at time zone 'Asia/Ho_Chi_Minh','MM-DD HH24:MI') slot,
  round(trigger::numeric,1) trigger, round(depth::numeric,1) depth, round(raster::numeric,1) raster, round(tiles::numeric,1) tiles,
  round((extract(epoch from (logical_date + interval '15 minutes') - tiles_end)/60)::numeric,1) margin_min
from t order by logical_date;
\""
