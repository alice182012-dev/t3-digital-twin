# Timing report of task 9c (the edge depth table task) over the runs of flood_mapping_full, for US-045.
# 9c runs in the routing_adapter run that the run's 9b asset event triggered (US-073), and the query joins the two
# through Airflow's asset_event and dagrun_asset_event tables.
# Read-only. Run it in PowerShell on the server, in the repo folder, after some runs have finished:
#   .\scripts\edge_depth\table_timing.ps1            # the newest 250 successful DAG runs
#   .\scripts\edge_depth\table_timing.ps1 -Runs 20
# It reads the task times from the Airflow database (airflow-postgres) and the XCom `edge_depth_table`, and pipes them
# through table_timing.py in the worker. The exit code is 0 only when every run ended within 5 minutes of
# 3_calculate_depth, none held up the tile task, and no table task failed.
param([int]$Runs = 250, [double]$LimitMinutes = 5)

$postgres = "airflow_new-airflow-postgres-1"
$worker = "airflow_new-airflow-worker-1"

$sql = @"
with runs as (
  select run_id, logical_date from dag_run
  where dag_id = 'flood_mapping_full' and state = 'success'
  order by logical_date desc limit $Runs
), core as (
  select r.run_id, r.logical_date,
    max(case when ti.task_id = '3_calculate_depth' and ti.state = 'success' then ti.end_date end) calc_end,
    max(case when ti.task_id = '9_build_flood_tiles' and ti.state = 'success' then ti.start_date end) tiles_start,
    max(case when ti.task_id = '9_build_flood_tiles' and ti.state = 'success' then ti.end_date end) tiles_end
  from runs r join task_instance ti on ti.run_id = r.run_id and ti.dag_id = 'flood_mapping_full'
  group by r.run_id, r.logical_date
), routing as (
  -- A routing_adapter run builds the newest run_ts among the 9b events that triggered it, so only that event's
  -- core run is matched to it.
  select distinct on (dr.id) ae.source_run_id core_run_id, dr.run_id routing_run_id
  from dag_run dr
  join dagrun_asset_event dae on dae.dag_run_id = dr.id
  join asset_event ae on ae.id = dae.event_id
  where dr.dag_id = 'routing_adapter'
    and ae.source_dag_id = 'flood_mapping_full' and ae.source_task_id = '9b_load_depth_raster'
  order by dr.id, ae.extra->>'run_ts' desc
), t as (
  select c.*, ti.run_id routing_run_id, ti.state c_state, ti.start_date c_start, ti.end_date c_end
  from core c
  left join routing g on g.core_run_id = c.run_id
  left join task_instance ti on ti.dag_id = 'routing_adapter' and ti.run_id = g.routing_run_id
    and ti.task_id = '9c_build_edge_depth_table'
)
select t.run_id,
  to_char(t.logical_date at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
  coalesce(to_char(t.calc_end at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), ''),
  coalesce(to_char(t.tiles_start at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), ''),
  coalesce(to_char(t.tiles_end at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), ''),
  coalesce(t.c_state, ''),
  coalesce(to_char(t.c_start at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), ''),
  coalesce(to_char(t.c_end at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'), ''),
  coalesce((select replace(x.value::text, chr(10), ' ') from xcom x
            where x.dag_id = 'routing_adapter' and x.run_id = t.routing_run_id
              and x.task_id = '9c_build_edge_depth_table' and x.key = 'edge_depth_table' limit 1), '')
from t order by t.logical_date;
"@

$sql | docker exec -i $postgres psql -U airflow -d airflow -At -F "~" |
    docker exec -i $worker python /opt/airflow/scripts/edge_depth/table_timing.py --limit-minutes $LimitMinutes
exit $LASTEXITCODE
