cd "$(git rev-parse --show-toplevel)" || exit 1
DK="docker --context remote-server"
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. the replay settings of the worker on the server"
$DK exec airflow_new-airflow-worker-1 sh -c 'printenv | grep -E "^FLOOD_(TEST_RAIN|RAIN_THRESHOLD)" | sort'
echo
echo "2. the runs the preview expects at the server's gate of 0.01 mm/h"
python3 scripts/rain_replay.py preview scripts/rain_events/hanoi_20251005_48h.csv 2026-10-02T09:00:00Z 0.01
echo
echo "3. what the rain gate read in the first slot (offset 0) and in the peak slot (offset 1470 minutes)"
for slot in 2026-10-02T09:00:00 2026-10-03T09:30:00; do
  echo "slot ${slot}Z:"
  $DK exec airflow_new-airflow-worker-1 sh -c "grep -h -o -E 'Replaying [^\"]*|Rain gate: max=[0-9.]* mm/h' /opt/airflow/logs/dag_id=flood_mapping_full/run_id=scheduled__${slot}+00:00/task_id=0_check_forecast_rain/attempt=1.log 2>/dev/null || echo no log for this slot yet" | sed 's/^/   /'
done
echo
echo "4. runs of the window by state (slots 2026-10-02 16:00 to 2026-10-04 15:45 +07)"
$DK exec airflow_new-airflow-postgres-1 sh -c "psql -U \"\${POSTGRES_USER:-airflow}\" -d \"\${POSTGRES_DB:-airflow}\" -At -F ' ' -c \"select state, count(*) from dag_run where dag_id='flood_mapping_full' and logical_date >= '2026-10-02 09:00:00+00' and logical_date <= '2026-10-04 08:45:00+00' group by state order by state\"" | sed 's/^/   /'
