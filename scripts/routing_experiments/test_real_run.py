import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import real_run
import edge_depth_table as edt

LAT0, STEP = 20.98, 0.001  # 0.001 degrees of latitude is about 111 m


def chain_export(nodes: int):
    d = Path(tempfile.mkdtemp())
    rows = "edge_id,wkt,base_node,adj_node\n" + "".join(
        f'{i},"LINESTRING (105.75 {LAT0 + i * STEP:.6f}, 105.75 {LAT0 + (i + 1) * STEP:.6f})",{i},{i + 1}\n'
        for i in range(nodes - 1))
    (d / "edges.csv").write_text(rows)
    (d / "graph.json").write_text(json.dumps({"format_version": 2, "graph_hash": "h", "edge_count": nodes - 1, "node_count": nodes}))
    return d


def table(path: Path, edges: int, depth_of_edge):
    t0 = datetime(2026, 10, 9, tzinfo=timezone.utc)
    header = edt.TableHeader("h", "run1", tuple(t0 + timedelta(minutes=15 * i) for i in range(3)), edges)
    edt.write_table(path, header, [[depth_of_edge(e)] * 3 for e in range(edges)])
    return path


class RealRunTest(unittest.TestCase):
    def test_a_flooded_edge_cuts_the_route_share_of_a_limit_below_its_depth(self):
        export = chain_export(50)
        path = table(Path(tempfile.mkdtemp()) / "run1.bin", 49, lambda e: 40 if e == 25 else 0)
        result = real_run.run_real(export, [("wet", [path])], {"car": 30, "truck": 50}, per_class=5, seed=1, steps=[0])
        rows = {r["plan_limit"]: r for r in result["us092_limit_sweep"]["wet|run1|0"]["rows"]}
        self.assertLess(rows[30]["route_share"], 1.0)
        self.assertEqual(rows[50]["route_share"], 1.0)
        self.assertEqual(result["n_pairs"], 15)
        self.assertIn("One-way roads are open both ways: the export holds no one-way flag.", result["notes"])
        self.assertIn("wet|run1|0|car", result["us093_sticky_vs_arrival_only"])

    def test_workers_give_the_result_of_one_process(self):
        export = chain_export(50)
        path = table(Path(tempfile.mkdtemp()) / "run1.bin", 49, lambda e: 40 if e == 25 else 0)
        args = (export, [("wet", [path])], {"car": 30}, 3, 1)
        self.assertEqual(real_run.run_real(*args, steps=[0, 1], jobs=2), real_run.run_real(*args, steps=[0, 1], jobs=1))

    def test_a_table_of_another_graph_is_refused(self):
        export = chain_export(50)
        path = Path(tempfile.mkdtemp()) / "run1.bin"
        t0 = datetime(2026, 10, 9, tzinfo=timezone.utc)
        edt.write_table(path, edt.TableHeader("other", "run1", (t0, t0 + timedelta(minutes=15)), 49), [[0, 0]] * 49)
        with self.assertRaises(edt.StaleTableError):
            real_run.run_real(export, [("wet", [path])], {"car": 30}, per_class=2, seed=1, steps=[0])


if __name__ == "__main__":
    unittest.main()
