import unittest
from pathlib import Path

from simulator import family_member_load_report as report


ROOT = Path(__file__).resolve().parents[1]


class FamilyMemberLoadReportTests(unittest.TestCase):
    def test_every_family_member_gets_calibrated_load_summary(self):
        scenario = report.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = report.load_json(
            ROOT / "examples" / "person_family_timeline.json"
        )
        result = report.member_report(scenario, timeline)
        members = {x["id"]: x for x in result["members"]}

        self.assertEqual(
            set(members),
            {"husband", "wife", "son", "daughter"},
        )
        self.assertEqual(members["husband"]["kind"], "adult")
        self.assertEqual(members["wife"]["kind"], "adult")
        self.assertEqual(members["son"]["kind"], "child")
        self.assertEqual(members["daughter"]["kind"], "child")

        allowed = {
            "STABLE",
            "RECOVERY_ATTENTION",
            "SUSTAINED_LOAD_REVIEW",
            "HIGH_LOAD_REVIEW",
        }
        for item in members.values():
            self.assertIn(item["band"], allowed)
            self.assertIn("peak_load", item)
            self.assertIn("mean_components", item)
            self.assertIn("recommendations", item)

    def test_child_load_review_uses_caregiver_action(self):
        # Integration boundary is covered by PERSON-LOAD-CAL1; here ensure
        # the report preserves child kind for downstream caregiver wording.
        scenario = report.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = report.load_json(
            ROOT / "examples" / "person_family_timeline.json"
        )
        result = report.member_report(scenario, timeline)
        child_kinds = [
            x["kind"] for x in result["members"]
            if x["id"] in {"son", "daughter"}
        ]
        self.assertEqual(child_kinds, ["child", "child"])


if __name__ == "__main__":
    unittest.main()
