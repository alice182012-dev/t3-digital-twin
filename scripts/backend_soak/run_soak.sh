#!/bin/sh
# The 48-hour soak verdict for US-034. Usage: run_soak.sh [SINCE]
# SINCE is the soak start. The default is 2026-10-02 00:45 +07, the first run after the US-037 cold start.
# Every command only reads. It runs against the remote Docker host, as .claude/CLAUDE.md requires.
SINCE=${1:-2026-10-02T00:45:00+07:00}
HERE=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
D="docker --context remote-server"

echo "Soak since $SINCE, checked $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. container state (a restart or an OOM kill inside the window ends the soak)"
for c in graphhopper-1 floodmap-backend-1 flood-routing-frontend-1; do
	$D inspect -f '{{.Name}} started={{.State.StartedAt}} restarts={{.RestartCount}} oomkilled={{.State.OOMKilled}} status={{.State.Status}}' "airflow_new-$c"
done
echo
echo "2. requests by status and error lines since the start"
# GraphHopper's log has lines of up to 450 KB, so a PowerShell filter on the host cuts them before they cross the network.
sed "s/SINCE_PLACEHOLDER/$SINCE/" "$HERE/gh_log_filter.ps1" |
	ssh -o ConnectTimeout=30 tecotec@100.67.84.55 powershell -NoProfile -NonInteractive -Command - >"$TMP/graphhopper-1.log" 2>&1
for c in floodmap-backend-1 flood-routing-frontend-1; do
	$D logs --timestamps --since "$SINCE" "airflow_new-$c" >"$TMP/$c.log" 2>&1
done
python3 "$HERE/soak_checks.py" logs "$TMP"/graphhopper-1.log "$TMP"/floodmap-backend-1.log "$TMP"/flood-routing-frontend-1.log
LOGS=$?
echo
echo "3. known answers: POST /route against the vehicle depth limits, newest run"
$D exec -i airflow_new-floodmap-backend-1 python - roads --per-bucket 6 <"$HERE/soak_checks.py"
ROADS=$?
echo
echo "logs exit $LOGS, roads exit $ROADS (0 means no 5xx, no error line, and no failed check)"
[ "$LOGS" -eq 0 ] && [ "$ROADS" -eq 0 ]
