# Timing report of task 9c (the edge depth table task) over the runs of flood_mapping_full, for US-045.
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
), t as (
  select r.run_id, r.logical_date,
    max(case when ti.task_id = '3_calculate_depth' and ti.state = 'success' then ti.end_date end) calc_end,
    max(case when ti.task_id = '9_build_flood_tiles' and ti.state = 'success' then ti.start_date end) tiles_start,
    max(case when ti.task_id = '9_build_flood_tiles' and ti.state = 'success' then ti.end_date end) tiles_end,
    max(case when ti.task_id = '9c_build_edge_depth_table' then ti.state end) c_state,
    max(case when ti.task_id = '9c_build_edge_depth_table' then ti.start_date end) c_start,
    max(case when ti.task_id = '9c_build_edge_depth_table' then ti.end_date end) c_end
  from runs r join task_instance ti on ti.run_id = r.run_id and ti.dag_id = 'flood_mapping_full'
  group by r.run_id, r.logical_date
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
            where x.dag_id = 'flood_mapping_full' and x.run_id = t.run_id
              and x.task_id = '9c_build_edge_depth_table' and x.key = 'edge_depth_table' limit 1), '')
from t order by t.logical_date;
"@

$sql | docker exec -i $postgres psql -U airflow -d airflow -At -F "~" |
    docker exec -i $worker python /opt/airflow/scripts/edge_depth/table_timing.py --limit-minutes $LimitMinutes
exit $LASTEXITCODE
