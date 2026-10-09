import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import edge_depth_table
import gap_continuity
from edge_depth_table import TableHeader, write_table

START = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def write_run(directory: Path, name: str, offset_slots: int, depths_by_edge: list) -> None:
    steps = tuple(START + timedelta(minutes=15 * (offset_slots + i)) for i in range(len(depths_by_edge[0])))
    header = TableHeader(graph_hash="g", run_name=name, step_times=steps, edge_count=len(depths_by_edge))
    write_table(directory / f"{name}.bin", header, depths_by_edge)


class ContinuityTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def run_main(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = gap_continuity.main([str(self.dir), *args])
        return code, out.getvalue(), err.getvalue()

    def test_a_kept_flood_is_inside_the_band(self):
        # run A forecasts 4 wet edges at its second step. Run B starts at that step with 4 wet edges.
        write_run(self.dir, "A", 0, [[0, 5], [0, 7], [2, 9], [0, 3], [0, 0]])
        write_run(self.dir, "B", 1, [[5, 1], [7, 0], [9, 0], [3, 0], [0, 0]])
        code, stdout, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("B  wet      4  forecast by A      4  ratio  1.00  ok", stdout)
        self.assertIn("1 of 1 runs inside the band", stdout)

    def test_a_lost_flood_is_outside_the_band(self):
        write_run(self.dir, "A", 0, [[0, 5], [0, 7], [2, 9], [0, 3]])
        write_run(self.dir, "B", 1, [[5, 1], [0, 0], [0, 0], [0, 0]])
        code, stdout, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("B  wet      1  forecast by A      4  ratio  0.25  OUTSIDE", stdout)

    def test_the_wet_threshold_counts_only_deep_enough_edges(self):
        write_run(self.dir, "A", 0, [[0, 5], [0, 7], [2, 9], [0, 3]])
        write_run(self.dir, "B", 1, [[5, 1], [7, 0], [9, 0], [3, 0]])
        _, stdout, _ = self.run_main("--wet-cm", "6")
        self.assertIn("B  wet      2  forecast by A      2  ratio  1.00  ok", stdout)

    def test_first_and_last_pick_the_runs(self):
        write_run(self.dir, "A", 0, [[0, 5]])
        write_run(self.dir, "B", 1, [[5, 5]])
        write_run(self.dir, "C", 2, [[5, 5]])
        _, stdout, _ = self.run_main("--first", "B")
        self.assertIn("C  wet", stdout)
        self.assertNotIn("B  wet", stdout)

    def test_a_run_that_does_not_follow_the_previous_one_fails_with_both_names(self):
        write_run(self.dir, "A", 0, [[0, 5]])
        write_run(self.dir, "B", 5, [[5, 5]])
        with self.assertRaisesRegex(ValueError, "run A did not forecast .* first step of B"):
            self.run_main()

    def test_one_table_is_not_enough(self):
        write_run(self.dir, "A", 0, [[0, 5]])
        code, _, stderr = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("need at least 2 tables", stderr)


if __name__ == "__main__":
    unittest.main()
