import contextlib
import io
import json
import unittest
from datetime import datetime, timedelta, timezone

import table_timing as tt

T0 = datetime(2026, 10, 5, 15, 15, tzinfo=timezone.utc)
SEP = "~"


def iso(moment):
    return "" if moment is None else moment.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def line(slot=T0, calc_end=60, tiles_start=61, tiles_end=200, state="success", c_start=65, c_end=110, report="default"):
    """One line of the query output. Times are seconds after the slot. Report 'default' is a real-looking report."""
    def at(seconds):
        return None if seconds is None else slot + timedelta(seconds=seconds)

    if report == "default":
        report = {"run_ts": "20261005T221500", "edge_count": 67833, "steps": 8, "bytes": 1085487, "seconds": 42.0,
                  "wet_edges": [992, 1040, 1100, 1180, 1200, 1210, 1190, 1150]}
    fields = [f"run_{iso(slot)[11:16]}", iso(slot), iso(at(calc_end)), iso(at(tiles_start)), iso(at(tiles_end)), state or "",
              iso(at(c_start)), iso(at(c_end)), "" if report is None else json.dumps(report)]
    return SEP.join(fields)


def analyse(*lines, limit_s=300):
    return tt.analyse(tt.parse_lines("\n".join(lines) + "\n"), limit_s=limit_s)


class ParseTest(unittest.TestCase):
    def test_a_full_line(self):
        row = tt.parse_lines(line() + "\n")[0]
        self.assertEqual(row.logical_date, T0)
        self.assertEqual(row.calc_end, T0 + timedelta(seconds=60))
        self.assertEqual(row.c_state, "success")
        self.assertEqual(row.report["edge_count"], 67833)

    def test_a_dry_cycle_line_has_empty_fields(self):
        row = tt.parse_lines(f"run_x{SEP}{iso(T0)}{SEP * 7}\n")[0]
        self.assertIsNone(row.calc_end)
        self.assertIsNone(row.c_state)
        self.assertIsNone(row.report)

    def test_a_line_that_is_not_a_row_is_refused_with_the_line(self):
        with self.assertRaises(ValueError) as caught:
            tt.parse_lines("Error response from daemon: no such container\n")
        self.assertIn("Error response from daemon", str(caught.exception))

    def test_a_json_string_that_wraps_the_report_is_unwrapped(self):
        wrapped = json.dumps(json.dumps({"edge_count": 5}))
        row = tt.parse_lines(line(report=None).rsplit(SEP, 1)[0] + SEP + wrapped + "\n")[0]
        self.assertEqual(row.report, {"edge_count": 5})


class RunTest(unittest.TestCase):
    def test_the_time_after_the_depth_task_is_the_end_of_9c_minus_the_end_of_3(self):
        result = analyse(line(calc_end=60, c_end=110))
        self.assertAlmostEqual(result.runs[0].after_calc_s, 50.0)
        self.assertFalse(result.runs[0].over_limit)

    def test_a_run_over_the_limit_is_flagged(self):
        result = analyse(line(calc_end=60, c_end=60 + 301), limit_s=300)
        self.assertTrue(result.runs[0].over_limit)
        self.assertEqual(result.exit_code, 1)

    def test_exactly_at_the_limit_passes(self):
        self.assertFalse(analyse(line(calc_end=60, c_end=360), limit_s=300).runs[0].over_limit)

    def test_the_task_duration_is_end_minus_start(self):
        self.assertAlmostEqual(analyse(line(c_start=65, c_end=110)).runs[0].task_s, 45.0)

    def test_the_report_numbers_come_from_the_xcom(self):
        run = analyse(line()).runs[0]
        self.assertEqual((run.edge_count, run.size_bytes, run.wet_max), (67833, 1085487, 1210))


class DelayTest(unittest.TestCase):
    def test_a_table_task_that_starts_after_the_tile_task_started_delays_nothing(self):
        # The tile task waited for 9b (60 to 100) and started at 100. 9c ran 105 to 150.
        run = analyse(line(calc_end=60, tiles_start=100, c_start=105, c_end=150)).runs[0]
        self.assertFalse(run.delayed_tiles)
        self.assertAlmostEqual(run.tile_wait_s, 40.0)

    def test_a_table_task_that_ran_while_the_tile_task_waited_is_a_delay_even_when_it_ended_first(self):
        # Ready at 60, 9c ran 65 to 90, tiles started at 95.
        self.assertTrue(analyse(line(calc_end=60, tiles_start=95, c_start=65, c_end=90)).runs[0].delayed_tiles)

    def test_a_table_task_that_holds_the_worker_while_the_tile_task_waits_is_a_delay(self):
        # The tile task became ready at 60 and started at 100, and 9c ran from 65 to 105.
        run = analyse(line(calc_end=60, tiles_start=100, c_start=65, c_end=105)).runs[0]
        self.assertTrue(run.delayed_tiles)
        self.assertAlmostEqual(run.tile_wait_s, 40.0)

    def test_running_at_the_same_time_as_the_tile_task_is_not_a_delay(self):
        # Tiles started at 61 (no wait), and 9c ran from 65 to 200 beside it.
        self.assertFalse(analyse(line(calc_end=60, tiles_start=61, tiles_end=220, c_start=65, c_end=200)).runs[0].delayed_tiles)

    def test_a_delay_fails_the_report(self):
        self.assertEqual(analyse(line(calc_end=60, tiles_start=100, c_start=65, c_end=105)).exit_code, 1)


class StateTest(unittest.TestCase):
    def test_a_dry_cycle_is_skipped_and_not_counted_as_a_failure(self):
        dry = f"run_x{SEP}{iso(T0)}{SEP * 7}"
        result = analyse(dry, line(slot=T0 + timedelta(minutes=15)))
        self.assertEqual((result.skipped, len(result.runs), result.failed), (1, 1, 0))
        self.assertEqual(result.exit_code, 0)

    def test_a_failed_table_task_fails_the_report_and_is_listed(self):
        result = analyse(line(state="failed", c_end=None, report=None), line(slot=T0 + timedelta(minutes=15)))
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.exit_code, 1)

    def test_an_upstream_failed_table_task_counts_as_failed(self):
        self.assertEqual(analyse(line(state="upstream_failed", c_start=None, c_end=None, report=None)).failed, 1)

    def test_a_task_still_running_is_pending_and_does_not_decide_the_report(self):
        result = analyse(line(state="running", c_end=None, report=None), line(slot=T0 + timedelta(minutes=15)))
        self.assertEqual((result.pending, result.failed), (1, 0))
        self.assertEqual(result.exit_code, 0)

    def test_a_task_with_no_state_yet_after_the_depth_task_is_pending(self):
        self.assertEqual(analyse(line(state=None, c_start=None, c_end=None, report=None), line(slot=T0 + timedelta(minutes=15))).pending, 1)

    def test_no_run_at_all_is_not_a_pass(self):
        self.assertEqual(tt.analyse([]).exit_code, 1)

    def test_only_dry_cycles_is_not_a_pass(self):
        self.assertEqual(analyse(f"run_x{SEP}{iso(T0)}{SEP * 7}").exit_code, 1)


class SummaryTest(unittest.TestCase):
    def test_worst_median_and_best(self):
        result = analyse(*[line(slot=T0 + timedelta(minutes=15 * i), calc_end=60, c_end=60 + s) for i, s in enumerate([30, 50, 90])])
        self.assertEqual((result.worst_s, result.median_s, result.best_s), (90.0, 50.0, 30.0))

    def test_the_report_names_the_runs_and_the_verdict(self):
        out = tt.render(analyse(line(), line(slot=T0 + timedelta(minutes=15), calc_end=60, c_end=60 + 400)), limit_s=300)
        self.assertIn("22:15", out)  # the slot in +07
        self.assertIn("OVER", out)
        self.assertIn("FAIL", out)

    def test_a_clean_report_says_pass(self):
        self.assertIn("PASS", tt.render(analyse(line()), limit_s=300))


class MainTest(unittest.TestCase):
    def test_main_reads_stdin_and_returns_the_exit_code(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tt.main(["--limit-minutes", "5"], stdin=io.StringIO(line() + "\n"))
        self.assertEqual(code, 0)
        self.assertIn("PASS", out.getvalue())

    def test_main_returns_one_on_a_bad_line_and_names_it(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tt.main([], stdin=io.StringIO("no such container\n"))
        self.assertEqual(code, 1)
        self.assertIn("no such container", out.getvalue())


if __name__ == "__main__":
    unittest.main()
