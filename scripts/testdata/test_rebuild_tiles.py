import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_tiles  # noqa: E402

STORM = Path("/opt/airflow/data/testdata/storm-2026-10-10")
MANIFEST = {
    "runs": [
        {"run_ts": "20261010T041500", "nc": "nc/111/results_3di.nc"},
        {"run_ts": "20261010T043000", "nc": "nc/222/results_3di.nc"},
        {"run_ts": "20261010T044500", "nc": "nc/333/results_3di.nc"},
    ]
}


class PlanJobsTests(unittest.TestCase):
    def test_a_run_maps_to_the_nc_of_its_sim(self):
        jobs = rebuild_tiles.plan_jobs(MANIFEST, ["20261010T043000"], STORM)
        self.assertEqual(
            jobs,
            [("20261010T043000", Path("/opt/airflow/data/testdata/storm-2026-10-10/nc/222/results_3di.nc"))],
        )

    def test_jobs_keep_the_order_requested_and_drop_repeats(self):
        jobs = rebuild_tiles.plan_jobs(MANIFEST, ["20261010T044500", "20261010T041500", "20261010T044500"], STORM)
        self.assertEqual([run_ts for run_ts, _ in jobs], ["20261010T044500", "20261010T041500"])

    def test_an_unknown_run_raises_and_names_it(self):
        with self.assertRaisesRegex(ValueError, "not in the manifest: 20261010T999999"):
            rebuild_tiles.plan_jobs(MANIFEST, ["20261010T041500", "20261010T999999"], STORM)


if __name__ == "__main__":
    unittest.main()
