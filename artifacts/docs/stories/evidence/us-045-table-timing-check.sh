#!/usr/bin/env bash
# Evidence for US-045. Read-only. Run from the Mac; every command goes through the remote-server context.
# Gap = end of 3_calculate_depth (flood_mapping_full) to end of the next 9c_build_edge_depth_table (routing_adapter).
d() { docker --context remote-server "$@"; }
d exec airflow_new-airflow-postgres-1 psql -U airflow -d airflow -c "
with c as (select end_date calc_end from task_instance where dag_id='flood_mapping_full' and task_id='3_calculate_depth' and state='success' and start_date > '2026-10-08 08:00:00+00'),
d as (select start_date, end_date, duration from task_instance where dag_id='routing_adapter' and task_id='9c_build_edge_depth_table' and state='success' and start_date > '2026-10-08 08:00:00+00'),
g as (select d.duration d9c, extract(epoch from d.end_date - c.calc_end)/60 gap from c join lateral (select * from d where d.start_date >= c.calc_end order by d.start_date limit 1) d on true)
select count(*) runs, round(min(gap)::numeric,2) gap_min, round(avg(gap)::numeric,2) gap_avg, round(max(gap)::numeric,2) gap_max, round(max(d9c)::numeric,1) d9c_max_s from g"
d exec airflow_new-airflow-worker-1 sh -c 'cd /opt/airflow; ls -l edge_depth_tables/latest edge_depth_tables/$(cat edge_depth_tables/latest); python scripts/edge_depth/spot_check.py edge_depth_tables/$(cat edge_depth_tables/latest) | tail -1'
