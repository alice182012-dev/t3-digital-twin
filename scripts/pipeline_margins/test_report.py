import contextlib
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import report

ROWS = """10-02 00:45 3.5 3.2 1.6 4.4 1.9
10-02 01:00 3.4 3.5 1.7 5.0 4.1
10-02 01:15 3.6 3.9 1.7 5.6 2.7
10-02 01:30 3.5 3.4 1.8 6.1 2.4
"""
SLOTS = ["10-02 00:45", "10-02 01:00", "10-02 01:15", "10-02 01:30"]


def row(slot, margin):
    return report.Row(slot, None if margin is None else 1.0, 1.0, 1.0, 1.0, margin)


class ParseRowsTest(unittest.TestCase):
    def test_a_full_row_and_a_dry_cycle_row_with_empty_fields(self):
        rows = report.parse_rows("10-02 00:45 3.5 3.2 1.6 4.4 1.9\n10-02 01:00     \n")
        self.assertEqual(rows[0], report.Row("10-02 00:45", 3.5, 3.2, 1.6, 4.4, 1.9))
        self.assertEqual(rows[1], report.Row("10-02 01:00", None, None, None, None, None))

    def test_a_line_that_is_not_a_row_is_refused_with_the_line(self):
        with self.assertRaises(ValueError) as caught:
            report.parse_rows("request returned 500 Internal Server Error for API route\n")
        self.assertIn("request returned 500", str(caught.exception))

    def test_a_negative_margin_and_blank_lines(self):
        rows = report.parse_rows("\n10-02 00:45 3.5 3.2 1.6 4.4 -1.2\n\n")
        self.assertEqual([r.margin for r in rows], [-1.2])


class JudgeTest(unittest.TestCase):
    def test_the_four_runs_of_2026_10_02_pass_with_their_margins(self):
        result = report.judge(report.parse_rows(ROWS))
        self.assertEqual((result.worst, result.best), (1.9, 4.1))
        self.assertEqual(result.median, 2.55)
        self.assertEqual((result.late, result.missing, result.passed), ([], [], True))
        self.assertEqual(result.worst_slot, "10-02 00:45")

    def test_a_run_with_a_margin_below_the_minimum_is_late_and_fails(self):
        result = report.judge([row("10-02 00:45", 2.0), row("10-02 01:00", -0.4)])
        self.assertEqual([r.slot for r in result.late], ["10-02 01:00"])
        self.assertFalse(result.passed)

    def test_a_margin_of_exactly_zero_passes_the_default_minimum_and_fails_a_higher_one(self):
        self.assertTrue(report.judge([row("10-02 00:45", 0.0)]).passed)
        self.assertFalse(report.judge([row("10-02 00:45", 0.5)], min_margin=1.0).passed)

    def test_an_expected_run_with_no_row_or_no_margin_is_missing(self):
        rows = [row(SLOTS[0], 2.0), row(SLOTS[2], None), row(SLOTS[3], 1.0)]
        result = report.judge(rows, expected=SLOTS)
        self.assertEqual(result.missing, [SLOTS[1], SLOTS[2]])
        self.assertFalse(result.passed)

    def test_expected_runs_after_the_last_row_are_not_judged_yet(self):
        result = report.judge([row(SLOTS[0], 2.0), row(SLOTS[1], 3.0)], expected=SLOTS)
        self.assertEqual(result.missing, [])
        self.assertTrue(result.passed)

    def test_since_and_until_limit_the_expected_runs(self):
        rows = [row(SLOTS[2], 2.0)]
        result = report.judge(rows, expected=SLOTS, since=SLOTS[2], until=SLOTS[3])
        self.assertEqual(result.missing, [SLOTS[3]])

    def test_since_and_until_also_limit_the_margins_and_the_late_runs(self):
        rows = [row(SLOTS[0], -5.0), row(SLOTS[1], 2.0), row(SLOTS[2], 3.0), row(SLOTS[3], -4.0)]
        result = report.judge(rows, since=SLOTS[1], until=SLOTS[2])
        self.assertEqual(result.margins, [2.0, 3.0])
        self.assertEqual((result.late, result.passed), ([], True))

    def test_dry_cycle_rows_that_are_not_expected_to_simulate_do_not_count(self):
        rows = [row(SLOTS[0], 2.0), row(SLOTS[1], None), row(SLOTS[2], 3.0)]
        result = report.judge(rows, expected=[SLOTS[0], SLOTS[2]])
        self.assertEqual((result.missing, result.passed, len(result.margins)), ([], True, 2))

    def test_no_rows_with_a_margin_fails(self):
        self.assertFalse(report.judge([]).passed)
        self.assertFalse(report.judge([row(SLOTS[0], None)]).passed)


class TrendTest(unittest.TestCase):
    def test_a_margin_that_falls_one_minute_per_run_reaches_zero_after_the_last_run(self):
        rows = [row(s, m) for s, m in zip(SLOTS, [4.0, 3.0, 2.0, 1.0])]
        trend = report.judge(rows).trends[0]
        self.assertEqual((trend.first_slot, trend.last_slot, trend.runs), (SLOTS[0], SLOTS[3], 4))
        self.assertAlmostEqual(trend.slope, -1.0)
        self.assertAlmostEqual(trend.runs_to_zero, 1.0)

    def test_a_flat_or_rising_margin_never_reaches_zero(self):
        rows = [row(s, m) for s, m in zip(SLOTS, [1.0, 1.0, 1.0, 1.0])]
        self.assertIsNone(report.judge(rows).trends[0].runs_to_zero)

    def test_a_gap_in_the_slots_starts_a_new_chain(self):
        slots = ["10-02 00:00", "10-02 00:15", "10-02 00:30", "10-02 02:00", "10-02 02:15", "10-02 02:30"]
        rows = [row(s, m) for s, m in zip(slots, [3, 2, 1, 5, 4, 3])]
        trends = report.judge(rows).trends
        self.assertEqual([(t.first_slot, t.runs) for t in trends], [("10-02 00:00", 3), ("10-02 02:00", 3)])

    def test_a_chain_of_fewer_than_three_runs_has_no_slope(self):
        trend = report.judge([row(SLOTS[0], 2.0), row(SLOTS[1], 1.0)]).trends[0]
        self.assertIsNone(trend.slope)


class ExpectedFromEventTest(unittest.TestCase):
    EVENT = [(0, 0.0), (30, 6.0), (60, 0.0), (90, 0.0), (120, 0.0), (150, 0.0), (180, 6.0), (210, 0.0)]

    def test_expected_slots_are_the_simulating_slots_in_local_time(self):
        start = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)
        slots = report.expected_slots(self.EVENT, start, 5.0, hours=3, lookahead_hours=0.5)
        self.assertEqual(
            slots,
            ["10-02 16:00", "10-02 16:15", "10-02 16:30", "10-02 16:45", "10-02 18:30", "10-02 18:45"],
        )


class RenderAndMainTest(unittest.TestCase):
    def test_the_report_text_for_the_four_runs(self):
        text = report.render(report.judge(report.parse_rows(ROWS)), min_margin=0.0)
        self.assertEqual(
            text,
            "\n".join(
                [
                    "runs with a margin: 4",
                    "margin to the end of the tile task in minutes: worst +1.9 at 10-02 00:45, median +2.5, best +4.1",
                    "late runs (margin below 0.0): none",
                    "missing runs: none",
                    "chain 1: 10-02 00:45 to 10-02 01:30, 4 runs, margin slope +0.01 minutes per run, last margin +2.4",
                    "verdict: PASS",
                ]
            ),
        )

    def run_main(self, text, *args):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rows.txt"
            path.write_text(text)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = report.main([*args, str(path)])
        return code, out.getvalue()

    def test_exit_code_is_0_for_a_pass_and_1_for_a_late_run(self):
        self.assertEqual(self.run_main(ROWS)[0], 0)
        late = ROWS + "10-02 01:45 3.5 3.4 1.8 6.1 -0.3\n"
        code, out = self.run_main(late)
        self.assertEqual(code, 1)
        self.assertIn("verdict: FAIL", out)

    def test_unreadable_input_exits_with_1_and_says_why(self):
        code, out = self.run_main("request returned 500 Internal Server Error\n")
        self.assertEqual(code, 1)
        self.assertIn("cannot read", out)

    def test_the_event_arguments_add_the_missing_run_check(self):
        event = Path(report.__file__).resolve().parents[1] / "rain_events" / "hanoi_20251005_48h.csv"
        rows = "10-02 16:00 3 3 1 5 2.0\n10-02 16:30 3 3 1 5 2.0\n"
        code, out = self.run_main(rows, "--event", str(event), "--start", "2026-10-02T09:00:00Z", "--threshold", "0.01")
        self.assertEqual(code, 1)
        self.assertIn("missing runs: 10-02 16:15", out)


if __name__ == "__main__":
    unittest.main()
