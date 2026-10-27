#!/usr/bin/env bash
# Read-only check for US-070: duration of task 9c over the runs of the second replay. Run from the Mac.
set -u
d() { docker --context remote-server exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -At -F ' ' -c "$1"; }
echo "captured: $(date '+%F %T %z') on $(hostname -s), reading server 100.67.84.55"
echo "9c runs by state (all time): $(d "select state, count(*) from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' group by state" | tr '\n' ';')"
echo "9c in the second replay (success only), seconds min / mean / max / runs: $(d "select round(min(duration)), round(avg(duration)), round(max(duration)), count(*) from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' and state='success' and start_date >= '2026-10-09 05:50+00'")"
echo "runs past the 120 s cancel: $(d "select count(*) from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' and duration > 120")"
echo "chain 1 (first 27 runs), seconds: $(d "select round(duration) from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' and state='success' and start_date >= '2026-10-09 05:50+00' order by start_date limit 27" | tr '\n' ' ')"
echo "chain 2 (last 18 runs), seconds: $(d "select round(duration) from (select duration, start_date from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' and state='success' and start_date >= '2026-10-09 05:50+00' order by start_date desc limit 18) x order by start_date" | tr '\n' ' ')"
