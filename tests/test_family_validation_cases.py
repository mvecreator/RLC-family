import copy
import unittest
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


def timeline(events=None, days=30):
    return {
        "моделирование": {
            "дней": days,
            "шаг_дней": 0.02,
            "выборка_дней": 0.10,
        },
        "события": events or [],
    }


def calm_scenario():
    s = solo.load_json(ROOT / "examples" / "person_family_scenario.json")
    s["отношения"]["напряженность"] = 0.15
    s["отношения"]["накопленная_память"] = 0.10
    for link in s["связи_персонажей"]:
        link["quality"] = 0.90
    s["финансы"]["доходы_в_месяц"] = [6000]
    s["финансы"]["резерв"] = 18000
    return s


def actions(link):
    return [x["action"] for x in link["recommendations"]]


class FamilyValidationCases(unittest.TestCase):
    def test_calm_family_has_no_repair_or_breakdown_signal(self):
        result = family_safety.assess(calm_scenario(), timeline())
        for link in result["summary"]["links"].values():
            self.assertLess(link["peak_strain"]["value"], 0.40)
            self.assertNotIn("RELATIONSHIP_REPAIR_REVIEW", actions(link))
            self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions(link))

    def test_high_interaction_good_channel_is_not_breakdown(self):
        events = [{
            "id": "single-person-high-drive",
            "день": 2,
            "длительность_дней": 14,
            "персонаж": "husband",
            "добавить_возбуждение": 0.90,
        }]
        result = family_safety.assess(calm_scenario(), timeline(events))
        for link in result["summary"]["links"].values():
            self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions(link))
            self.assertNotIn("RELATIONSHIP_REPAIR_REVIEW", actions(link))

    def test_financial_stress_alone_does_not_become_relationship_breakdown(self):
        s = calm_scenario()
        s["финансы"].update({
            "доходы_в_месяц": [3000],
            "ипотека_в_месяц": 1450,
            "базовые_расходы_в_месяц": 2200,
            "прочие_расходы_в_месяц": 550,
            "резерв": 800,
        })
        result = family_safety.assess(s, timeline())
        for link in result["summary"]["links"].values():
            self.assertLess(link["peak_strain"]["value"], 0.50)
            self.assertNotIn("RELATIONSHIP_REPAIR_REVIEW", actions(link))
            self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions(link))

    def test_parent_child_strain_stays_localized(self):
        events = [
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
        ]
        result = family_safety.assess(calm_scenario(), timeline(events))
        father_son = result["summary"]["links"]["husband->son"]
        partner = result["summary"]["links"]["husband->wife"]
        self.assertIn("RELATIONSHIP_REPAIR_REVIEW", actions(father_son))
        self.assertNotIn("BREAKDOWN_RISK_REVIEW", actions(father_son))
        self.assertNotIn("RELATIONSHIP_REPAIR_REVIEW", actions(partner))
        self.assertGreater(
            father_son["peak_strain"]["value"],
            partner["peak_strain"]["value"] + 0.25,
        )


if __name__ == "__main__":
    unittest.main()
