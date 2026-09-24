import copy
import unittest

from simulator import channel_coupling as cc
from simulator import channel_coupling_calibration as cal
from simulator import link_semiconductor as semi
from simulator import person_model as pm
from simulator import rlc_family_sim as core


class ChannelCouplingTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 15)

    def test_reciprocal_rule_order_is_independent(self):
        a = cal.base_scenario()
        b = copy.deepcopy(a)
        b["channel_couplings"] = list(
            reversed(b["channel_couplings"])
        )

        ira = pm.compile_person_network(a)
        irb = pm.compile_person_network(b)
        index_a = {
            node["id"]: idx for idx, node in enumerate(ira["nodes"])
        }
        index_b = {
            node["id"]: idx for idx, node in enumerate(irb["nodes"])
        }
        va = [0.20, -0.20]
        vb = [0.20, -0.20]

        out_a, _ = cc.apply_couplings(
            ira["links"], va, index_a, ira["channel_couplings"],
            semi, pm.refresh_link_semantics,
        )
        out_b, _ = cc.apply_couplings(
            irb["links"], vb, index_b, irb["channel_couplings"],
            semi, pm.refresh_link_semantics,
        )
        aa = {link["link_id"]: link for link in out_a}
        bb = {link["link_id"]: link for link in out_b}

        self.assertAlmostEqual(
            aa["personal"]["communication_quality"],
            bb["personal"]["communication_quality"],
            places=12,
        )
        self.assertAlmostEqual(
            aa["work"]["reverse_ratio"],
            bb["work"]["reverse_ratio"],
            places=12,
        )

    def test_cross_pair_requires_explicit_opt_in(self):
        links = [
            {
                "link_id": "ab",
                "pair_id": "a->b",
                "element_type": "RESISTIVE",
            },
            {
                "link_id": "bc",
                "pair_id": "b->c",
                "element_type": "RESISTIVE",
            },
        ]
        with self.assertRaises(ValueError):
            cc.compile_couplings({
                "channel_couplings": [{
                    "coupling_id": "x",
                    "source_link_id": "ab",
                    "target_link_id": "bc",
                    "source_signal": "communication_quality",
                    "target_field": "communication_quality",
                    "gain": -0.1,
                }]
            }, links)

    def test_invalid_gate_target_is_rejected(self):
        with self.assertRaises(core.ScenarioError):
            pm.compile_person_network(cal.base_scenario(rules=[{
                "coupling_id": "bad",
                "source_link_id": "work",
                "target_link_id": "personal",
                "source_signal": "power",
                "target_field": "gate",
                "gain": -0.2,
            }]))


    def test_threshold_out_of_range_is_rejected(self):
        with self.assertRaises(core.ScenarioError):
            pm.compile_person_network(cal.base_scenario(rules=[{
                "coupling_id": "bad-threshold",
                "source_link_id": "work",
                "target_link_id": "personal",
                "source_signal": "power",
                "target_field": "communication_quality",
                "threshold": 1.2,
                "gain": -0.2,
            }]))

    def test_gate_source_requires_mosfet(self):
        with self.assertRaises(core.ScenarioError):
            pm.compile_person_network(cal.base_scenario(rules=[{
                "coupling_id": "bad-gate-source",
                "source_link_id": "personal",
                "target_link_id": "work",
                "source_signal": "gate",
                "target_field": "reverse_ratio",
                "gain": 0.2,
            }]))


if __name__ == "__main__":
    unittest.main()
