import random
import unittest

import precaution as pc
from precaution import FractionRow, PlanOptions
from sticky_cost import Distribution
from sticky_reference import Edge, Graph

STEPS = (0, 900, 1800)

# The short road O -> A -> D is 200 s. The detour O -> D is 500 s.
WITH_DETOUR = Graph([Edge(0, 0, 1, 100), Edge(1, 1, 2, 100), Edge(2, 0, 2, 500)])
NO_DETOUR = Graph([Edge(0, 0, 1, 100), Edge(1, 1, 2, 100)])


def table(by_edge):
    return lambda edge_id, step: by_edge.get(edge_id, [0, 0, 0])[step]


def plan(graph, by_edge, fraction=0.5, limit_cm=20, origin=0, destination=2, departure_s=0, margin_s=600):
    return pc.plan_options(graph, origin, destination, departure_s, 0, STEPS, table(by_edge), limit_cm, fraction, margin_s)


class PlanOptionsTest(unittest.TestCase):
    def test_shallow_water_on_the_short_road_recommends_the_detour_and_shows_the_short_road_second(self):
        o = plan(WITH_DETOUR, {1: [15, 15, 15]})
        self.assertEqual(o.recommended.edge_ids, (2,))
        self.assertEqual(o.second.edge_ids, (0, 1))
        self.assertEqual((o.flagged_through_water, o.ran_precaution_search), (False, True))

    def test_no_detour_falls_back_to_the_limit_route_flagged_with_one_option(self):
        o = plan(NO_DETOUR, {1: [15, 15, 15]})
        self.assertEqual(o.recommended.edge_ids, (0, 1))
        self.assertIsNone(o.second)
        self.assertEqual((o.flagged_through_water, o.ran_precaution_search), (True, True))

    def test_a_dry_graph_gives_one_option_and_skips_the_precaution_search(self):
        o = plan(WITH_DETOUR, {})
        self.assertEqual(o.recommended.edge_ids, (0, 1))
        self.assertIsNone(o.second)
        self.assertEqual((o.flagged_through_water, o.ran_precaution_search), (False, False))

    def test_water_at_the_limit_closes_the_short_road_for_both_searches(self):
        o = plan(WITH_DETOUR, {1: [20, 20, 20]})
        self.assertEqual(o.recommended.edge_ids, (2,))
        self.assertIsNone(o.second)
        self.assertEqual((o.flagged_through_water, o.ran_precaution_search), (False, False))

    def test_depth_at_the_precaution_depth_counts_as_touching_it(self):
        o = plan(WITH_DETOUR, {1: [10, 10, 10]})
        self.assertEqual(o.recommended.edge_ids, (2,))

    def test_water_that_arrives_after_the_margin_does_not_touch_the_route(self):
        o = plan(WITH_DETOUR, {1: [0, 0, 15]}, margin_s=0)
        self.assertEqual((o.recommended.edge_ids, o.ran_precaution_search), ((0, 1), False))

    def test_no_route_under_the_limit_gives_no_options(self):
        o = plan(NO_DETOUR, {1: [30, 30, 30]})
        self.assertEqual(o, PlanOptions(None, None, False, False))

    def test_a_zero_fraction_makes_every_edge_touch_the_precaution_depth(self):
        o = plan(NO_DETOUR, {}, fraction=0)
        self.assertEqual((o.recommended.edge_ids, o.flagged_through_water, o.ran_precaution_search), ((0, 1), True, True))


def random_case(rng):
    nodes = rng.randint(3, 7)
    edges = [Edge(i, rng.randrange(nodes), rng.randrange(nodes), rng.choice([50, 200, 400, 700, 1500]))
             for i in range(rng.randint(nodes, nodes * 4))]
    by_edge = {e.id: [rng.choice([0, 0, 0, 12, 30]) for _ in STEPS] for e in edges}
    return Graph(edges), nodes, by_edge


class ContainmentTest(unittest.TestCase):
    def test_the_recommended_route_never_ends_before_the_second(self):
        rng = random.Random(11)
        both = fallback = skipped = 0
        for case in range(300):
            graph, nodes, by_edge = random_case(rng)
            departure_s = rng.choice([0, 300, 900, 1200])
            departure_step_s = max(t for t in STEPS if t <= departure_s)
            origin, destination = rng.sample(range(nodes), 2)
            with self.subTest(case=case):
                o = pc.plan_options(graph, origin, destination, departure_s, departure_step_s, STEPS, table(by_edge), 20,
                                    rng.choice([0.25, 0.5]), rng.choice([0, 300, 600, 1200]))
                if o.recommended is None:
                    self.assertIsNone(o.second)
                    continue
                fallback += o.flagged_through_water
                skipped += not o.ran_precaution_search
                if o.second is not None:
                    both += 1
                    self.assertGreaterEqual(o.recommended.end_s, o.second.end_s)
                    self.assertNotEqual(o.recommended.edge_ids, o.second.edge_ids)
        self.assertGreater(both, 20)
        self.assertGreater(fallback, 5)
        self.assertGreater(skipped, 20)


class SweepFractionTest(unittest.TestCase):
    def test_counts_each_outcome_per_vehicle_and_fraction(self):
        graph = Graph([Edge(0, 0, 1, 100), Edge(1, 1, 2, 100), Edge(2, 0, 2, 500), Edge(3, 3, 4, 100), Edge(4, 5, 6, 100)])
        by_edge = {1: [15, 15, 15], 3: [15, 15, 15], 4: [30, 30, 30]}
        pairs = [(0, 2), (3, 4), (5, 6), (6, 5), (0, 1)]
        out = pc.sweep_fraction(graph, pairs, 0, 0, STEPS, table(by_edge), 600, {"car": 20}, [0.5])
        self.assertEqual(
            out[("car", 0.5)],
            FractionRow(
                n_routed=3,
                n_no_route=2,
                share_recommended_under_precaution=2 / 3,
                share_flagged=1 / 3,
                share_single_option=2 / 3,
                share_search_skipped=1 / 3,
                extra_s=Distribution(n=3, mean=100.0, median=0.0, p90=300.0, max=300.0),
            ),
        )

    def test_a_vehicle_with_no_routed_pair_has_no_shares(self):
        out = pc.sweep_fraction(NO_DETOUR, [(2, 0)], 0, 0, STEPS, table({}), 600, {"foot": 40}, [0.5])
        self.assertEqual(out[("foot", 0.5)], FractionRow(0, 1, None, None, None, None, None))

    def test_a_higher_limit_admits_the_shallow_road_and_cuts_the_extra_time(self):
        out = pc.sweep_fraction(WITH_DETOUR, [(0, 2)], 0, 0, STEPS, table({1: [25, 25, 25]}), 600,
                                {"car": 30, "motorbike": 20}, [0.5])
        self.assertEqual(out[("car", 0.5)].extra_s.max, 300)
        self.assertEqual(out[("motorbike", 0.5)].extra_s.max, 0)


if __name__ == "__main__":
    unittest.main()
