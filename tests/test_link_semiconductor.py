import unittest

from simulator import link_semiconductor as semi
from simulator import link_semiconductor_calibration as cal
from simulator import person_model as pm
from simulator import person_network_solver as pnet
from simulator import rlc_family_sim as core


class LinkSemiconductorTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 10)

    def test_resistor_power_is_exactly_i2r(self):
        link = {"element_type": "RESISTIVE", "R_link": 1.7}
        i = semi.current(link, 0.30, 0.0)
        self.assertAlmostEqual(
            semi.power(link, 0.30, 0.0),
            i * i * link["R_link"],
            places=12,
        )

    def test_mosfet_gate_monotonicity(self):
        link = {
            "element_type": "MOSFET",
            "R_link": 1.0,
            "gate_threshold": 0.5,
            "gate_softness": 0.08,
            "off_ratio": 0.02,
            "reverse_ratio": 0.20,
        }
        currents = []
        for gate in (0.1, 0.3, 0.5, 0.7, 0.9):
            link["gate"] = gate
            currents.append(abs(semi.current(link, 0.2, 0.0)))
        self.assertEqual(currents, sorted(currents))

    def test_person_net_rejects_nonlinear_links(self):
        scenario = {
            "person_model": {"gender_prior_strength": 0},
            "персонажи": [
                {"id": "boss", "type": "adult", "gender": "female"},
                {"id": "worker", "type": "adult", "gender": "male"},
            ],
            "связи_персонажей": [{
                "from": "boss",
                "to": "worker",
                "quality": 0.8,
                "element_type": "MOSFET",
                "gate": 0.8,
            }],
            "отношения": {
                "напряженность": 0.2,
                "частота_событий": 1.0,
                "накопленная_память": 0.1
            },
            "связь": {
                "качество_проводника": 0.8,
                "усиление_эмоций": 1.0,
                "фильтр_критического_мышления": 0.8,
                "усиление_антенны": 0.2,
                "внешний_фон": 0.1,
                "сброс_через_антенну": 0.3,
                "согласование_собеседника": 0.8
            },
            "финансы": {
                "доходы_в_месяц": [1.0],
                "ипотека_в_месяц": 0.0,
                "базовые_расходы_в_месяц": 0.5,
                "прочие_расходы_в_месяц": 0.1,
                "резерв": 3.0,
                "долг_по_ипотеке": 0.0,
                "ставка_годовая": 0.0
            }
        }
        with self.assertRaises(core.ScenarioError):
            pnet.solve_network(scenario)

    def test_invalid_element_type_rejected(self):
        with self.assertRaises(core.ScenarioError):
            pm.compile_person_network({
                "персонажи": [
                    {"id": "a", "type": "adult"},
                    {"id": "b", "type": "adult"},
                ],
                "связи_персонажей": [{
                    "from": "a",
                    "to": "b",
                    "quality": 0.8,
                    "element_type": "MAGIC",
                }],
            })


if __name__ == "__main__":
    unittest.main()
