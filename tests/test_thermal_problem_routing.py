import unittest
from pathlib import Path

from simulator import problem_solver as ps
from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


class ThermalProblemRoutingTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        self.timeline = solo.load_json(
            ROOT / "examples" / "person_family_stress_timeline.json"
        )

    def test_family_thermal_route(self):
        result = ps.solve_problem(
            self.scenario,
            {
                "type": "family_thermal",
                "timeline": self.timeline,
            },
        )
        self.assertEqual(result["problem_type"], "family_thermal")
        self.assertIn("persons", result["summary"])
        self.assertIn("links", result["summary"])

    def test_recovery_scenarios_route(self):
        result = ps.solve_problem(
            self.scenario,
            {
                "type": "recovery_scenarios",
                "timeline": self.timeline,
                "cutoff_day": 20,
                "profiles": [
                    "continue_7d",
                    "deep_recovery_7d",
                ],
            },
        )
        self.assertIn("profiles", result)
        self.assertIn("continue_7d", result["profiles"])
        self.assertIn("deep_recovery_7d", result["profiles"])


if __name__ == "__main__":
    unittest.main()
