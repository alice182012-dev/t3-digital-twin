#!/usr/bin/env bash
# Evidence for US-088. Read-only. Run from the repository root.
F=scripts/rain_events/hanoi_20260916_storm.csv
head -3 $F; echo "..."; tail -2 $F
python3 -I - <<'PY'
import csv
rows=[(int(a),float(b)) for a,b in list(csv.reader(open("scripts/rain_events/hanoi_20260916_storm.csv")))[1:]]
print(f"{len(rows)} rows, offsets {rows[0][0]} to {rows[-1][0]} min, step {rows[1][0]-rows[0][0]} min")
print(f"total {sum(v for _,v in rows)*0.5:.2f} mm, peak {max(v for _,v in rows):.2f} mm/h")
PY
python3 scripts/rain_replay.py preview $F 2026-10-08T08:45:00Z 5
git ls-files --error-unmatch $F
