import unittest
from pathlib import Path

from simulator import personal_rhythm as rhythm
from simulator import rhythm_25h_calibration as cal


ROOT = Path(__file__).resolve().parents[1]


class Rhythm25hTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 15)

    def test_25h_drift_is_about_minus_0_96_external_hours_per_day(self):
        compiled = rhythm.compile_person_rhythm(
            {
                "rhythm": {
                    "intrinsic_day_hours": 25.0,
                    "schedule_lock": 0.70,
                }
            },
            {"external_day_hours": 24.0},
        )
        self.assertAlmostEqual(
            rhythm.daily_phase_drift_hours(compiled),
            -0.96,
            places=12,
        )

    def test_free_running_25h_has_no_schedule_load(self):
        compiled = rhythm.compile_person_rhythm(
            {
                "rhythm": {
                    "intrinsic_day_hours": 25.0,
                    "schedule_lock": 0.0,
                }
            },
            {"external_day_hours": 24.0},
        )
        for day in (1.0, 6.0, 12.0, 18.0):
            self.assertEqual(
                rhythm.state(compiled, day)[
                    "schedule_mismatch_load"
                ],
                0.0,
            )

    def test_25h_realigns_after_25_days(self):
        compiled = rhythm.compile_person_rhythm(
            {
                "rhythm": {
                    "intrinsic_day_hours": 25.0,
                    "schedule_lock": 1.0,
                }
            },
            {"external_day_hours": 24.0},
        )
        state = rhythm.state(compiled, 25.0)
        self.assertAlmostEqual(
            state["relative_phase_cycles"], 0.0, places=12
        )
        self.assertAlmostEqual(
            state["phase_mismatch"], 0.0, places=12
        )


if __name__ == "__main__":
    unittest.main()
