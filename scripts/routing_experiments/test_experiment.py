import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import experiment as ex
import golden_fixture
import sticky_reference as ref
from planner import PlanFailure, PlannedRoute
from rewalk import Route, SlowDown
from sampling import Pair

LIMITS = {"car": 250, "foot": 300}
P_SHORT_A = Pair("under_2km-0", "under_2km", (105.75, 21.0), (105.76, 21.0))
P_SHORT_B = Pair("under_2km-1", "under_2km", (105.75, 21.01), (105.76, 21.01))
P_LONG = Pair("over_5km-0", "over_5km", (105.71, 20.98), (105.79, 21.02))

# Path A: edge 0 then edge 2, entering edge 2 at 1,900 s when it holds 255 cm. Path B: edges 3 and 4, both shallow.
PATH_A = Route((0, 2), (1000.0, 100.0))
PATH_B = Route((3, 4), (1000.0, 1000.0))


def planned(route, engine=None):
    return PlannedRoute(route, tuple(10.0 for _ in route.edge_ids), 10.0 * len(route.edge_ids), engine or {})


def single_timestep_planner(request):
    if request.pair is P_LONG:
        return PlanFailure(400, "Cannot find point 0: 20.98,105.71")
    return planned(PATH_A if request.pair is P_SHORT_A else PATH_B)


class GoldenTables:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "20261001T000000.bin"
        path.write_bytes(golden_fixture.build()[0])
        return ex.TableSet.load("end of storm", [path])

    def __exit__(self, *exc):
        self._tmp.cleanup()


def run(table_set, planner=single_timestep_planner, model="single_timestep", slowdown=None, pairs=None, steps=(1,)):
    return ex.run_experiment(model=model, storm="golden fixture", pairs=pairs or [P_SHORT_A, P_SHORT_B, P_LONG],
                             table_sets=[table_set], limits=LIMITS, planner=planner, departure_steps=steps, slowdown=slowdown)


def row(result, **key):
    matches = [r for r in result["summary"] if all(r[k] == v for k, v in key.items())]
    assert len(matches) == 1, (key, matches)
    return matches[0]


class SummaryTest(unittest.TestCase):
    def test_one_of_two_car_routes_violates_and_the_severity_is_its_own(self):
        with GoldenTables() as tables:
            result = run(tables)
        r = row(result, vehicle="car", length_class="under_2km", departure_step=1, rule="at_or_before")
        self.assertEqual(
            {k: r[k] for k in ("storm", "stage", "routes", "violating_routes", "violation_rate", "worst_over_limit_cm_max",
                               "violating_edges_mean", "first_violation_s_median", "dropped_cannot_find_point", "no_route")},
            {"storm": "golden fixture", "stage": "end of storm", "routes": 2, "violating_routes": 1, "violation_rate": 0.5,
             "worst_over_limit_cm_max": 5, "violating_edges_mean": 1.0, "first_violation_s_median": 1000.0,
             "dropped_cannot_find_point": 0, "no_route": 0},
        )
        self.assertEqual(row(result, vehicle="car", length_class="under_2km", rule="worse_of_two")["worst_over_limit_cm_max"], 6)

    def test_the_higher_limit_of_foot_sees_no_violation(self):
        with GoldenTables() as tables:
            result = run(tables)
        for rule in ("at_or_before", "nearest", "worse_of_two"):
            self.assertEqual(row(result, vehicle="foot", length_class="under_2km", rule=rule)["violating_routes"], 0)

    def test_a_pair_that_cannot_be_snapped_is_dropped_and_counted(self):
        with GoldenTables() as tables:
            result = run(tables)
        r = row(result, vehicle="car", length_class="over_5km", rule="at_or_before")
        self.assertEqual((r["routes"], r["dropped_cannot_find_point"], r["violation_rate"]), (0, 1, None))

    def test_every_rule_appears_for_every_group(self):
        with GoldenTables() as tables:
            result = run(tables)
        self.assertEqual(len(result["summary"]), 2 * 2 * 1 * 3)  # vehicles, classes, departure steps, rules

    def test_the_departure_is_the_step_the_route_was_planned_on(self):
        requests = []

        def planner(request):
            requests.append((request.vehicle, request.valid_time, request.run))
            return planned(PATH_B)

        with GoldenTables() as tables:
            run(tables, planner=planner, pairs=[P_SHORT_A], steps=(1, 2))
        self.assertEqual(requests, [
            ("car", "2026-10-01T00:15:00+00:00", "20261001T000000"), ("car", "2026-10-01T00:30:00+00:00", "20261001T000000"),
            ("foot", "2026-10-01T00:15:00+00:00", "20261001T000000"), ("foot", "2026-10-01T00:30:00+00:00", "20261001T000000")])


class StickyEngineTest(unittest.TestCase):
    """The reference sticky search plans on the same pairs. Its routes must not meet a closed road."""

    def sticky_planner(self, table):
        graph = ref.Graph([ref.Edge(0, 0, 2, 1000.0), ref.Edge(2, 2, 1, 100.0), ref.Edge(3, 0, 3, 1000.0), ref.Edge(4, 3, 1, 1000.0)])
        steps = tuple(t.timestamp() for t in table.header.step_times)

        def plan(request):
            departure = datetime.fromisoformat(request.valid_time).timestamp()
            rule = ref.StickyClosure(steps, table.depth_cm, LIMITS[request.vehicle], departure_s=departure)
            found = ref.earliest_arrival(graph, 0, 1, rule)
            seconds = tuple(graph.edge(e).seconds for e in found.edge_ids)
            return planned(Route(found.edge_ids, seconds), {"status": "applied", "departure": departure})

        return plan

    def test_the_sticky_routes_pass_the_check(self):
        with GoldenTables() as tables:
            result = run(tables, planner=self.sticky_planner(tables.tables[0]), model="sticky", pairs=[P_SHORT_A])
        self.assertEqual(result["sticky_check"], {
            "routes": 2, "sticky_crossings": 0,
            "violations_by_rule": {"at_or_before": 0, "nearest": 0, "worse_of_two": 0},
            "rules_the_margin_covers": ["at_or_before", "nearest"], "passed": True})
        self.assertEqual(result["model_check"], {"routes": 2, "not_this_model": 0})

    def test_the_single_timestep_routes_fail_the_check(self):
        with GoldenTables() as tables:
            check = run(tables, pairs=[P_SHORT_A])["sticky_check"]
        self.assertEqual((check["sticky_crossings"], check["violations_by_rule"]["at_or_before"], check["passed"]), (1, 1, False))

    def test_a_route_from_the_engine_in_a_single_timestep_run_is_counted(self):
        with GoldenTables() as tables:
            result = run(tables, planner=lambda r: planned(PATH_B, {"status": "applied"}), pairs=[P_SHORT_A])
        self.assertEqual(result["model_check"], {"routes": 2, "not_this_model": 2})


class SensitivityTest(unittest.TestCase):
    def test_slowing_deep_edges_is_labelled_and_changes_the_rate(self):
        slow_route = Route((29, 2), (1000.0, 600.0))
        with GoldenTables() as tables:
            free = run(tables, planner=lambda r: planned(slow_route), pairs=[P_SHORT_A], steps=(0,))
            slowed = run(tables, planner=lambda r: planned(slow_route), pairs=[P_SHORT_A], steps=(0,),
                         slowdown=SlowDown(min_depth_cm=200, factor=2.0))
        self.assertEqual(free["case"], "free flow")
        self.assertEqual(slowed["case"], "sensitivity: edges at 200 cm or deeper take 2 times their free-flow time")
        key = dict(vehicle="car", length_class="under_2km", rule="at_or_before")
        self.assertEqual((row(free, **key)["violation_rate"], row(slowed, **key)["violation_rate"]), (0.0, 1.0))


class ResultFileTest(unittest.TestCase):
    def test_the_file_names_the_runs_it_read_and_the_labels(self):
        with GoldenTables() as tables, tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "result.json"
            ex.write_result(out, run(tables))
            data = json.loads(out.read_text())
        self.assertEqual(data["table_sets"], [{"stage": "end of storm", "runs": ["20261001T000000"],
                                               "graph_hashes": [golden_fixture.GRAPH_HASH]}])
        self.assertEqual((data["story"], data["model"], data["storm"], data["vehicles"]),
                         ("US-091", "single_timestep", "golden fixture", {"car": 250, "foot": 300}))
        self.assertEqual(data["rules"], ["at_or_before", "nearest", "worse_of_two"])
        self.assertEqual(len(data["routes"]), 6)
        self.assertEqual(data["routes"][0]["walks"]["at_or_before"]["violations"],
                         [{"position": 1, "edge_id": 2, "arrival_s": 1790814700.0, "step": 2, "depth_cm": 255}])


class VehicleLimitTest(unittest.TestCase):
    def test_the_limits_come_from_vehicle_profiles(self):
        self.assertEqual(ex.vehicle_limits(), {"motorbike": 20, "car": 30, "truck": 35, "foot": 40})


class DepartureStepsTest(unittest.TestCase):
    def test_the_default_is_every_step_but_the_last(self):
        with GoldenTables() as tables:
            self.assertEqual(ex.default_departure_steps([tables]), (0, 1, 2, 3, 4, 5, 6, 7))


if __name__ == "__main__":
    unittest.main()
