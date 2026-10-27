import random
import unittest

import sticky_cost as sc
from sticky_cost import Distribution, Outcome, Summary
from sticky_reference import Edge, Graph

STEPS = (0, 900, 1800)


def table(by_edge):
    return lambda edge_id, step: by_edge.get(edge_id, [0, 0, 0])[step]


def compare(graph, origin, destination, by_edge, departure_s=0, limit_cm=20, margin_s=600, **kw):
    return sc.compare(graph, origin, destination, departure_s, 0, STEPS, table(by_edge), limit_cm, margin_s, **kw)


# Fast path O -> A -> D enters A -> D at 800 s. A slow direct edge O -> D takes 2000 s.
FAST_AND_SLOW = Graph([Edge(0, 0, 1, 800), Edge(1, 1, 2, 100), Edge(2, 0, 2, 2000)])


class CompareTest(unittest.TestCase):
    def test_same_when_nothing_is_flooded(self):
        r = compare(FAST_AND_SLOW, 0, 2, {})
        self.assertEqual((r.outcome, r.extra_s, r.exact), (Outcome.SAME, 0.0, True))

    def test_sticky_is_longer_when_the_margin_sees_a_step_the_arrival_does_not(self):
        # Edge 1 is entered at 800 s. Arrival-only reads step 0 (dry). The sticky window reaches 1400 s and
        # sees step 1, where the edge is flooded.
        r = compare(FAST_AND_SLOW, 0, 2, {1: [0, 30, 0]})
        self.assertEqual((r.outcome, r.extra_s), (Outcome.STICKY_LONGER, 2000 - 900))

    def test_sticky_has_no_route_when_the_only_path_floods_within_the_margin_after_the_arrival(self):
        graph = Graph([Edge(0, 0, 1, 800), Edge(1, 1, 2, 100)])
        r = compare(graph, 0, 2, {1: [0, 30, 0]}, margin_s=900)
        self.assertEqual((r.outcome, r.extra_s), (Outcome.STICKY_NO_ROUTE, None))

    def test_neither_routes_when_no_path_exists(self):
        r = compare(FAST_AND_SLOW, 2, 0, {})
        self.assertEqual((r.outcome, r.extra_s, r.exact), (Outcome.NEITHER_ROUTES, None, True))

    def test_the_departure_step_counts_for_the_sticky_side_when_the_departure_falls_inside_it(self):
        graph = Graph([Edge(0, 0, 1, 100)])
        r = sc.compare(graph, 0, 1, 1000, 900, STEPS, table({0: [0, 30, 0]}), 20, 0)
        self.assertEqual(r.outcome, Outcome.NEITHER_ROUTES)

    def test_an_inexact_arrival_only_search_is_recorded_as_inexact(self):
        graph = Graph([Edge(0, 0, 1, 10), Edge(1, 0, 1, 1000), Edge(5, 1, 2, 10)])
        r = compare(graph, 0, 2, {5: [30, 0, 0]}, margin_s=0, max_expansions=1)
        self.assertEqual((r.outcome, r.extra_s, r.exact), (Outcome.INEXACT, None, False))

    def test_an_inexact_record_bounds_the_extra_time_from_above_by_the_sticky_end_minus_the_lower_bound(self):
        graph = Graph([Edge(0, 0, 1, 100), Edge(1, 1, 2, 100), Edge(2, 0, 2, 1000)])
        r = compare(graph, 0, 2, {1: [30, 0, 0]}, margin_s=0, max_expansions=1)
        self.assertEqual((r.outcome, r.extra_s, r.exact, r.extra_s_at_most), (Outcome.INEXACT, None, False, 800.0))

    def test_a_departure_before_the_first_step_is_refused(self):
        with self.assertRaises(ValueError):
            sc.compare(FAST_AND_SLOW, 0, 2, -1, 0, STEPS, table({}), 20, 600)


def random_case(rng):
    nodes = rng.randint(3, 7)
    edges = []
    for i in range(rng.randint(nodes, nodes * 3)):
        edges.append(Edge(i, rng.randrange(nodes), rng.randrange(nodes), rng.choice([50, 200, 400, 700, 1500])))
    by_edge = {e.id: [rng.choice([0, 0, 30]) for _ in STEPS] for e in edges}
    return Graph(edges), nodes, by_edge


class ContainmentTest(unittest.TestCase):
    def test_sticky_never_ends_before_arrival_only_and_never_routes_alone(self):
        rng = random.Random(7)
        routed_both = exact_cases = 0
        for case in range(300):
            graph, nodes, by_edge = random_case(rng)
            departure_s = rng.choice([0, 300, 900, 1200])
            departure_step_s = max(t for t in STEPS if t <= departure_s)
            origin, destination = rng.sample(range(nodes), 2)
            margin_s = rng.choice([0, 300, 600, 1200])
            with self.subTest(case=case):
                r = sc.compare(graph, origin, destination, departure_s, departure_step_s, STEPS, table(by_edge), 20,
                               margin_s)
                if r.outcome is Outcome.INEXACT:
                    continue
                exact_cases += 1
                if r.outcome in (Outcome.SAME, Outcome.STICKY_LONGER):
                    routed_both += 1
                    self.assertGreaterEqual(r.extra_s, 0)
        self.assertGreater(exact_cases, 150)
        self.assertGreater(routed_both, 50)


class SummaryTest(unittest.TestCase):
    def test_groups_by_key_and_leaves_inexact_records_out_of_the_shares(self):
        records = [
            (("car", "peak"), sc.CompareRecord(Outcome.SAME, 0.0, True)),
            (("car", "peak"), sc.CompareRecord(Outcome.STICKY_LONGER, 100.0, True)),
            (("car", "peak"), sc.CompareRecord(Outcome.STICKY_LONGER, 300.0, True)),
            (("car", "peak"), sc.CompareRecord(Outcome.STICKY_NO_ROUTE, None, True)),
            (("car", "peak"), sc.CompareRecord(Outcome.INEXACT, None, False)),
            (("truck", "peak"), sc.CompareRecord(Outcome.NEITHER_ROUTES, None, True)),
        ]
        out = sc.summarize(records)
        self.assertEqual(
            out[("car", "peak")],
            Summary(n=5, n_inexact=1, share_sticky_no_route=0.25, share_sticky_longer=0.5,
                    extra_s=Distribution(n=3, mean=400 / 3, median=100.0, p90=300.0, max=300.0)),
        )
        self.assertEqual(
            out[("truck", "peak")],
            Summary(n=1, n_inexact=0, share_sticky_no_route=0.0, share_sticky_longer=0.0, extra_s=None),
        )

    def test_the_upper_bounds_of_inexact_records_with_a_sticky_route_are_summarised(self):
        out = sc.summarize([("k", sc.CompareRecord(Outcome.INEXACT, None, False, 22.0)),
                            ("k", sc.CompareRecord(Outcome.INEXACT, None, False, 10.0)),
                            ("k", sc.CompareRecord(Outcome.INEXACT, None, False))])
        self.assertEqual(out["k"].n_inexact, 3)
        self.assertEqual(out["k"].inexact_extra_s_at_most, sc.Distribution(2, 16.0, 16.0, 22.0, 22.0))

    def test_a_group_with_only_inexact_records_has_no_shares(self):
        out = sc.summarize([("k", sc.CompareRecord(Outcome.INEXACT, None, False))])
        self.assertEqual(out["k"], Summary(n=1, n_inexact=1, share_sticky_no_route=None, share_sticky_longer=None, extra_s=None))


if __name__ == "__main__":
    unittest.main()
