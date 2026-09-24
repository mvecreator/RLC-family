import copy
import unittest
from pathlib import Path

from simulator import recovery_scenarios as recovery
from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


class RecoveryScenarioTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        self.timeline = solo.load_json(
            ROOT / "examples" / "person_family_stress_timeline.json"
        )

    def test_deep_recovery_beats_continuation_at_stress_cutoff(self):
        result = recovery.compare_profiles(
            self.scenario,
            self.timeline,
            cutoff_day=20.0,
            profile_names=["continue_7d", "deep_recovery_7d"],
        )
        cont = result["profiles"]["continue_7d"]["summary"]
        deep = result["profiles"]["deep_recovery_7d"]["summary"]

        self.assertLess(
            deep["max_person_heat"],
            cont["max_person_heat"],
        )
        self.assertLess(
            deep["max_person_recovery_debt"],
            cont["max_person_recovery_debt"],
        )
        self.assertLess(
            deep["max_link_heat"],
            cont["max_link_heat"],
        )
        self.assertLessEqual(
            deep["max_link_damage"],
            cont["max_link_damage"],
        )

    def test_mountain_style_is_mechanism_bundle_not_special_physics(self):
        profile = recovery.PROFILES["mountain_style_7d"]
        self.assertIn("interpretation", profile)
        self.assertNotIn("altitude_gain", profile)
        self.assertNotIn("mountain_gain", profile)

        result = recovery.compare_profiles(
            self.scenario,
            self.timeline,
            cutoff_day=20.0,
            profile_names=["deep_recovery_7d", "mountain_style_7d"],
        )
        deep = result["profiles"]["deep_recovery_7d"]["summary"]
        mountain = result["profiles"]["mountain_style_7d"]["summary"]

        # Person-side assumptions are intentionally identical.
        self.assertAlmostEqual(
            mountain["max_person_heat"],
            deep["max_person_heat"],
            places=10,
        )
        # Link side is slightly more conservative on heavy interaction.
        self.assertLessEqual(
            mountain["max_link_heat"],
            deep["max_link_heat"],
        )

    def test_cool_then_shared_reduces_link_damage_vs_continuation(self):
        result = recovery.compare_profiles(
            self.scenario,
            self.timeline,
            cutoff_day=20.0,
            profile_names=["continue_7d", "cool_then_shared_7d"],
        )
        cont = result["profiles"]["continue_7d"]["summary"]
        staged = result["profiles"]["cool_then_shared_7d"]["summary"]
        self.assertLessEqual(
            staged["max_link_damage"],
            cont["max_link_damage"],
        )


    def test_future_events_after_cutoff_cannot_change_recovery_projection(self):
        altered = copy.deepcopy(self.timeline)
        for event in altered["события"]:
            if float(event.get("день", 0)) > 20.0:
                event["качество_связи"] = 0.01
                event["добавить_возбуждение"] = 5.0

        a = recovery.compare_profiles(
            self.scenario,
            self.timeline,
            cutoff_day=20.0,
            profile_names=["continue_7d", "deep_recovery_7d"],
        )
        b = recovery.compare_profiles(
            self.scenario,
            altered,
            cutoff_day=20.0,
            profile_names=["continue_7d", "deep_recovery_7d"],
        )

        self.assertEqual(a["thermal_at_cutoff"], b["thermal_at_cutoff"])
        self.assertEqual(a["profiles"], b["profiles"])


if __name__ == "__main__":
    unittest.main()
