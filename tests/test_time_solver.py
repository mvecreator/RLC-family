import copy
import json
import tempfile
import unittest
from pathlib import Path

from simulator import rlc_family_sim as core
from simulator import time_solver as ts

ROOT = Path(__file__).resolve().parents[1]


class TimeSolverTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads((ROOT / "examples" / "family_scenario.json").read_text(encoding="utf-8"))
        self.timeline = json.loads((ROOT / "examples" / "family_timeline.json").read_text(encoding="utf-8"))

    def test_deterministic(self):
        a = ts.simulate_timeline(self.scenario, self.timeline)
        b = ts.simulate_timeline(self.scenario, self.timeline)
        self.assertEqual(a, b)

    def test_money_impulse_reaches_reserve(self):
        tl = {"моделирование":{"дней":2,"шаг_дней":0.02,"выборка_дней":0.5},
              "события":[{"день":1,"денежный_импульс":1000}]}
        with_imp = ts.simulate_timeline(self.scenario, tl)
        no_imp = ts.simulate_timeline(self.scenario, {"моделирование":tl["моделирование"],"события":[]})
        delta = with_imp["summary"]["final_reserve"] - no_imp["summary"]["final_reserve"]
        self.assertAlmostEqual(delta, 1000.0, places=6)

    def test_memory_impulse_persists(self):
        tl = {"моделирование":{"дней":1,"шаг_дней":0.01,"выборка_дней":0.25},
              "события":[{"день":0.5,"импульс_памяти":0.2}]}
        a = ts.simulate_timeline(self.scenario, tl)
        b = ts.simulate_timeline(self.scenario, {"моделирование":tl["моделирование"],"события":[]})
        self.assertGreater(a["summary"]["final_memory"], b["summary"]["final_memory"])

    def test_argument_creates_larger_current_peak(self):
        base = {"моделирование":{"дней":3,"шаг_дней":0.01,"выборка_дней":0.1},"события":[]}
        event = copy.deepcopy(base)
        event["события"] = [{
            "день":1,"длительность_дней":0.4,
            "добавить":{"отношения.напряженность":0.25,"связь.усиление_эмоций":0.2}
        }]
        a = ts.simulate_timeline(self.scenario, base)
        b = ts.simulate_timeline(self.scenario, event)
        self.assertGreater(abs(b["summary"]["peak_interaction_current"]), abs(a["summary"]["peak_interaction_current"]) + 1e-5)

    def test_talk_after_argument_beats_silence_on_memory(self):
        base = copy.deepcopy(self.scenario)
        base["отношения"]["напряженность"] = 0.40
        base["отношения"]["накопленная_память"] = 0.25
        base["связь"]["качество_проводника"] = 0.75
        base["связь"]["усиление_эмоций"] = 1.05

        argument = {
            "id": "argument",
            "день": 1,
            "длительность_дней": 0.4,
            "добавить": {
                "отношения.напряженность": 0.28,
                "связь.усиление_эмоций": 0.20
            },
            "импульс_памяти": 0.08
        }

        silence = {
            "id": "silence",
            "день": 1.4,
            "длительность_дней": 2.0,
            "установить": {"связь.качество_проводника": 0.25}
        }

        talk = {
            "id": "talk",
            "день": 1.4,
            "длительность_дней": 0.5,
            "установить": {
                "связь.качество_проводника": 0.90,
                "связь.сброс_через_антенну": 0.80,
                "связь.согласование_собеседника": 0.90
            }
        }

        silence_result = ts.simulate_timeline(
            base,
            {"моделирование":{"дней":7,"шаг_дней":0.01,"выборка_дней":0.05},
             "события":[argument, silence]},
        )
        talk_result = ts.simulate_timeline(
            base,
            {"моделирование":{"дней":7,"шаг_дней":0.01,"выборка_дней":0.05},
             "события":[argument, talk]},
        )

        self.assertLess(
            talk_result["summary"]["final_memory"],
            silence_result["summary"]["final_memory"],
        )

    def test_adolescent_nonlinearity_increases_memory_under_high_tension(self):
        low = copy.deepcopy(self.scenario)
        high = copy.deepcopy(self.scenario)
        for scenario in (low, high):
            scenario["отношения"]["напряженность"] = 0.72
            scenario["отношения"]["накопленная_память"] = 0.35
            scenario["отношения"]["сопротивление_детей"] = [0.40]
            scenario["связь"]["качество_проводника"] = 0.70
            scenario["связь"]["усиление_эмоций"] = 1.15
        low["отношения"]["подростковая_нелинейность"] = 0.0
        high["отношения"]["подростковая_нелинейность"] = 0.90

        timeline = {
            "моделирование":{"дней":7,"шаг_дней":0.01,"выборка_дней":0.05},
            "события":[]
        }
        low_result = ts.simulate_timeline(low, timeline)
        high_result = ts.simulate_timeline(high, timeline)

        self.assertGreater(
            high_result["summary"]["final_memory"],
            low_result["summary"]["final_memory"],
        )

    def test_zero_duration_set_does_not_persist(self):
        tl = {"моделирование":{"дней":1,"шаг_дней":0.01,"выборка_дней":0.2},
              "события":[{"день":0.5,"установить":{"связь.внешний_фон":1.0}}]}
        a = ts.simulate_timeline(self.scenario, tl)
        b = ts.simulate_timeline(self.scenario, {"моделирование":tl["моделирование"],"события":[]})
        self.assertAlmostEqual(a["samples"][-1]["drive"], b["samples"][-1]["drive"], places=10)

    def test_dt_guard(self):
        tl = {"моделирование":{"дней":2,"шаг_дней":0.5,"выборка_дней":1},"события":[]}
        with self.assertRaises(core.ScenarioError):
            ts.simulate_timeline(self.scenario, tl)

    def test_outputs(self):
        result = ts.simulate_timeline(self.scenario, self.timeline)
        with tempfile.TemporaryDirectory() as td:
            ts.write_outputs(td, result)
            for name in ("timeline_result.json", "timeline_report.md", "timeline.csv"):
                self.assertTrue((Path(td) / name).exists())

    def test_equations_exposed(self):
        result = ts.simulate_timeline(self.scenario, self.timeline)
        self.assertTrue(any("dq/dt" in eq for eq in result["equations"]))
        self.assertTrue(any("dDebt/dt" in eq for eq in result["equations"]))


if __name__ == "__main__":
    unittest.main()
