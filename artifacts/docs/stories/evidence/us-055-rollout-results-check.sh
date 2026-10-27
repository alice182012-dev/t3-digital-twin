#!/usr/bin/env bash
# Evidence for US-055. Read-only. Reads the result files that rollout.ps1 wrote on 2026-10-07 11:23Z
# and runs the offline checks of routing_proof.py on them. No request reaches the backend.
d() { docker --context remote-server exec airflow_new-airflow-worker-1 "$@"; }
T=/opt/airflow/scripts/routing_proof/routing_proof.py; O=/opt/airflow/data/routing_proof
d python $T compare $O/pairs-off.json $O/pairs-on.json
d python $T crossings --a $O/pairs-off.json --b $O/pairs-on.json
d python -c "import json;[print(f\"{k:18} p50 {v['p50_ms']:6} ms  p95 {v['p95_ms']:6} ms  status {v['statuses']}  td {v['td_statuses']}\") for k,v in json.load(open('$O/latency-on.json')).items()]"
