import unittest
from datetime import datetime, timezone

from stale_run import age_minutes, is_stale, limit_minutes, message

SLOT = datetime(2026, 10, 13, 3, 0, tzinfo=timezone.utc)


def at(hour, minute):
    return datetime(2026, 10, 13, hour, minute, tzinfo=timezone.utc)


class LimitMinutesTests(unittest.TestCase):
    def test_default_is_two_hours(self):
        self.assertEqual(limit_minutes({}), 120)

    def test_zero_turns_the_guard_off(self):
        self.assertEqual(limit_minutes({"FLOOD_STALE_RUN_MINUTES": "0"}), 0)

    def test_a_whole_number_is_read(self):
        self.assertEqual(limit_minutes({"FLOOD_STALE_RUN_MINUTES": " 45 "}), 45)

    def test_anything_else_raises_and_names_the_variable(self):
        for raw in ("", "abc", "1.5", "-1", "2h", "1e2"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "FLOOD_STALE_RUN_MINUTES"):
                    limit_minutes({"FLOOD_STALE_RUN_MINUTES": raw})


class IsStaleTests(unittest.TestCase):
    def test_exactly_at_the_limit_is_not_stale(self):
        self.assertIs(is_stale(SLOT, at(5, 0), 120), False)

    def test_one_minute_over_is_stale(self):
        self.assertIs(is_stale(SLOT, at(5, 1), 120), True)

    def test_limit_zero_is_never_stale(self):
        self.assertIs(is_stale(SLOT, at(23, 0), 0), False)

    def test_age_is_in_minutes(self):
        self.assertEqual(age_minutes(SLOT, at(6, 0)), 180.0)


class MessageTests(unittest.TestCase):
    def test_names_the_slot_the_age_and_the_limit(self):
        self.assertEqual(
            message(SLOT, at(6, 0), 120),
            "Run slot 2026-10-13T03:00:00Z is 180 minutes old, over the limit of 120 minutes "
            "(FLOOD_STALE_RUN_MINUTES). Skipping so an old run does no work.",
        )


if __name__ == "__main__":
    unittest.main()
