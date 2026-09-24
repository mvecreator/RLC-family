import unittest
from pathlib import Path

from simulator import person_solo_calibration as solo
from simulator import person_safety as safety


ROOT = Path(__file__).resolve().parents[1]


class PersonSafetyTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(ROOT / "examples" / "person_solo_scenario.json")
        self.obs = solo.load_json(ROOT / "examples" / "person_solo_wake_observations.json")
        self.hist = solo.load_json(ROOT / "examples" / "person_solo_historical_timeline.json")
        self.current = solo.load_json(ROOT / "examples" / "person_solo_current_timeline.json")

    def test_stress_accumulates_gradually(self):
        result = safety.assess(self.scenario, self.obs, self.hist, days=30)
        t = result["trajectory"]
        self.assertGreater(t[7]["stress_load"], t[0]["stress_load"])
        self.assertGreater(t[14]["stress_load"], t[7]["stress_load"])

    def test_persistent_pattern_produces_gp_review_guardrail(self):
        result = safety.assess(self.scenario, self.obs, self.hist, days=30)
        levels = [x["level"] for x in result["care"]["signals"]]
        self.assertIn("SELF_MONITOR", levels)
        self.assertIn("GP_REVIEW", levels)

    def test_current_sparse_coffee_load_is_lower(self):
        a = safety.assess(self.scenario, self.obs, self.hist, days=30)
        b = safety.assess(self.scenario, self.obs, self.current, days=30)
        self.assertGreater(
            a["components"]["forcing_load"],
            b["components"]["forcing_load"],
        )
        self.assertGreater(
            a["summary"]["final_stress_load"],
            b["summary"]["final_stress_load"],
        )

    def test_psychosis_red_flag_overrides_numeric_score(self):
        result = safety.assess(
            self.scenario,
            self.obs,
            self.current,
            days=1,
            clinical={"hallucinations": True},
        )
        levels = [x["level"] for x in result["care"]["signals"]]
        self.assertIn("URGENT_MEDICAL_REVIEW", levels)
        self.assertFalse(result["care"]["psychosis_probability_computed"])

    def test_emergency_flag_is_separate(self):
        result = safety.assess(
            self.scenario,
            self.obs,
            self.current,
            days=1,
            clinical={"cannot_keep_self_safe": True},
        )
        self.assertEqual(
            result["care"]["clinical_red_flags"]["level"],
            "EMERGENCY",
        )

    def test_missing_red_flags_are_unknown_not_negative(self):
        result = safety.assess(
            self.scenario, self.obs, self.current, days=1
        )
        self.assertEqual(
            result["care"]["clinical_red_flags"]["level"],
            "NOT_ASSESSED_FOR_RED_FLAGS",
        )

    def test_deterministic(self):
        a = safety.assess(self.scenario, self.obs, self.hist, days=30)
        b = safety.assess(self.scenario, self.obs, self.hist, days=30)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
