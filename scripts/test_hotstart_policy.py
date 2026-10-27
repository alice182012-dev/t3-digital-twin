import unittest

from hotstart_policy import should_hotstart


class ShouldHotstartTests(unittest.TestCase):
    def test_no_previous_slot_run_forces_cold_start(self):
        self.assertIs(should_hotstart(0), False)

    def test_one_previous_slot_run_allows_hotstart(self):
        self.assertIs(should_hotstart(1), True)

    def test_rule_off_allows_hotstart_without_previous_run(self):
        self.assertIs(should_hotstart(0, enabled=False), True)


if __name__ == "__main__":
    unittest.main()
