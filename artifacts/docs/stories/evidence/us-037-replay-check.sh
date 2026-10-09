# The end-of-test check of US-037. Set UNTIL to judge a window that is still running, for example UNTIL="10-03 09:00".
cd "$(git rev-parse --show-toplevel)" || exit 1
UNTIL=${UNTIL:-10-04 15:45}
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. every run of the replay window 2026-10-02 16:00 to $UNTIL +07, read from the Airflow database on the server"
ROWS=$(sh scripts/pipeline_margins/run_margins.sh 250)
echo "$ROWS" | python3 scripts/pipeline_margins/report.py --event scripts/rain_events/hanoi_20251005_48h.csv --start 2026-10-02T09:00:00Z --threshold 0.01 --since "10-02 16:00" --until "$UNTIL" | cut -c1-170
echo "exit code: ${PIPESTATUS[1]}"
echo
echo "2. the same rows by 6-hour block"
echo "$ROWS" | awk -v until="$UNTIL" '
function key(d, t) { return d " " t }
NF==7 && key($1,$2) >= "10-02 16:00" && key($1,$2) <= until {
  split($2, t, ":"); b = int(t[1] / 6) * 6; k = sprintf("%s %02d:00", $1, b)
  n[k]++; m[k] += $7; tk[k] += $6; if (!(k in lo) || $7 < lo[k]) lo[k] = $7
} END { for (k in n) printf "%s block  runs %2d  mean margin %+5.1f  worst %+6.1f  mean tile task %4.1f min\n", k, n[k], m[k]/n[k], lo[k], tk[k]/n[k] }' | sort
