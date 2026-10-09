import random
import unittest

from arrival_only import ArrivalOnlyClosure, ArrivalOnlyResult, SimplePathSearch, earliest_arrival_arrival_only
from sticky_reference import Edge, Graph, Route

STEPS = (0, 900, 1800)


def closure(by_edge, limit_cm=20, steps=STEPS):
    return ArrivalOnlyClosure(steps, lambda edge_id, step: by_edge.get(edge_id, [0] * len(steps))[step], limit_cm)


class ClosureTest(unittest.TestCase):
    def test_reads_the_step_at_or_before_the_arrival(self):
        rule = closure({7: [0, 30, 0]})
        self.assertFalse(rule.is_closed(7, 899))
        self.assertTrue(rule.is_closed(7, 900))
        self.assertTrue(rule.is_closed(7, 1799))
        self.assertFalse(rule.is_closed(7, 1800))

    def test_a_depth_equal_to_the_limit_closes(self):
        self.assertTrue(closure({7: [20, 0, 0]}).is_closed(7, 0))

    def test_before_the_first_step_reads_step_zero_and_after_the_last_reads_the_last(self):
        rule = closure({7: [30, 0, 30]})
        self.assertTrue(rule.is_closed(7, -500))
        self.assertTrue(rule.is_closed(7, 99_999))

    def test_a_later_step_does_not_leak_into_an_earlier_arrival(self):
        self.assertFalse(closure({7: [0, 0, 30]}).is_closed(7, 1799))


# O -> A has a fast edge (100 s) and a slow detour through B (500 s + 400 s). A -> D is closed during step 0.
OVERTAKE = Graph(
    [
        Edge(0, 0, 1, 100),
        Edge(1, 0, 3, 500),
        Edge(2, 3, 1, 400),
        Edge(3, 1, 2, 100),
    ]
)


class SearchTest(unittest.TestCase):
    def test_a_later_arrival_passes_a_road_that_was_closed_for_the_earlier_one(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({3: [30, 0, 0]}), 0)
        self.assertEqual(result, ArrivalOnlyResult(Route((1, 2, 3), (0, 500, 900), 1000), exact=True))

    def test_the_fast_label_wins_when_nothing_is_closed(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({}), 0)
        self.assertEqual(result.route, Route((0, 3), (0, 100), 200))

    def test_origin_is_destination(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 1, 1, closure({}), 250)
        self.assertEqual(result, ArrivalOnlyResult(Route((), (), 250), exact=True))

    def test_unreachable(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 2, 0, closure({}), 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))

    def test_closed_for_every_arrival(self):
        result = earliest_arrival_arrival_only(OVERTAKE, 0, 2, closure({3: [30, 30, 30]}), 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))



def oracle(graph, origin, destination, rule, departure_s):
    """Minimum arrival over every simple path, by plain enumeration."""
    best = float("inf")

    def walk(node, time, visited):
        nonlocal best
        if node == destination:
            best = min(best, time)
            return
        for edge in graph.out_edges(node):
            if edge.head not in visited and not rule.is_closed(edge.id, time):
                walk(edge.head, time + edge.seconds, visited | {edge.head})

    walk(origin, departure_s, {origin})
    return None if best == float("inf") else best


def walk_route(graph, origin, route, rule, departure_s):
    """Replays a route and returns its end time, or raises if it is not a simple, open, connected walk."""
    node, time, visited = origin, departure_s, [origin]
    for edge_id, entered in zip(route.edge_ids, route.arrivals_s, strict=True):
        (edge,) = [e for e in graph.out_edges(node) if e.id == edge_id]
        assert entered == time and not rule.is_closed(edge_id, time)
        node, time = edge.head, time + edge.seconds
        visited.append(node)
    assert len(set(visited)) == len(visited)
    return node, time


def random_case(seed):
    rng = random.Random(seed)
    nodes = rng.randint(2, 7)
    steps = (0, 300, 600, 900)
    edges = [
        Edge(i, rng.randrange(nodes), rng.randrange(nodes), rng.randint(1, 600)) for i in range(rng.randint(1, 14))
    ]
    graph = Graph(edges, both_directions=rng.random() < 0.5)
    depths = {e.id: [rng.choice((0, 0, 10, 30)) for _ in steps] for e in edges}
    origin, destination = rng.randrange(nodes), rng.randrange(nodes)
    return graph, origin, destination, closure(depths, steps=steps), rng.choice((0, 150, 450))


class OracleTest(unittest.TestCase):
    def test_matches_brute_force_on_random_graphs(self):
        found = 0
        for seed in range(400):
            graph, origin, destination, rule, departure = random_case(seed)
            with self.subTest(seed=seed):
                expected = oracle(graph, origin, destination, rule, departure)
                result = earliest_arrival_arrival_only(graph, origin, destination, rule, departure)
                self.assertTrue(result.exact)
                if expected is None:
                    self.assertIsNone(result.route)
                    continue
                found += 1
                self.assertEqual(result.route.end_s, expected)
                self.assertEqual(walk_route(graph, origin, result.route, rule, departure), (destination, expected))
        self.assertGreater(found, 100, "too few reachable cases to exercise the search")


def wide_random_case(seed):
    """More nodes, up to eight steps, and roads that close and reopen, so the pruning meets recession."""
    rng = random.Random(seed)
    nodes = rng.randint(3, 9)
    gap = rng.choice((120, 300))
    steps = tuple(i * gap for i in range(rng.randint(2, 8)))
    edges = [Edge(i, rng.randrange(nodes), rng.randrange(nodes), rng.randint(1, 500)) for i in range(rng.randint(3, 20))]
    graph = Graph(edges, both_directions=rng.random() < 0.6)
    depths = {e.id: [rng.choice((0, 0, 30)) for _ in steps] for e in edges}
    return graph, rng.randrange(nodes), rng.randrange(nodes), closure(depths, steps=steps), rng.choice((0, 100, 400, 900))


class PruningTest(unittest.TestCase):
    def test_matches_brute_force_on_wide_random_graphs(self):
        found = 0
        for seed in range(1500):
            graph, origin, destination, rule, departure = wide_random_case(seed)
            with self.subTest(seed=seed):
                expected = oracle(graph, origin, destination, rule, departure)
                result, _ = SimplePathSearch(graph).earliest_arrival(origin, destination, rule, departure)
                self.assertTrue(result.exact)
                self.assertEqual(None if result.route is None else result.route.end_s, expected)
                found += expected is not None
        self.assertGreater(found, 700)

    def test_a_destination_that_every_closed_road_shuts_off_ends_without_enumerating_paths(self):
        # A 6 x 6 grid is a dense web of simple paths. The only road into the destination is closed at every step.
        side = 6
        node = lambda r, c: r * side + c  # noqa: E731
        pairs = [(node(r, c), node(r, c + 1)) for r in range(side) for c in range(side - 1)]
        pairs += [(node(r, c), node(r + 1, c)) for r in range(side - 1) for c in range(side)]
        edges = [Edge(i, tail, head, 10) for i, (tail, head) in enumerate(pairs)]
        sink = side * side
        gate = Edge(len(edges), node(side - 1, side - 1), sink, 10)
        graph = Graph(edges + [gate], both_directions=True)
        rule = closure({gate.id: [30, 30]}, steps=(0, 900))
        result, expansions = _counted(graph, node(0, 0), sink, rule, 0, max_expansions=1000)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))
        self.assertEqual(expansions, 0)

    def test_a_road_that_opens_too_late_to_catch_ends_without_enumerating_paths(self):
        # The gate opens at 900 s. Every route arrives at its tail before 900 s and the traveller cannot wait,
        # but the relaxation can, so only the arrival-time check separates this from the case above.
        graph = Graph([Edge(0, 0, 1, 100), Edge(1, 1, 2, 100), Edge(2, 2, 3, 10)])
        rule = closure({2: [30, 0]}, steps=(0, 900))
        result, _ = _counted(graph, 0, 3, rule, 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))

def _counted(graph, origin, destination, rule, departure_s, max_expansions=1_000_000):
    return SimplePathSearch(graph).earliest_arrival(origin, destination, rule, departure_s, max_expansions)


# O=0, A=1, D=2, B=3. A -> D is closed in step 0 and open from 900 s. Going O -> A -> O -> A reaches A at 1500 s.
O, A, D, B = 0, 1, 2, 3
LOOP = [Edge(0, O, A, 500), Edge(1, A, O, 500), Edge(2, A, D, 10)]
DETOUR = [Edge(3, O, B, 1000), Edge(4, B, D, 600)]
A_TO_D_OPENS_AT_900 = {2: [30, 0]}


class NoLoopTest(unittest.TestCase):
    def test_the_search_takes_the_later_detour_that_avoids_the_loop(self):
        simple = earliest_arrival_arrival_only(Graph(LOOP + DETOUR), O, D, closure(A_TO_D_OPENS_AT_900, steps=(0, 900)), 0)
        self.assertEqual(simple, ArrivalOnlyResult(Route((3, 4), (0, 1000), 1600), exact=True))

    def test_no_simple_route_is_exact_none_even_when_a_loop_would_reach(self):
        result = earliest_arrival_arrival_only(Graph(LOOP), O, D, closure(A_TO_D_OPENS_AT_900, steps=(0, 900)), 0)
        self.assertEqual(result, ArrivalOnlyResult(None, exact=True))

    def test_origin_is_destination(self):
        result = earliest_arrival_arrival_only(Graph(LOOP), A, A, closure({}, steps=(0, 900)), 250)
        self.assertEqual(result, ArrivalOnlyResult(Route((), (), 250), exact=True))


class BudgetTest(unittest.TestCase):
    def test_a_budget_spent_before_the_destination_pops_is_inexact(self):
        graph = Graph(LOOP + DETOUR)
        rule = closure(A_TO_D_OPENS_AT_900, steps=(0, 900))
        self.assertEqual(earliest_arrival_arrival_only(graph, O, D, rule, 0, max_expansions=1), ArrivalOnlyResult(None, exact=False))
        self.assertEqual(
            earliest_arrival_arrival_only(graph, O, D, rule, 0, max_expansions=3),
            ArrivalOnlyResult(Route((3, 4), (0, 1000), 1600), exact=True),
        )


if __name__ == "__main__":
    unittest.main()
