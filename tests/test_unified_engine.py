import unittest
from pathlib import Path

from simulator import problem_solver as ps
from simulator import unified_engine as engine
from simulator import unified_engine_calibration as cal


ROOT = Path(__file__).resolve().parents[1]


class UnifiedEngineTests(unittest.TestCase):
    def setUp(self):
        self.scenario = cal.load_json(
            ROOT / "examples" /
            "acoustic_induction1_households_scenario.json"
        )
        self.spec = cal.load_json(
            ROOT / "examples" / "unified_engine1_spec.json"
        )

    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 16)

    def test_compile_only_mode_is_valid(self):
        result = engine.run_engine(self.scenario, {})
        self.assertIn("person_ir", result["outputs"])
        self.assertNotIn("timeline", result["outputs"])
        self.assertEqual(
            result["engine_version"],
            "RLC-FAMILY-UNIFIED-ENGINE1-0.1",
        )

    def test_problem_solver_routes_unified_engine(self):
        result = ps.solve_problem(
            self.scenario,
            {
                "type": "unified_engine",
                "engine_spec": {},
            },
        )
        self.assertEqual(
            result["engine_version"],
            "RLC-FAMILY-UNIFIED-ENGINE1-0.1",
        )
        self.assertIn("person_ir", result["outputs"])

    def test_digest_changes_when_input_changes(self):
        a = engine.compile_engine(self.scenario, self.spec)
        changed = dict(self.spec)
        changed["tag"] = "different-input"
        b = engine.compile_engine(self.scenario, changed)
        self.assertNotEqual(a["input_digest"], b["input_digest"])


if __name__ == "__main__":
    unittest.main()
