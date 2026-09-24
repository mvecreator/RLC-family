import copy
import json
import math
import unittest
from pathlib import Path

from simulator import person_network_solver as pns

ROOT=Path(__file__).resolve().parents[1]


class PersonNetworkSolverTests(unittest.TestCase):
    def test_mixed_role_example(self):
        scenario=json.loads(
            (ROOT/"examples"/"person_family_scenario.json").read_text(encoding="utf-8")
        )
        result=pns.solve_network(scenario)
        nodes={n["id"]:n for n in result["nodes"]}
        self.assertGreater(nodes["husband"]["L"],nodes["husband"]["C"])
        self.assertGreater(nodes["wife"]["C"],nodes["wife"]["L"])
        self.assertEqual(result["summary"]["node_count"],4)
        self.assertEqual(result["summary"]["link_count"],6)

    def test_identical_nodes_equal_voltage(self):
        scenario={
            "персонажи":[
                {"id":"a","type":"adult","gender":"male","source_weight":1},
                {"id":"b","type":"adult","gender":"male","source_weight":1},
            ],
            "person_model":{"gender_prior_strength":0},
            "связи_персонажей":[{"from":"a","to":"b","quality":0.7}],
            "отношения":{"напряженность":0.5,"частота_событий":1.0},
            "связь":{"качество_проводника":0.7},
            "финансы":{}
        }
        result=pns.solve_network(scenario)
        a,b=result["nodes"]
        self.assertAlmostEqual(a["voltage_re"],b["voltage_re"],places=12)
        self.assertAlmostEqual(a["voltage_im"],b["voltage_im"],places=12)

    def test_better_link_reduces_voltage_difference(self):
        base={
            "персонажи":[
                {"id":"source","type":"adult","gender":"male","source_weight":1},
                {"id":"receiver","type":"adult","gender":"male","source_weight":0},
            ],
            "person_model":{"gender_prior_strength":0},
            "отношения":{"напряженность":0.6,"частота_событий":1.0},
            "связь":{"качество_проводника":0.7},
            "финансы":{}
        }
        low=copy.deepcopy(base)
        high=copy.deepcopy(base)
        low["связи_персонажей"]=[{"from":"source","to":"receiver","quality":0.2}]
        high["связи_персонажей"]=[{"from":"source","to":"receiver","quality":0.9}]
        rl=pns.solve_network(low)
        rh=pns.solve_network(high)
        def gap(result):
            by={n["id"]:complex(n["voltage_re"],n["voltage_im"]) for n in result["nodes"]}
            return abs(by["source"]-by["receiver"])
        self.assertLess(gap(rh),gap(rl))

    def test_results_finite(self):
        scenario=json.loads(
            (ROOT/"examples"/"person_family_scenario.json").read_text(encoding="utf-8")
        )
        result=pns.solve_network(scenario)
        for node in result["nodes"]:
            for key in ("voltage_re","voltage_im","voltage_abs","phase_deg"):
                self.assertTrue(math.isfinite(node[key]))
        for link in result["links"]:
            self.assertTrue(math.isfinite(link["current_abs"]))


if __name__=="__main__":
    unittest.main()
