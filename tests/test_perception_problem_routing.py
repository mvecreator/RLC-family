import unittest
from pathlib import Path

from simulator import perception_identification_calibration as cal
from simulator import problem_solver as ps


ROOT = Path(__file__).resolve().parents[1]


class PerceptionProblemRoutingTests(unittest.TestCase):
    def test_problem_solver_routes_perception_identification(self):
        scenario = cal.load_json(
            ROOT / "examples" / "perception_id1_synthetic_target.json"
        )
        spec = cal.load_json(
            ROOT / "examples" / "perception_id1_low_prior_spec.json"
        )
        result = ps.solve_problem(
            scenario,
            {
                "type": "perception_identification",
                "perception_spec": spec,
            },
        )
        self.assertEqual(
            result["model_version"],
            "RLC-FAMILY-PERCEPTION-ID1-0.1",
        )
        self.assertFalse(result["real_world_belief_inference"])


if __name__ == "__main__":
    unittest.main()
