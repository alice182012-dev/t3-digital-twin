import json
import tempfile
import unittest
from pathlib import Path

from corridor import RoadNetwork, Way, load_ways

# 0.001 degrees of longitude at latitude 21 is about 103.9 m.
CROSS = [
    Way("way/1", ((105.760, 21.025), (105.761, 21.025), (105.762, 21.025))),  # west to east
    Way("way/2", ((105.761, 21.024), (105.761, 21.025), (105.761, 21.026))),  # south to north
]


class RoadNetworkTest(unittest.TestCase):
    def test_a_shared_vertex_becomes_a_node_and_splits_both_ways(self):
        net = RoadNetwork.from_ways(CROSS)

        self.assertEqual(len(net.node_xy), 5)  # four ends and the crossing
        self.assertEqual(len(net.edges), 8)  # four road pieces, two directions each

    def test_a_vertex_used_by_one_way_does_not_split_it(self):
        way = Way("way/9", ((105.760, 21.025), (105.7605, 21.0252), (105.761, 21.025)))

        net = RoadNetwork.from_ways([way])

        self.assertEqual(len(net.node_xy), 2)
        self.assertEqual(len(net.edges), 2)

    def test_length_follows_the_polyline(self):
        way = Way("way/9", ((105.760, 21.025), (105.7605, 21.0252), (105.761, 21.025)))

        straight = RoadNetwork.from_ways([Way("way/8", ((105.760, 21.025), (105.761, 21.025)))])
        bent = RoadNetwork.from_ways([way])

        self.assertAlmostEqual(straight.edges[0].length_m, 103.9, delta=0.5)
        self.assertGreater(bent.edges[0].length_m, straight.edges[0].length_m)

    def test_each_edge_has_a_reverse_edge(self):
        net = RoadNetwork.from_ways(CROSS)

        for edge in net.edges:
            reverse = net.edges[edge.id ^ 1]
            self.assertEqual((reverse.tail, reverse.head), (edge.head, edge.tail))
            self.assertEqual(reverse.length_m, edge.length_m)

    def test_edge_ids_are_dense_from_zero(self):
        net = RoadNetwork.from_ways(CROSS)

        self.assertEqual([e.id for e in net.edges], list(range(len(net.edges))))

    def test_nearest_node_finds_the_closest_vertex_node(self):
        net = RoadNetwork.from_ways(CROSS)

        node = net.nearest_node(lon=105.7611, lat=21.0251)

        self.assertEqual(net.node_xy[node], (105.761, 21.025))

    def test_the_shortest_path_goes_by_length(self):
        net = RoadNetwork.from_ways(CROSS)
        west = net.nearest_node(105.760, 21.025)
        north = net.nearest_node(105.761, 21.026)

        path = net.shortest_path_edges(west, north)

        self.assertEqual(len(path), 2)
        self.assertEqual(net.edges[path[0]].tail, west)
        self.assertEqual(net.edges[path[-1]].head, north)

    def test_banned_edges_are_not_used(self):
        loop = [
            Way("way/1", ((105.760, 21.025), (105.761, 21.025))),
            Way("way/2", ((105.761, 21.025), (105.7615, 21.0255), (105.762, 21.025))),
            Way("way/3", ((105.761, 21.025), (105.762, 21.025))),
            Way("way/4", ((105.762, 21.025), (105.7625, 21.025))),
        ]
        net = RoadNetwork.from_ways(loop)
        start = net.nearest_node(105.760, 21.025)
        end = net.nearest_node(105.7625, 21.025)
        direct = net.shortest_path_edges(start, end)
        shortcut = direct[1]

        detour = net.shortest_path_edges(start, end, banned=frozenset({shortcut}))

        self.assertNotIn(shortcut, detour)
        self.assertGreater(sum(net.edges[e].length_m for e in detour), sum(net.edges[e].length_m for e in direct))

    def test_no_path_gives_none(self):
        net = RoadNetwork.from_ways(
            [Way("way/1", ((105.760, 21.025), (105.761, 21.025))), Way("way/2", ((105.770, 21.025), (105.771, 21.025)))]
        )

        self.assertIsNone(net.shortest_path_edges(net.nearest_node(105.760, 21.025), net.nearest_node(105.771, 21.025)))

    def test_graph_converts_length_to_seconds_at_one_speed(self):
        net = RoadNetwork.from_ways(CROSS)

        graph = net.graph(speed_mps=10.0)

        for edge in net.edges:
            self.assertAlmostEqual(graph.edge(edge.id).seconds, edge.length_m / 10.0)


class LoadWaysTest(unittest.TestCase):
    def test_reads_line_strings_and_skips_other_geometry(self):
        collection = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"@id": "way/5"}, "geometry": {"type": "LineString", "coordinates": [[105.76, 21.025], [105.761, 21.025]]}},
                {"type": "Feature", "properties": {"@id": "node/6"}, "geometry": {"type": "Point", "coordinates": [105.76, 21.025]}},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "roads.geojson"
            path.write_text(json.dumps(collection))

            ways = load_ways(path)

        self.assertEqual(ways, [Way("way/5", ((105.76, 21.025), (105.761, 21.025)))])


if __name__ == "__main__":
    unittest.main()
