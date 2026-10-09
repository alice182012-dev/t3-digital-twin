#!/bin/bash
# Read-only check of US-102 after a storm replay. It changes nothing on the server.
#
# Usage: us-102-replay-check.sh START_UTC [TABLE_DIR] [GAP_FROM_MIN] [GAP_TO_MIN]
#   START_UTC     the replay start that replay.ps1 start printed, which is FLOOD_TEST_RAIN_START, for example 2026-10-09T06:30:00Z
#   TABLE_DIR     the copied edge depth tables on this machine, for the wet-edge ratio (skipped when absent)
#   GAP_FROM_MIN  first event offset to inspect, in minutes (default 360, hour 6)
#   GAP_TO_MIN    last event offset to inspect, in minutes (default 450, hour 7.5)
# The inspected offsets cover the former BL-028 gap, where the forecast dips under 5 mm/h.
# Run it from the repository on a machine with the remote-server docker context.
cd "$(git rev-parse --show-toplevel)" || exit 1
START=${1:?usage: us-102-replay-check.sh START_UTC [TABLE_DIR] [GAP_FROM_MIN] [GAP_TO_MIN]}
TABLE_DIR=${2:-}
FROM=${3:-360}
TO=${4:-450}
DK="docker --context remote-server"
W=airflow_new-airflow-worker-1
P=airflow_new-airflow-postgres-1

echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "Replay start slot: $START. Inspected offsets: $FROM to $TO minutes."
echo
echo "1. the replay settings of the worker on the server"
$DK exec $W sh -c 'printenv | grep -E "^FLOOD_(TEST_RAIN|RAIN_THRESHOLD)" | sort'
echo
SLOTS=$(python3 - "$START" "$FROM" "$TO" <<'PY'
import sys
from datetime import datetime, timedelta, timezone
start = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
for minutes in range(int(sys.argv[2]), int(sys.argv[3]) + 1, 15):
    print((start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S"))
PY
)

echo "2. the runs of the inspected slots: the trigger task state and the hotstart or cold start line of its log"
for slot in $SLOTS; do
  state=$($DK exec $P sh -c "psql -U \"\${POSTGRES_USER:-airflow}\" -d \"\${POSTGRES_DB:-airflow}\" -At -c \"select coalesce(max(ti.state),'no run') from dag_run r join task_instance ti on ti.run_id=r.run_id and ti.dag_id=r.dag_id where r.dag_id='flood_mapping_full' and r.logical_date='${slot}+00' and ti.task_id='1_trigger_simulation'\"")
  line=$($DK exec $W sh -c "grep -h -o -E '\[Hotstart[^]]*\] Saved state [^ ]*|\[Coldstart\] No saved state[^\"]*' /opt/airflow/logs/dag_id=flood_mapping_full/run_id=scheduled__${slot}+00:00/task_id=1_trigger_simulation/attempt=1.log 2>/dev/null | head -1")
  echo "slot ${slot}Z  trigger ${state:-no run}  ${line:-no hotstart line}"
done
echo
echo "3. all runs of the replay by state"
$DK exec $P sh -c "psql -U \"\${POSTGRES_USER:-airflow}\" -d \"\${POSTGRES_DB:-airflow}\" -At -F ' ' -c \"select ti.state, count(*) from dag_run r join task_instance ti on ti.run_id=r.run_id and ti.dag_id=r.dag_id where r.dag_id='flood_mapping_full' and r.logical_date >= '${START}+00' and ti.task_id='1_trigger_simulation' group by ti.state order by 1\"" | sed 's/^/   /'
echo
if [ -n "$TABLE_DIR" ] && [ -d "$TABLE_DIR" ]; then
  # Table names are the slot in +07. The first table is the baseline, so start one slot before the inspected ones.
  read -r FIRST LAST <<EOF
$(python3 - "$START" "$FROM" "$TO" <<'PY'
import sys
from datetime import datetime, timedelta, timezone
start = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
name = lambda minutes: (start + timedelta(minutes=minutes, hours=7)).strftime("%Y%m%dT%H%M%S")
print(name(int(sys.argv[2]) - 15), name(int(sys.argv[3])))
PY
)
EOF
  echo "4. wet edges at the first step of each run against the previous run's forecast, runs $FIRST to $LAST"
  python3 scripts/edge_depth/gap_continuity.py "$TABLE_DIR" --first "$FIRST" --last "$LAST"
else
  echo "4. wet-edge ratio skipped: no TABLE_DIR given or found"
fi
