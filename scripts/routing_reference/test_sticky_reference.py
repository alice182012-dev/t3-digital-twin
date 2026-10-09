import random
import unittest

from sticky_reference import (
    Crossing,
    Edge,
    Graph,
    Route,
    StickyClosure,
    earliest_arrival,
    find_crossings,
)

STEPS = tuple(900 * k for k in range(9))  # 15-minute steps over 2 hours


def depth_table(by_edge):
    """by_edge maps an edge id to the depth in cm at each step. Edges not listed are dry."""
    return lambda edge_id, step: by_edge.get(edge_id, [0] * len(STEPS))[step]


def rule(by_edge, limit_cm=20, departure_s=0, margin_s=600):
    return StickyClosure(STEPS, depth_table(by_edge), limit_cm, departure_s, margin_s)


def diamond():
    """0 -> 1 -> 3 is fast (edge 1 is the corridor road). 0 -> 2 -> 3 is the detour."""
    return Graph([Edge(0, 0, 1, 600), Edge(1, 1, 3, 600), Edge(2, 0, 2, 900), Edge(3, 2, 3, 900)])


def no_detour():
    return Graph([Edge(0, 0, 1, 600), Edge(1, 1, 3, 600)])


FLOODED_FROM_STEP_1 = [0, 50, 50, 50, 50, 50, 50, 50, 50]


class StickyClosureTest(unittest.TestCase):
    def test_a_dry_road_is_open(self):
        self.assertFalse(rule({}).is_closed(1, arrival_s=600))

    def test_a_road_that_floods_inside_the_window_is_closed(self):
        r = rule({1: FLOODED_FROM_STEP_1})
        self.assertTrue(r.is_closed(1, arrival_s=600))  # window 0..1200 holds step 900

    def test_a_road_that_floods_after_the_window_is_open(self):
        r = rule({1: [0, 0, 0, 0, 50, 50, 50, 50, 50]})  # floods at 3600 s
        self.assertFalse(r.is_closed(1, arrival_s=900))  # window 0..1500

    def test_the_end_of_the_window_is_included(self):
        r = rule({1: FLOODED_FROM_STEP_1}, margin_s=300)
        self.assertTrue(r.is_closed(1, arrival_s=600))  # window 0..900 reaches step 900
        r = rule({1: FLOODED_FROM_STEP_1}, margin_s=299)
        self.assertFalse(r.is_closed(1, arrival_s=600))  # window 0..899 stops short

    def test_an_arrival_exactly_on_a_step_counts_that_step(self):
        r = rule({1: FLOODED_FROM_STEP_1}, margin_s=0)
        self.assertTrue(r.is_closed(1, arrival_s=900))
        self.assertFalse(r.is_closed(1, arrival_s=899))

    def test_a_departure_between_two_steps_ignores_the_step_before_it(self):
        wet_at_step_0 = {1: [50, 0, 0, 0, 0, 0, 0, 0, 0]}
        self.assertFalse(rule(wet_at_step_0, departure_s=450).is_closed(1, arrival_s=450))
        wet_at_step_1 = {1: [0, 50, 0, 0, 0, 0, 0, 0, 0]}
        self.assertTrue(rule(wet_at_step_1, departure_s=450).is_closed(1, arrival_s=450))  # window 450..1050

    def test_water_that_drained_before_departure_does_not_close_the_road(self):
        drains = {1: [50, 50, 0, 0, 0, 0, 0, 0, 0]}
        self.assertTrue(rule(drains, departure_s=0).is_closed(1, arrival_s=1200))
        self.assertFalse(rule(drains, departure_s=1800).is_closed(1, arrival_s=2400))

    def test_flooded_then_drained_stays_closed_for_a_later_arrival(self):
        drains = {1: [50, 50, 0, 0, 0, 0, 0, 0, 0]}  # flooded until 900 s
        self.assertTrue(rule(drains).is_closed(1, arrival_s=1500))  # scenario 3 shape: arrives after it drains

    def test_the_limit_decides_which_vehicle_is_blocked(self):
        shallow = {1: [0, 25, 25, 25, 25, 25, 25, 25, 25]}
        self.assertTrue(rule(shallow, limit_cm=20).is_closed(1, arrival_s=600))  # motorbike
        self.assertFalse(rule(shallow, limit_cm=30).is_closed(1, arrival_s=600))  # car

    def test_a_depth_equal_to_the_limit_closes_the_road(self):
        at_limit = {1: [0, 20, 20, 20, 20, 20, 20, 20, 20]}
        self.assertTrue(rule(at_limit, limit_cm=20).is_closed(1, arrival_s=600))
        self.assertFalse(rule(at_limit, limit_cm=21).is_closed(1, arrival_s=600))

    def test_closing_step_names_the_first_step_that_closes_the_road(self):
        r = rule({1: [0, 0, 50, 50, 0, 0, 0, 0, 0]})
        self.assertEqual(r.closing_step(1, arrival_s=1500), 2)
        self.assertIsNone(r.closing_step(1, arrival_s=600))


class EarliestArrivalTest(unittest.TestCase):
    def test_a_dry_network_takes_the_fast_road(self):
        route = earliest_arrival(diamond(), 0, 3, rule({}))

        self.assertEqual(route, Route(edge_ids=(0, 1), arrivals_s=(0, 600), end_s=1200))

    def test_a_road_that_rises_before_arrival_sends_the_route_to_the_detour(self):
        route = earliest_arrival(diamond(), 0, 3, rule({1: FLOODED_FROM_STEP_1}))

        self.assertEqual(route, Route(edge_ids=(2, 3), arrivals_s=(0, 900), end_s=1800))

    def test_a_road_that_rises_after_passing_stays_on_the_route(self):
        route = earliest_arrival(diamond(), 0, 3, rule({1: [0, 0, 0, 0, 50, 50, 50, 50, 50]}))

        self.assertEqual(route.edge_ids, (0, 1))

    def test_no_detour_gives_no_route(self):
        self.assertIsNone(earliest_arrival(no_detour(), 0, 3, rule({1: FLOODED_FROM_STEP_1})))

    def test_a_trip_that_starts_at_the_destination_is_empty(self):
        self.assertEqual(earliest_arrival(diamond(), 3, 3, rule({})), Route((), (), 0))

    def test_the_trip_starts_at_the_departure_time(self):
        route = earliest_arrival(diamond(), 0, 3, rule({}, departure_s=1800))

        self.assertEqual(route.arrivals_s, (1800, 2400))
        self.assertEqual(route.end_s, 3000)

    def test_an_unreachable_destination_gives_no_route(self):
        self.assertIsNone(earliest_arrival(diamond(), 3, 0, rule({})))

    def test_a_closed_first_road_blocks_the_trip_at_the_origin(self):
        self.assertIsNone(earliest_arrival(no_detour(), 0, 3, rule({0: [50] * 9})))

    def test_the_search_matches_brute_force_on_random_graphs(self):
        rng = random.Random(47)
        for case in range(300):
            nodes = 5
            edges = [
                Edge(i, rng.randrange(nodes), rng.randrange(nodes), rng.choice([300, 600, 900, 1200]))
                for i in range(rng.randrange(10, 24))
            ]
            depths = {e.id: [rng.choice([0, 0, 50]) for _ in STEPS] for e in edges}
            r = rule(depths, departure_s=rng.choice([0, 900]))
            graph = Graph(edges)

            found = earliest_arrival(graph, 0, nodes - 1, r)
            best = brute_force_end(graph, 0, nodes - 1, r)

            with self.subTest(case=case):
                if best is None:
                    self.assertIsNone(found)
                else:
                    self.assertIsNotNone(found)
                    self.assertEqual(found.end_s, best)
                    self.assertEqual(find_crossings(found.edge_ids, [graph.edge(i).seconds for i in found.edge_ids], r), [])


def brute_force_end(graph, origin, destination, r):
    """Earliest end time over every simple path, found by trying them all."""
    best = None

    def walk(node, time, seen):
        nonlocal best
        if node == destination:
            best = time if best is None else min(best, time)
            return
        for edge in graph.out_edges(node):
            if edge.head in seen or r.is_closed(edge.id, time):
                continue
            walk(edge.head, time + edge.seconds, seen | {edge.head})

    walk(origin, r.departure_s, {origin})
    return best


class FindCrossingsTest(unittest.TestCase):
    def test_a_route_over_dry_roads_has_no_crossing(self):
        self.assertEqual(find_crossings((0, 1), (600, 600), rule({})), [])

    def test_a_route_over_a_road_that_rises_before_arrival_crosses_it(self):
        crossings = find_crossings((0, 1), (600, 600), rule({1: FLOODED_FROM_STEP_1}))

        self.assertEqual(crossings, [Crossing(position=1, edge_id=1, arrival_s=600, closing_step=1)])

    def test_arrival_adds_up_the_time_of_the_edges_before_it(self):
        floods_at_1800_s = {1: [0, 0, 50, 50, 50, 50, 50, 50, 50]}

        slow_first_edge = find_crossings((0, 1), (1800, 600), rule(floods_at_1800_s))
        fast_first_edge = find_crossings((0, 1), (600, 600), rule(floods_at_1800_s))

        self.assertEqual(slow_first_edge, [Crossing(position=1, edge_id=1, arrival_s=1800, closing_step=2)])
        self.assertEqual(fast_first_edge, [])  # arrival 600 gives window 0..1200, which stops before 1800 s

    def test_the_trip_starts_at_the_departure_time(self):
        drains = {1: [50, 50, 0, 0, 0, 0, 0, 0, 0]}

        self.assertEqual(find_crossings((0, 1), (600, 600), rule(drains, departure_s=1800)), [])

    def test_the_clock_runs_from_the_requested_departure_and_the_window_from_its_step(self):
        floods_at_1800_s = {1: [0, 0, 50, 50, 50, 50, 50, 50, 50]}
        floored = StickyClosure(STEPS, depth_table(floods_at_1800_s), 20, departure_s=840, window_start_s=0)

        crossings = find_crossings((0, 1), (1000, 600), floored)

        self.assertEqual(crossings, [Crossing(position=1, edge_id=1, arrival_s=1840, closing_step=2)])

    def test_the_step_that_contains_the_departure_still_counts(self):
        wet_at_step_0 = {1: [50, 0, 0, 0, 0, 0, 0, 0, 0]}
        floored = StickyClosure(STEPS, depth_table(wet_at_step_0), 20, departure_s=840, window_start_s=0)

        self.assertTrue(floored.is_closed(1, arrival_s=840))

    def test_a_departure_on_a_step_gives_the_same_crossings_as_one_time(self):
        floods_at_1800_s = {1: [0, 0, 50, 50, 50, 50, 50, 50, 50]}
        on_step = StickyClosure(STEPS, depth_table(floods_at_1800_s), 20, departure_s=900, window_start_s=900)

        self.assertEqual(find_crossings((0, 1), (1000, 600), on_step),
                         find_crossings((0, 1), (1000, 600), rule(floods_at_1800_s, departure_s=900)))
        self.assertEqual(find_crossings((0, 1), (1000, 600), on_step),
                         [Crossing(position=1, edge_id=1, arrival_s=1900, closing_step=2)])

    def test_every_crossing_is_reported(self):
        crossings = find_crossings((0, 1), (600, 600), rule({0: [50] * 9, 1: [50] * 9}))

        self.assertEqual([c.edge_id for c in crossings], [0, 1])

    def test_edges_and_times_must_line_up(self):
        with self.assertRaises(ValueError):
            find_crossings((0, 1), (600,), rule({}))


class GraphTest(unittest.TestCase):
    def test_edge_ids_must_be_unique(self):
        with self.assertRaises(ValueError):
            Graph([Edge(0, 0, 1, 1), Edge(0, 1, 2, 1)])

    def test_a_negative_travel_time_is_refused(self):
        with self.assertRaises(ValueError):
            Edge(0, 0, 1, -1)


class StickyClosureValidationTest(unittest.TestCase):
    def test_step_times_must_increase(self):
        with self.assertRaises(ValueError):
            StickyClosure((0, 900, 900), lambda e, s: 0, 20)

    def test_a_negative_margin_is_refused(self):
        with self.assertRaises(ValueError):
            StickyClosure(STEPS, lambda e, s: 0, 20, margin_s=-1)


if __name__ == "__main__":
    unittest.main()
