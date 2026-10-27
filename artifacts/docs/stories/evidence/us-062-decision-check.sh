cd "$(git rev-parse --show-toplevel)" || exit 1
F=artifacts/docs/concepts/flood-map-reaction-time-findings.md
echo "Host: $(hostname), $(uname -sm)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. the findings page: the answer in short"
sed -n '/^## The answer in short/,/^## Evidence table/p' "$F" | sed '1d;$d' | fold -s -w 170
echo
T=$(sed -n '/^## Evidence table/,/^## Derived numbers/p' "$F" | grep -E '^\| E[0-9]+ ')
echo "2. evidence table: $(echo "$T" | wc -l | tr -d ' ') rows with a source. Languages: $(echo "$T" | awk -F'|' '{gsub(/ /,"",$6); print $6}' | sort | uniq -c | awk '{printf "%s %s, ", $2, $1}')"
echo
echo "3. the decision as recorded on the findings page"
sed -n '/^## Decision for US-062/,/^## Status history/p' "$F" | sed '1d;$d' | grep -v '^$' | fold -s -w 170
echo
echo "4. the 15-minute cycle in the code the decision keeps"
grep -n '^CYCLE_MINUTES' scripts/create_simulation.py
grep -n "schedule=" dags/flood_mapping_dag.py | head -2
echo
echo "5. the story status"
grep -n '^status:' artifacts/docs/user-stories/map-refresh-requirement-research.md
