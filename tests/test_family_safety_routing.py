import unittest
from pathlib import Path

from simulator import person_solo_calibration as solo
from simulator import problem_solver as ps


ROOT = Path(__file__).resolve().parents[1]


class FamilySafetyRoutingTests(unittest.TestCase):
    def test_problem_solver_routes_family_safety(self):
        scenario = solo.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = solo.load_json(
            ROOT / "examples" / "person_family_stress_timeline.json"
        )
        result = ps.solve_problem(
            scenario,
            {"type": "family_safety", "timeline": timeline},
        )
        self.assertIn("summary", result)
        self.assertIn("links", result["summary"])
        self.assertFalse(
            result["summary"]["breakdown_probability_computed"]
        )


if __name__ == "__main__":
    unittest.main()
