import unittest

from simulator import person_load_calibration as cal
from simulator import person_load_model as pload


class PersonLoadCalibrationTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], result["total"])

    def test_short_strong_stress_recovers_without_sustained_review(self):
        result = cal.run_case(
            "short",
            [0.10] * 3 + [0.65] * 3 + [0.10] * 24,
        )["summary"]
        self.assertEqual(result["band"], "RECOVERY_ATTENTION")
        self.assertIsNone(result["first_sustained_load_review_day"])
        self.assertLess(result["final_load"], pload.RECOVERY_ATTENTION)

    def test_high_sustained_requires_dwell(self):
        result = cal.run_case("high", [0.50] * 30)["summary"]
        self.assertEqual(result["band"], "SUSTAINED_LOAD_REVIEW")
        self.assertIsNotNone(result["first_sustained_load_review_day"])
        self.assertGreaterEqual(
            result["first_sustained_load_review_day"],
            pload.SUSTAINED_DWELL_DAYS,
        )

    def test_child_uses_caregiver_language(self):
        result = cal.run_case(
            "child", [0.50] * 30, kind="child"
        )["summary"]
        actions = [x["action"] for x in pload.recommendations(
            result, kind="child"
        )]
        self.assertIn("CAREGIVER_LOAD_REVIEW", actions)
        self.assertNotIn("SUSTAINED_LOAD_REVIEW", actions)

    def test_equilibrium_inverse_is_consistent(self):
        for target in (0.35, 0.50, 0.65):
            load = pload.required_constant_load_for_equilibrium(target)
            state = pload.equilibrium_for_constant_load(load)
            self.assertAlmostEqual(state, target, places=12)


if __name__ == "__main__":
    unittest.main()
