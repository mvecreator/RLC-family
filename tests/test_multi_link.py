import unittest
from pathlib import Path

from simulator import multi_link_calibration as cal
from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core


ROOT = Path(__file__).resolve().parents[1]


class MultiLinkTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 11)

    def test_legacy_single_link_keeps_old_family_key(self):
        scenario = cal.base_scenario([
            {"from": "a", "to": "b", "quality": 0.8}
        ])
        ir = pm.compile_person_network(scenario)
        self.assertEqual(ir["links"][0]["link_id"], "a->b")

    def test_parallel_pair_without_explicit_ids_is_rejected(self):
        with self.assertRaises(core.ScenarioError):
            pm.compile_person_network(cal.base_scenario([
                {"from": "a", "to": "b", "quality": 0.8},
                {"from": "a", "to": "b", "quality": 0.7},
            ]))

    def test_pair_target_is_ambiguous_with_parallel_branches(self):
        ir = pm.compile_person_network(
            cal.base_scenario(cal.two_parallel())
        )
        with self.assertRaises(core.ScenarioError):
            pts._compile_events(
                {
                    "events": [{
                        "id": "ambiguous",
                        "at_day": 0,
                        "duration_days": 1,
                        "target_link": ["a", "b"],
                        "communication_quality_set": 0.5,
                    }]
                },
                {"a", "b"},
                ir["links"],
            )

    def test_incident_parallel_load_is_monotone(self):
        one = family_safety._incident_link_load(
            cal.safety_sample(1), "a"
        )
        two = family_safety._incident_link_load(
            cal.safety_sample(2), "a"
        )
        self.assertGreater(two, one)
        self.assertLessEqual(two, 1.0)


if __name__ == "__main__":
    unittest.main()
