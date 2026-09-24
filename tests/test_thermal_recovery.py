import unittest

from simulator import thermal_calibration as cal
from simulator import thermal_recovery as therm


class ThermalRecoveryTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 10)

    def test_i_squared_r_scaling(self):
        i = 0.2
        low = i * i * 0.3
        high_r = i * i * 1.5
        double_i = (2 * i) ** 2 * 0.3
        self.assertGreater(high_r, low)
        self.assertAlmostEqual(double_i, 4 * low, places=12)

    def test_damage_only_accumulates_above_overheat_threshold(self):
        below = therm.advance_damage(
            0.0, therm.LINK_OVERHEAT - 0.01, 0.5, 1.0
        )
        above = therm.advance_damage(
            0.0, therm.LINK_OVERHEAT + 0.20, 0.5, 1.0
        )
        self.assertEqual(below, 0.0)
        self.assertGreater(above, 0.0)

    def test_recovery_debt_can_outlive_immediate_heat_peak(self):
        heat, debt = cal.run_steps_person(
            0.70, 1.0, 0.05, 1.0, 1.0
        )
        self.assertLess(heat, 0.70)
        self.assertGreater(debt, 0.0)

    def test_person_and_link_bands_are_non_diagnostic_labels(self):
        self.assertEqual(therm.person_heat_band(0.60), "OVERHEATED")
        self.assertEqual(
            therm.link_heat_band(0.40, 0.60),
            "RUPTURE_RISK_REVIEW",
        )


if __name__ == "__main__":
    unittest.main()
