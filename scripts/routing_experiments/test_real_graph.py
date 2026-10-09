import json
import tempfile
import unittest
from pathlib import Path

import real_graph
from sticky_reference import StickyClosure, earliest_arrival

# 0.001 degrees of latitude is about 111 m.
ROWS = (
    'edge_id,wkt,base_node,adj_node\n'
    '0,"LINESTRING (105.7 21.000, 105.7 21.001)",10,11\n'
    '1,"LINESTRING (105.7 21.001, 105.7 21.002)",11,12\n'
)


def export(meta_extra=None, rows=ROWS):
    d = Path(tempfile.mkdtemp())
    meta = {"format_version": 2, "graph_hash": "h", "edge_count": 2, "node_count": 3, **(meta_extra or {})}
    (d / "graph.json").write_text(json.dumps(meta))
    (d / "edges.csv").write_text(rows)
    return d


class LoadGraphTest(unittest.TestCase):
    def test_a_length_is_read_from_the_wkt(self):
        self.assertAlmostEqual(real_graph.wkt_length_m("LINESTRING (105.7 21.000, 105.7 21.001)"), 111.2, delta=0.5)

    def test_a_road_is_open_in_both_directions_with_its_own_id(self):
        graph, graph_hash = real_graph.load_graph(export(), speed_mps=10)
        rule = StickyClosure((0.0, 900.0), lambda e, s: 0, 20)
        forward = earliest_arrival(graph, 10, 12, rule)
        backward = earliest_arrival(graph, 12, 10, rule)
        self.assertEqual(graph_hash, "h")
        self.assertEqual(forward.edge_ids, (0, 1))
        self.assertEqual(backward.edge_ids, (1, 0))
        self.assertAlmostEqual(forward.end_s, 22.2, delta=0.2)

    def test_a_format_1_export_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no base_node"):
            real_graph.load_graph(export({"format_version": 1}))

    def test_a_row_count_that_differs_from_the_edge_count_is_refused(self):
        with self.assertRaisesRegex(ValueError, "edge_count"):
            real_graph.load_graph(export({"edge_count": 3}))


if __name__ == "__main__":
    unittest.main()
