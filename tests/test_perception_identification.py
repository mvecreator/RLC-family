import unittest
from pathlib import Path

from simulator import perception_identification as pid
from simulator import perception_identification_calibration as cal


ROOT = Path(__file__).resolve().parents[1]


class PerceptionIdentificationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = cal.load_json(
            ROOT / "examples" / "perception_id1_synthetic_target.json"
        )
        self.low_spec = cal.load_json(
            ROOT / "examples" / "perception_id1_low_prior_spec.json"
        )
        self.high_spec = cal.load_json(
            ROOT / "examples" / "perception_id1_high_prior_spec.json"
        )

    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 14)

    def test_same_short_trace_can_support_different_prior_selected_models(self):
        low = pid.analyze(self.scenario, self.low_spec)
        high = pid.analyze(self.scenario, self.high_spec)
        self.assertEqual(
            low["actual_theta"],
            high["actual_theta"],
        )
        self.assertLess(
            low["perceived_theta_from_brief_window"]["R"],
            high["perceived_theta_from_brief_window"]["R"],
        )
        self.assertLess(
            low["perceived_theta_from_brief_window"]["L"],
            high["perceived_theta_from_brief_window"]["L"],
        )

    def test_brief_window_leaves_more_models_than_full_window(self):
        result = pid.analyze(self.scenario, self.low_spec)
        self.assertGreater(
            result["brief_identifiability"]["candidate_count"],
            result["full_identifiability"]["candidate_count"],
        )

    def test_real_world_belief_inference_is_false(self):
        result = pid.analyze(self.scenario, self.low_spec)
        self.assertFalse(result["real_world_belief_inference"])


if __name__ == "__main__":
    unittest.main()
