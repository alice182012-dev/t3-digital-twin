cd "$(git rev-parse --show-toplevel)/scripts/pipeline_margins" || exit 1
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. tests of the margin report"
python3 -m pytest -v -p no:cacheprovider --color=no -W error test_report.py 2>&1 | sed -n '/collected/,$p' | sed 's/ *\[ *[0-9]*%\]//' | sed 's/test_report.py:://' | grep -E "PASSED|FAILED|passed|failed"
echo
echo "2. the four runs of 2026-10-02 00:45 to 01:30 (a fixture, margins from the US-037 pass)"
printf '10-02 00:45 3.5 3.2 1.6 4.4 1.9\n10-02 01:00 3.4 3.5 1.7 5.0 4.1\n10-02 01:15 3.6 3.9 1.7 5.6 2.7\n10-02 01:30 3.5 3.4 1.8 6.1 2.4\n' | python3 report.py; echo "exit code: $?"
echo
echo "3. real rows from the server (read-only run_margins.sh 250), the 50 mm/h storm of 2026-10-02 00:45 to 13:00 +07"
OUT=$(bash run_margins.sh 250 | python3 report.py --since "10-02 00:45" --until "10-02 13:00"); CODE=$?
echo "$OUT" | cut -c1-165
echo "exit code: $CODE"
echo
echo "4. the same rows with the margin read by hour"
bash run_margins.sh 250 | awk -F' ' '$1=="10-02" && $2>="00:45" && $2<="13:00" && NF==7 {split($2,t,":"); h=t[1]; s[h]+=$7; n[h]++; tl[h]+=$6} END {for (h in s) printf "%s:00 hour  runs %d  mean margin %+.1f min  mean tile task %.1f min\n", h, n[h], s[h]/n[h], tl[h]/n[h]}' | sort
