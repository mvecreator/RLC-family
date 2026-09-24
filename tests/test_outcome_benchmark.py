import unittest

from simulator import outcome_benchmark as bench
from simulator import outcome_blind as blind


class OutcomeBenchmarkTests(unittest.TestCase):
    def test_first_benchmark_reference_scores(self):
        result = bench.run_benchmark()

        self.assertEqual(result["direction_case_count"], 34)

        self.assertEqual(
            result["direction_scores"]["person"]["model"]["correct"], 26
        )
        self.assertEqual(
            result["direction_scores"]["person"]["persistence"]["correct"], 15
        )
        self.assertEqual(
            result["direction_scores"]["person"]["linear_trend"]["correct"], 17
        )

        self.assertEqual(
            result["direction_scores"]["link"]["model"]["correct"], 26
        )
        self.assertEqual(
            result["direction_scores"]["link"]["persistence"]["correct"], 14
        )
        self.assertEqual(
            result["direction_scores"]["link"]["linear_trend"]["correct"], 17
        )

    def test_hidden_shifts_are_not_magically_predicted(self):
        result = bench.run_benchmark()
        hidden = result["person_regime_scores"]["hidden_shift"]
        reversal = result["person_regime_scores"]["trend_reversal"]

        self.assertEqual(hidden["model"]["correct"], 0)
        self.assertEqual(hidden["linear_trend"]["correct"], 0)
        self.assertEqual(reversal["model"]["correct"], 0)
        self.assertEqual(reversal["linear_trend"]["correct"], 0)

    def test_localization_is_not_perfect(self):
        result = bench.run_benchmark()
        self.assertEqual(
            result["localization_scores"]["model"]["correct"], 2
        )
        self.assertEqual(
            result["localization_scores"]["linear_trend"]["correct"], 2
        )
        self.assertEqual(
            result["localization_scores"]["persistence"]["correct"], 0
        )

    def test_first_future_crossing_excludes_already_crossed_entities(self):
        rows = [
            {
                "day": float(day),
                "persons": {
                    "already": {
                        "accumulated_load": 0.50,
                        "combined": 0.20,
                    },
                    "future": {
                        "accumulated_load": 0.30 + 0.005 * day,
                        "combined": 0.25,
                    },
                },
                "links": {},
            }
            for day in range(6)
        ]
        prediction = blind.predict_prefix(rows, horizon_days=5)
        self.assertNotEqual(
            prediction["predicted_first_person_attention"],
            "already",
        )


if __name__ == "__main__":
    unittest.main()
