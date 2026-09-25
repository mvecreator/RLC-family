import unittest
from pathlib import Path

from simulator import neighbor_network_calibration as cal
from simulator import problem_solver as ps


ROOT = Path(__file__).resolve().parents[1]


class NeighborProblemRoutingTests(unittest.TestCase):
    def test_problem_solver_routes_neighbor_network(self):
        scenario = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_scenario.json"
        )
        spec = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_spec.json"
        )
        result = ps.solve_problem(
            scenario,
            {
                "type": "neighbor_network",
                "neighbor_spec": spec,
            },
        )
        self.assertEqual(
            result["model_version"],
            "RLC-FAMILY-NEIGHBOR-NET1-0.1",
        )
        self.assertEqual(
            [len(h["members"]) for h in result["neighbor_households"]],
            [1, 3, 2],
        )
        self.assertFalse(result["intent_inferred"])


if __name__ == "__main__":
    unittest.main()
