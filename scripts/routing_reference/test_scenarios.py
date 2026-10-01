import importlib.util
import unittest
from pathlib import Path

from corridor import RoadNetwork, Way
from scenarios import SCENARIOS, STEP_SECONDS, VEHICLE_LIMIT_CM, run_scenario, scenario_depth_cm

X = [105.7550 + 0.0008 * i for i in range(7)]  # about 83 m apart
LAT = 21.0250


def mini_network():
    """A main road of six pieces with two detours: x1 to x5 above it, and x4 to x6 below it."""
    main = [Way(f"way/{i}", ((X[i], LAT), (X[i + 1], LAT))) for i in range(6)]
    above = Way("way/20", ((X[1], LAT), (X[1], 21.0258), (X[5], 21.0258), (X[5], LAT)))
    below = Way("way/21", ((X[4], LAT), (X[4], 21.0242), (X[6], 21.0242), (X[6], LAT)))
    return RoadNetwork.from_ways(main + [above, below])


class ScenarioDepthTest(unittest.TestCase):
    def series(self, name):
        scenario = next(s for s in SCENARIOS if s.name.startswith(name))
        return [scenario_depth_cm(scenario, step, flood_cm=50) for step in range(8)]

    def test_rises_before_arrival_is_dry_at_step_0_and_flooded_from_minute_10(self):
        self.assertEqual(self.series("1."), [0, 50, 50, 50, 50, 50, 50, 50])

    def test_rises_after_passing_is_dry_until_minute_45(self):
        self.assertEqual(self.series("2."), [0, 0, 0, 50, 50, 50, 50, 50])

    def test_flooded_and_drains_is_flooded_from_minute_0_to_20(self):
        self.assertEqual(self.series("3."), [50, 50, 0, 0, 0, 0, 0, 0])

    def test_far_road_floods_from_minute_45(self):
        self.assertEqual(self.series("4."), [0, 0, 0, 50, 50, 50, 50, 50])


class RunScenarioTest(unittest.TestCase):
    def setUp(self):
        self.net = mini_network()
        self.origin = self.net.nearest_node(X[0], LAT)
        self.destination = self.net.nearest_node(X[6], LAT)

    def run_one(self, scenario, limit_cm=20, with_detour=True, flood_cm=50):
        return run_scenario(self.net, self.origin, self.destination, scenario, limit_cm, with_detour, flood_cm)

    def test_every_scenario_matches_the_sticky_column_for_each_vehicle_with_and_without_a_detour(self):
        for scenario in SCENARIOS:
            for vehicle, limit in VEHICLE_LIMIT_CM.items():
                for with_detour in (True, False):
                    with self.subTest(scenario=scenario.name, vehicle=vehicle, detour=with_detour):
                        outcome = self.run_one(scenario, limit, with_detour)
                        if not scenario.blocked:
                            self.assertTrue(outcome.uses_corridor)
                        elif with_detour:
                            self.assertIsNotNone(outcome.route)
                            self.assertFalse(outcome.uses_corridor)
                        else:
                            self.assertIsNone(outcome.route)
                        self.assertTrue(outcome.matches_sticky_column)

    def test_a_returned_route_never_crosses_a_closed_edge(self):
        for scenario in SCENARIOS:
            for with_detour in (True, False):
                with self.subTest(scenario=scenario.name, detour=with_detour):
                    self.assertEqual(self.run_one(scenario, with_detour=with_detour).crossings, [])

    def test_the_plain_shortest_route_crosses_a_closed_edge_exactly_when_the_scenario_blocks(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                crossings = self.run_one(scenario).static_crossings
                self.assertEqual(bool(crossings), scenario.blocked)

    def test_the_traveller_reaches_the_corridor_at_the_scenario_minute(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                self.assertAlmostEqual(self.run_one(scenario).corridor_arrival_s, scenario.arrival_min * 60, places=6)

    def test_the_corridor_road_is_the_one_entered_at_half_or_nine_tenths_of_the_route(self):
        middle = next(s for s in SCENARIOS if s.corridor == "middle")
        far = next(s for s in SCENARIOS if s.corridor == "far")

        self.assertEqual(self.run_one(middle).corridor_way_id, "way/3")
        self.assertEqual(self.run_one(far).corridor_way_id, "way/5")
        self.assertEqual(self.run_one(middle).path_edges, 6)

    def test_the_far_corridor_is_nearer_the_destination_than_the_middle_one(self):
        middle = next(s for s in SCENARIOS if s.corridor == "middle")
        far = next(s for s in SCENARIOS if s.corridor == "far")

        self.assertLess(self.run_one(middle).corridor_position, self.run_one(far).corridor_position)

    def test_a_shallow_flood_blocks_the_motorbike_but_not_the_car(self):
        rises_before_arrival = SCENARIOS[0]

        motorbike = self.run_one(rises_before_arrival, limit_cm=VEHICLE_LIMIT_CM["motorbike"], flood_cm=25)
        car = self.run_one(rises_before_arrival, limit_cm=VEHICLE_LIMIT_CM["car"], flood_cm=25)

        self.assertFalse(motorbike.uses_corridor)
        self.assertTrue(car.uses_corridor)

    def test_a_route_too_short_to_hold_a_corridor_is_refused(self):
        short = RoadNetwork.from_ways([Way("way/1", ((X[0], LAT), (X[1], LAT))), Way("way/2", ((X[1], LAT), (X[2], LAT)))])

        with self.assertRaisesRegex(ValueError, "at least 3 edges"):
            run_scenario(short, short.nearest_node(X[0], LAT), short.nearest_node(X[2], LAT), SCENARIOS[0], 20, True)

    def test_an_unreachable_destination_is_refused(self):
        island = RoadNetwork.from_ways(
            [Way("way/1", ((X[0], LAT), (X[1], LAT))), Way("way/2", ((105.80, LAT), (105.801, LAT)))]
        )

        with self.assertRaisesRegex(ValueError, "no route"):
            run_scenario(island, island.nearest_node(X[0], LAT), island.nearest_node(105.801, LAT), SCENARIOS[0], 20, True)


class VehicleLimitTest(unittest.TestCase):
    def test_limits_equal_the_backends_thresholds(self):
        path = Path(__file__).resolve().parents[2] / "floodmap/graphhopper-flood-road/scripts/flood_utils.py"
        spec = importlib.util.spec_from_file_location("flood_utils_under_test", path)
        flood_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flood_utils)

        self.assertEqual(
            {vehicle: flood_utils.vehicle_threshold_cm(vehicle) for vehicle in VEHICLE_LIMIT_CM}, VEHICLE_LIMIT_CM
        )

    def test_steps_are_the_8_steps_of_15_minutes_that_a_real_run_has(self):
        self.assertEqual(STEP_SECONDS, tuple(900 * k for k in range(8)))


if __name__ == "__main__":
    unittest.main()
