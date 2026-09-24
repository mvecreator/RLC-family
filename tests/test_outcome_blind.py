import copy
import unittest

from simulator import outcome_blind as blind
from simulator import outcome_blind_calibration as cal


class OutcomeBlindTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 8)

    def test_suffix_change_cannot_change_prefix_prediction(self):
        a = cal.generate_case(0.55, 0.55)
        b = cal.generate_case(0.55, 0.02)
        pa, _ = blind.split_rows(a, 5, 5)
        pb, _ = blind.split_rows(b, 5, 5)
        self.assertEqual(
            blind.predict_prefix(pa, 5),
            blind.predict_prefix(pb, 5),
        )

    def test_hidden_reversal_is_allowed_to_fail(self):
        rows = cal.generate_case(0.55, 0.02)
        result = blind.run_blind(rows, 5, 5)
        self.assertEqual(
            result["model"]["prediction"]["persons"]["p"]["direction"],
            "ACCUMULATING",
        )
        self.assertEqual(
            result["model"]["actual"]["persons"]["p"]["direction"],
            "RECOVERING",
        )

    def test_persistence_is_explicit_baseline(self):
        rows = cal.generate_case(0.55, 0.55)
        result = blind.run_blind(rows, 5, 5)
        self.assertIn("persistence_baseline", result)
        self.assertEqual(
            result["persistence_baseline"]["prediction"]["persons"]["p"]["direction"],
            "STABLE",
        )


if __name__ == "__main__":
    unittest.main()
