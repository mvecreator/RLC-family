import copy
import unittest
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


class PersonFamilySafetyTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        self.stressed = solo.load_json(
            ROOT / "examples" / "person_family_stress_timeline.json"
        )
        self.critical_scenario = solo.load_json(
            ROOT / "examples" / "person_family_breakdown_scenario.json"
        )
        self.critical_timeline = solo.load_json(
            ROOT / "examples" / "person_family_breakdown_timeline.json"
        )

    def test_accumulated_link_strain_is_gradual(self):
        result = family_safety.assess(self.scenario, self.stressed)
        rows = result["trajectory"]
        key = "husband->wife"
        early = min(rows, key=lambda x: abs(x["day"] - 2.0))
        later = min(rows, key=lambda x: abs(x["day"] - 14.0))
        self.assertGreater(
            later["links"][key]["accumulated_strain"],
            early["links"][key]["accumulated_strain"],
        )

    def test_persistent_partner_strain_raises_repair_review_only(self):
        result = family_safety.assess(self.scenario, self.stressed)
        link = result["summary"]["links"]["husband->wife"]
        actions = [x["action"] for x in link["recommendations"]]
        self.assertIn("RELATIONSHIP_REPAIR_REVIEW", actions)
        self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions)
        self.assertIsNone(link["first_breakdown_risk_day"])
        self.assertFalse(link["breakdown_probability_computed"])

    def test_critical_partner_strain_raises_breakdown_review(self):
        result = family_safety.assess(
            self.critical_scenario,
            self.critical_timeline,
        )
        link = result["summary"]["links"]["husband->wife"]
        actions = [x["action"] for x in link["recommendations"]]
        self.assertIn("RELATIONSHIP_REPAIR_REVIEW", actions)
        self.assertIn("BREAKDOWN_RISK_REVIEW", actions)
        self.assertIsNotNone(link["first_breakdown_risk_day"])
        self.assertGreaterEqual(link["peak_strain"]["value"], 0.65)
        self.assertFalse(link["breakdown_probability_computed"])

    def test_repair_window_reduces_final_strain_from_peak(self):
        result = family_safety.assess(self.scenario, self.stressed)
        link = result["summary"]["links"]["husband->wife"]
        self.assertLess(link["final_strain"], link["peak_strain"]["value"])

    def test_good_channel_does_not_inherit_breakdown_signal(self):
        calm = copy.deepcopy(self.stressed)
        for event in calm["события"]:
            if event["id"] == "partner-channel-degraded":
                event["качество_связи"] = 0.95
            if event["id"] in {
                "partner-a-sustained-load",
                "partner-b-sustained-load",
            }:
                event["добавить_возбуждение"] = 0.05
        result = family_safety.assess(self.scenario, calm)
        link = result["summary"]["links"]["husband->wife"]
        actions = [x["action"] for x in link["recommendations"]]
        self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions)

    def test_high_current_alone_is_not_conflict(self):
        sample = {
            "financial_stress": 0.0,
            "active_events": [],
            "nodes": [
                {"id": "a", "voltage": 0.10, "memory": 0.10},
                {"id": "b", "voltage": -0.10, "memory": 0.10},
            ],
            "links": [{
                "from": "a", "to": "b", "quality": 1.0,
                "current_abs": 1.0,
            }],
        }
        c = family_safety.instantaneous_components(sample)
        self.assertLess(c["links"]["a->b"]["combined"], 0.40)

    def test_explicit_safety_flag_overrides_joint_repair(self):
        result = family_safety.assess(
            self.scenario,
            self.stressed,
            {"fear_for_safety": True},
        )
        actions = result["summary"]["links"]["husband->wife"]["recommendations"]
        self.assertEqual(actions[0]["action"], "SAFETY_FIRST")
        self.assertTrue(
            result["summary"]["relationship_safety_override"]["active"]
        )

    def test_deterministic(self):
        a = family_safety.assess(self.scenario, self.stressed)
        b = family_safety.assess(self.scenario, self.stressed)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
