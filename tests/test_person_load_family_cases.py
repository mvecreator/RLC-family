import unittest
from pathlib import Path

from simulator import family_member_load_report as report


ROOT = Path(__file__).resolve().parents[1]


def bands(result):
    return {x["id"]: x["band"] for x in result["members"]}


class PersonLoadFamilyCases(unittest.TestCase):
    def test_canonical_week_keeps_all_members_stable(self):
        scenario = report.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = report.load_json(
            ROOT / "examples" / "person_family_timeline.json"
        )
        result = report.member_report(scenario, timeline)
        self.assertEqual(
            bands(result),
            {
                "husband": "STABLE",
                "wife": "STABLE",
                "son": "STABLE",
                "daughter": "STABLE",
            },
        )

    def test_prolonged_partner_load_affects_adults_not_children(self):
        scenario = report.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = report.load_json(
            ROOT / "examples" / "person_family_stress_timeline.json"
        )
        result = report.member_report(scenario, timeline)
        b = bands(result)
        self.assertEqual(b["husband"], "RECOVERY_ATTENTION")
        self.assertEqual(b["wife"], "RECOVERY_ATTENTION")
        self.assertEqual(b["son"], "STABLE")
        self.assertEqual(b["daughter"], "STABLE")

    def test_critical_partner_case_is_asymmetric(self):
        scenario = report.load_json(
            ROOT / "examples" / "person_family_breakdown_scenario.json"
        )
        timeline = report.load_json(
            ROOT / "examples" / "person_family_breakdown_timeline.json"
        )
        result = report.member_report(scenario, timeline)
        b = bands(result)
        self.assertEqual(b["husband"], "SUSTAINED_LOAD_REVIEW")
        self.assertEqual(b["wife"], "RECOVERY_ATTENTION")
        self.assertEqual(b["son"], "STABLE")
        self.assertEqual(b["daughter"], "STABLE")

    def test_targeted_son_load_stays_localized(self):
        scenario = report.load_json(
            ROOT / "examples" / "person_family_scenario.json"
        )
        timeline = {
            "моделирование": {
                "дней": 30,
                "шаг_дней": 0.02,
                "выборка_дней": 0.10,
            },
            "события": [
                {
                    "id": "son-load",
                    "день": 1,
                    "длительность_дней": 18,
                    "персонаж": "son",
                    "добавить_возбуждение": 0.60,
                    "импульс_памяти": 0.05,
                },
                {
                    "id": "father-son-bad",
                    "день": 1,
                    "длительность_дней": 18,
                    "связь": ["husband", "son"],
                    "качество_связи": 0.15,
                },
                {
                    "id": "father-son-repair",
                    "день": 19,
                    "длительность_дней": 11,
                    "связь": ["husband", "son"],
                    "качество_связи": 0.92,
                },
            ],
        }
        result = report.member_report(scenario, timeline)
        b = bands(result)
        self.assertEqual(b["son"], "RECOVERY_ATTENTION")
        self.assertEqual(b["husband"], "STABLE")
        self.assertEqual(b["wife"], "STABLE")
        self.assertEqual(b["daughter"], "STABLE")

        members = {x["id"]: x for x in result["members"]}
        son_actions = [x["action"] for x in members["son"]["recommendations"]]
        self.assertIn("CAREGIVER_RECOVERY_ATTENTION", son_actions)


if __name__ == "__main__":
    unittest.main()
