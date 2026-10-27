import unittest

from sampling import BORDER, LENGTH_CLASSES, Pair, distance_m, length_class, sample_pairs


class LengthClassTest(unittest.TestCase):
    def test_the_classes_split_at_2_and_5_km(self):
        self.assertEqual(
            [length_class(m) for m in (0.0, 1999.9, 2000.0, 5000.0, 5000.1, 11000.0)],
            ["under_2km", "under_2km", "2_to_5km", "2_to_5km", "over_5km", "over_5km"],
        )

    def test_the_known_short_trip_is_about_730_m(self):
        self.assertAlmostEqual(distance_m((105.7550, 21.0250), (105.7620, 21.0255)), 729, delta=2)


class SampleTest(unittest.TestCase):
    def test_every_class_gets_its_count_and_every_point_is_inside_the_border(self):
        pairs = sample_pairs(per_class=20, seed=7)
        self.assertEqual([p.length_class for p in pairs].count("under_2km"), 20)
        self.assertEqual([p.length_class for p in pairs].count("2_to_5km"), 20)
        self.assertEqual([p.length_class for p in pairs].count("over_5km"), 20)
        for p in pairs:
            for lon, lat in (p.origin, p.destination):
                self.assertTrue(105.7015 <= lon <= 105.7971 and 20.9754 <= lat <= 21.0269, p)
            self.assertEqual(length_class(distance_m(p.origin, p.destination)), p.length_class)

    def test_the_same_seed_gives_the_same_pairs(self):
        self.assertEqual(sample_pairs(per_class=3, seed=11), sample_pairs(per_class=3, seed=11))
        self.assertNotEqual(sample_pairs(per_class=3, seed=11), sample_pairs(per_class=3, seed=12))

    def test_pair_names_carry_the_class_and_a_number(self):
        names = [p.name for p in sample_pairs(per_class=2, seed=1)]
        self.assertEqual(names, ["under_2km-0", "under_2km-1", "2_to_5km-0", "2_to_5km-1", "over_5km-0", "over_5km-1"])

    def test_the_border_is_the_model_border(self):
        self.assertEqual((BORDER.lon_min, BORDER.lon_max, BORDER.lat_min, BORDER.lat_max), (105.7015, 105.7971, 20.9754, 21.0269))
        self.assertEqual(LENGTH_CLASSES, ("under_2km", "2_to_5km", "over_5km"))

    def test_a_pair_round_trips_through_json(self):
        p = Pair("x-0", "under_2km", (105.75, 21.0), (105.76, 21.0))
        self.assertEqual(Pair.from_json(p.to_json()), p)


if __name__ == "__main__":
    unittest.main()
