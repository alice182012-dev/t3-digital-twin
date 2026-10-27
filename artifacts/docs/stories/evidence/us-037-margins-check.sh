cd /Users/maianhtran/Documents/3Di/Case-study-sim-center/airflow_clone/t3-digital-twin
echo "Docker host: $(docker --context remote-server info --format '{{.Name}} ({{.OperatingSystem}})') at 100.67.84.55"
echo "Step 1 margin = due time (slot + 15 min) minus the publish time of the first tile line of 9_build_flood_tiles. Times are +07."
for slot in 2026-10-01T17:45:00 2026-10-01T18:00:00 2026-10-01T18:15:00 2026-10-01T18:30:00; do
  marie-curie/us-037/step1_margins.sh $slot
  docker --context remote-server exec airflow_new-airflow-worker-1 sh -c "grep -h -E 'Chain check' /opt/airflow/logs/dag_id=flood_mapping_full/run_id=scheduled__${slot}+00:00/task_id=1_trigger_simulation/attempt=*.log" | python3 -c "
import sys, json
for l in sys.stdin: print('    ' + json.loads(l)['event'][:130])"
done
