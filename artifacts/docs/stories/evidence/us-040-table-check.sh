cd "$(git rev-parse --show-toplevel)/scripts/edge_depth" || exit 1
echo "Host: $(hostname), $(uname -sm), Python $(python3 --version | cut -d' ' -f2)"
echo "Captured: $(date '+%Y-%m-%d %H:%M:%S %z')"
echo
echo "1. tests of the reader and writer, including the literal-bytes test"
python3 -m pytest -v -p no:cacheprovider --color=no test_edge_depth_table.py 2>&1 | sed -n '/collected/,$p' | sed 's/ *\[ *[0-9]*%\]//'
echo
echo "2. the golden file as bytes (2 edges, 2 steps, hash abc, run r1)"
python3 - <<'PY'
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from edge_depth_table import TableHeader, write_table, read_table
t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
p = Path(tempfile.mkdtemp()) / "golden.bin"
write_table(p, TableHeader("abc", "r1", (t0, t0 + timedelta(minutes=15)), 2), [[0, 1], [256, 65535]])
raw = p.read_bytes()
print(len(raw), "bytes:", raw.hex(" "))
t = read_table(p)
print("read back:", t.header.graph_hash, t.header.run_name, t.header.edge_count, [t.edge_depths_cm(e) for e in range(2)])
PY
echo
echo "3. a reader refuses a wrong version and a truncated body"
python3 - <<'PY'
import struct, tempfile
from datetime import datetime, timezone
from pathlib import Path
from edge_depth_table import TableHeader, TableFormatError, write_table, read_table
t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
p = Path(tempfile.mkdtemp()) / "t.bin"
write_table(p, TableHeader("abc", "r1", (t0,), 2), [[7], [8]])
raw = p.read_bytes()
for label, bad in (("version 2", raw[:4] + struct.pack("<H", 2) + raw[6:]), ("one byte short", raw[:-1])):
    p.write_bytes(bad)
    try:
        read_table(p)
    except TableFormatError as e:
        print(f"{label}: refused, {e}")
PY
echo
echo "4. 2,000,000 edges and 9 steps, the size the PRD estimates"
python3 - <<'PY'
import os, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from edge_depth_table import TableHeader, write_table, read_table
t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
n = 2_000_000
h = TableHeader("h", "r", tuple(t0 + timedelta(minutes=15 * i) for i in range(9)), n)
p = Path(tempfile.mkdtemp()) / "big.bin"
a = time.time(); write_table(p, h, ([10 + s for s in range(9)] for _ in range(n))); w = time.time() - a
a = time.time(); t = read_table(p); r = time.time() - a
print(f"{os.path.getsize(p) / 1e6:.1f} MB, write {w:.1f} s, open {r:.2f} s, edge 1999999 step 8 = {t.depth_cm(n - 1, 8)} cm")
PY
