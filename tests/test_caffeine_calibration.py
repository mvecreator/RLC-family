import unittest

from simulator import caffeine_calibration as cal
from simulator import caffeine_model as caffeine
from simulator import sleep_trajectory_model as sleep


class CaffeineCalibrationTests(unittest.TestCase):
    def test_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 8)

    def test_half_life_parameter_is_configurable(self):
        self.assertAlmostEqual(
            caffeine.remaining_fraction(8, half_life_hours=8),
            0.5,
            places=12,
        )

    def test_later_same_dose_leaves_more_at_sleep(self):
        a = caffeine.residual_at_sleep([
            {"dose_mg": 100, "hours_before_sleep": 10}
        ])
        b = caffeine.residual_at_sleep([
            {"dose_mg": 100, "hours_before_sleep": 3}
        ])
        self.assertGreater(
            b["residual_mg_at_sleep"],
            a["residual_mg_at_sleep"],
        )

    def test_secondary_sleep_fades_after_mature_biphasic_stage(self):
        mature = sleep.state(0.60)
        resolving = sleep.state(0.85)
        final = sleep.state(1.0)
        self.assertEqual(mature["stage"], "BIPHASIC_MATURE")
        self.assertGreater(
            mature["secondary_bout_weight"],
            resolving["secondary_bout_weight"],
        )
        self.assertEqual(final["secondary_bout_weight"], 0.0)
        self.assertEqual(final["stage"], "MONOPHASIC_RECOVERED")


if __name__ == "__main__":
    unittest.main()
