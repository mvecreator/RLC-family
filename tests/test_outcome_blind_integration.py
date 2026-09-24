import unittest
from pathlib import Path

from simulator import outcome_blind_family_runner as runner
from simulator import outcome_blind_sleep as sleep_blind
from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


class OutcomeBlindIntegrationTests(unittest.TestCase):
    def test_family_case_runner_never_reports_future_rows_seen(self):
        spec = runner.load_json(
            ROOT / "examples" / "outcome_blind_family_cases.json"
        )
        result = runner.run_spec(spec)
        for case in result["cases"]:
            self.assertEqual(
                case["blindness_contract"]["prediction_future_rows_seen"],
                0,
            )

    def test_sleep_prefix_does_not_magically_predict_resolution(self):
        obs = solo.load_json(
            ROOT / "examples" / "person_solo_wake_observations.json"
        )
        result = sleep_blind.run(obs)
        self.assertEqual(result["prefix_stage"], "BIPHASIC_MATURE")
        self.assertEqual(result["prediction"]["direction"], "STABLE")
        self.assertEqual(result["actual"]["direction"], "DECREASING")
        self.assertFalse(result["direction_correct"])

    def test_personal_caffeine_feature_is_not_fabricated(self):
        obs = solo.load_json(
            ROOT / "examples" / "person_solo_wake_observations.json"
        )
        status = sleep_blind.personal_history_feature_status(obs)
        self.assertFalse(status["caffeine_dose_identified"])
        self.assertFalse(status["caffeine_timing_identified"])
        self.assertFalse(
            status["caffeine_feature_usable_without_assumption"]
        )


if __name__ == "__main__":
    unittest.main()
