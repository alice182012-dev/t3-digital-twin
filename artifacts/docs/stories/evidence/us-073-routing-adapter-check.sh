#!/usr/bin/env bash
# Evidence for US-073. Read-only. Run from the repo root on the Mac.
d() { docker --context remote-server "$@"; }
d exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -c "select dag_id, count(*) filter (where state='success') success, count(*) filter (where state='failed') failed from dag_run where dag_id in ('flood_mapping_full','routing_adapter') and start_date > '2026-10-08 08:00:00+00' group by 1 order by 1"
d exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -c "select count(*) simulating_core_runs, (select count(*) from dag_run where dag_id='routing_adapter' and start_date > '2026-10-08 08:00:00+00') routing_adapter_runs from task_instance where dag_id='flood_mapping_full' and task_id='9b_load_depth_raster' and state='success' and start_date > '2026-10-08 08:00:00+00'"
(cd test && python3 -m pytest test_routing_adapter_dag.py -q -k "holds_none or runs_on_the_asset or emits_the_asset" 2>&1 | tail -2)
