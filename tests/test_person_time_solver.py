import copy
import json
import math
import unittest
from pathlib import Path

from simulator import person_time_solver as pts
from simulator import problem_solver as ps

ROOT = Path(__file__).resolve().parents[1]


class PersonTimeSolverTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads(
            (ROOT / "examples" / "person_family_scenario.json").read_text(encoding="utf-8")
        )

    def test_no_event_starts_in_equilibrium(self):
        timeline = {
            "моделирование": {"дней": 1, "шаг_дней": 0.01, "выборка_дней": 0.1},
            "события": []
        }
        result = pts.simulate_person_timeline(self.scenario, timeline)
        for row in result["samples"]:
            for node in row["nodes"]:
                self.assertAlmostEqual(node["voltage"], 0.0, places=10)

    def test_targeted_wife_event_peaks_wife(self):
        timeline = {
            "моделирование": {"дней": 2, "шаг_дней": 0.005, "выборка_дней": 0.02},
            "события": [{
                "id": "wife-only",
                "день": 0.5,
                "длительность_дней": 0.25,
                "персонаж": "wife",
                "добавить_возбуждение": 0.50
            }]
        }
        result = pts.simulate_person_timeline(self.scenario, timeline)
        peaks = result["summary"]["persons"]
        wife = peaks["wife"]["peak_voltage_abs"]
        others = max(v["peak_voltage_abs"] for k, v in peaks.items() if k != "wife")
        self.assertGreater(wife, others)

    def test_stronger_link_transmits_more_to_receiver(self):
        base = {
            "название": "Two node propagation",
            "person_model": {"gender_prior_strength": 0},
            "персонажи": [
                {"id": "a", "type": "adult", "gender": "male", "source_weight": 1},
                {"id": "b", "type": "adult", "gender": "male", "source_weight": 1}
            ],
            "отношения": {
                "напряженность": 0.3,
                "частота_событий": 1.0,
                "накопленная_память": 0.2
            },
            "связь": {"качество_проводника": 0.7},
            "финансы": {}
        }
        event = [{
            "id": "hit-a",
            "день": 0.5,
            "длительность_дней": 0.25,
            "персонаж": "a",
            "добавить_возбуждение": 0.60
        }]
        timeline = {
            "моделирование": {"дней": 2, "шаг_дней": 0.005, "выборка_дней": 0.02},
            "события": event
        }
        weak = copy.deepcopy(base)
        strong = copy.deepcopy(base)
        weak["связи_персонажей"] = [{"from": "a", "to": "b", "quality": 0.20}]
        strong["связи_персонажей"] = [{"from": "a", "to": "b", "quality": 0.90}]
        rw = pts.simulate_person_timeline(weak, timeline)
        rs = pts.simulate_person_timeline(strong, timeline)
        self.assertGreater(
            rs["summary"]["persons"]["b"]["peak_voltage_abs"],
            rw["summary"]["persons"]["b"]["peak_voltage_abs"],
        )

    def test_memory_impulse_targets_only_one_person_at_t0(self):
        timeline = {
            "моделирование": {"дней": 0.5, "шаг_дней": 0.01, "выборка_дней": 0.1},
            "события": [{
                "id": "memory-wife",
                "день": 0,
                "персонаж": "wife",
                "импульс_памяти": 0.20
            }]
        }
        result = pts.simulate_person_timeline(self.scenario, timeline)
        initial = {x["id"]: x for x in result["samples"][0]["nodes"]}
        self.assertAlmostEqual(initial["wife"]["memory"], 0.44, places=12)
        self.assertAlmostEqual(initial["husband"]["memory"], 0.24, places=12)
        self.assertAlmostEqual(initial["son"]["memory"], 0.24, places=12)

    def test_link_quality_event_is_local_and_temporary(self):
        timeline = {
            "моделирование": {"дней": 2, "шаг_дней": 0.01, "выборка_дней": 0.1},
            "события": [{
                "id": "link-drop",
                "день": 0.5,
                "длительность_дней": 0.5,
                "связь": ["husband", "son"],
                "качество_связи": 0.10
            }]
        }
        result = pts.simulate_person_timeline(self.scenario, timeline)
        def quality_at(sample, a, b):
            for link in sample["links"]:
                if {link["from"], link["to"]} == {a, b}:
                    return link["quality"]
            raise AssertionError("link not found")
        during = min(result["samples"], key=lambda s: abs(s["day"] - 0.7))
        after = min(result["samples"], key=lambda s: abs(s["day"] - 1.5))
        self.assertAlmostEqual(quality_at(during, "husband", "son"), 0.10, places=12)
        self.assertAlmostEqual(quality_at(after, "husband", "son"), 0.86, places=12)
        self.assertAlmostEqual(quality_at(during, "wife", "son"), 0.66, places=12)

    def test_bonus_changes_reserve(self):
        base = {
            "моделирование": {"дней": 2, "шаг_дней": 0.01, "выборка_дней": 0.1},
            "события": []
        }
        with_bonus = copy.deepcopy(base)
        with_bonus["события"] = [{"id": "bonus", "день": 1, "денежный_импульс": 1000}]
        a = pts.simulate_person_timeline(self.scenario, base)
        b = pts.simulate_person_timeline(self.scenario, with_bonus)
        self.assertAlmostEqual(
            b["summary"]["final_reserve"] - a["summary"]["final_reserve"],
            1000.0,
            places=6,
        )

    def test_problem_solver_person_timeline_route(self):
        timeline = {
            "моделирование": {
                "дней": 1,
                "шаг_дней": 0.01,
                "выборка_дней": 0.1
            },
            "события": [{
                "id": "wife-event",
                "день": 0.2,
                "длительность_дней": 0.2,
                "персонаж": "wife",
                "добавить_возбуждение": 0.3
            }]
        }
        result = ps.solve_problem(
            self.scenario,
            {"type": "person_timeline", "timeline": timeline},
        )
        self.assertEqual(
            result["model_version"],
            "RLC-FAMILY-PERSON-TIME2-0.1",
        )
        self.assertIn("wife", result["summary"]["persons"])

    def test_memory_impulse_requires_person(self):
        timeline = {
            "моделирование": {
                "дней": 1,
                "шаг_дней": 0.01,
                "выборка_дней": 0.1
            },
            "события": [{
                "id": "bad-memory",
                "день": 0.2,
                "импульс_памяти": 0.1
            }]
        }
        with self.assertRaises(Exception):
            pts.simulate_person_timeline(self.scenario, timeline)

    def test_deterministic_and_finite(self):
        timeline = json.loads(
            (ROOT / "examples" / "person_family_timeline.json").read_text(encoding="utf-8")
        )
        a = pts.simulate_person_timeline(self.scenario, timeline)
        b = pts.simulate_person_timeline(self.scenario, timeline)
        self.assertEqual(a, b)
        for row in a["samples"]:
            for node in row["nodes"]:
                self.assertTrue(math.isfinite(node["voltage"]))
                self.assertTrue(math.isfinite(node["memory"]))
            for link in row["links"]:
                self.assertTrue(math.isfinite(link["current"]))


if __name__ == "__main__":
    unittest.main()
