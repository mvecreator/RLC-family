import copy
import unittest
from pathlib import Path

from simulator import neighbor_network as nn
from simulator import neighbor_network_calibration as cal
from simulator import rlc_family_sim as core


ROOT = Path(__file__).resolve().parents[1]


class NeighborNetTests(unittest.TestCase):
    def setUp(self):
        self.scenario = cal.load_json(
            ROOT / "examples" / "neighbor_net1_synthetic_scenario.json"
        )
        self.spec = cal.load_json(
            ROOT / "examples" / "neighbor_net1_synthetic_spec.json"
        )

    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 18)

    def test_temporal_alignment_is_not_intent_classifier(self):
        compiled = nn.compile_spec(self.scenario, self.spec)
        t0 = compiled["intervention"]["at_day"]
        pre = nn._window_events(
            compiled,
            t0 - compiled["window_days"],
            t0,
        )
        metrics = nn.event_metrics(
            pre,
            compiled["neighbor_ids"],
            compiled["window_days"],
            compiled["sync_tolerance_days"],
        )
        self.assertGreater(metrics["temporal_alignment_index"], 0.0)
        self.assertFalse(metrics["intent_inferred"])

    def test_intervention_does_not_delete_post_events(self):
        compiled = nn.compile_spec(self.scenario, self.spec)
        t0 = compiled["intervention"]["at_day"]
        post = [
            e["id"] for e in compiled["observed_stimuli"]
            if e["at_day"] >= t0
        ]
        self.assertEqual(
            post,
            ["post-n2-01", "post-n1-01", "post-n3-01"],
        )

    def test_unknown_neighbor_source_rejected(self):
        spec = copy.deepcopy(self.spec)
        spec["observed_stimuli"][0]["source_id"] = "unknown"
        with self.assertRaises(core.ScenarioError):
            nn.compile_spec(self.scenario, spec)

    def test_desynchronization_preserves_exposure_area(self):
        compiled = nn.compile_spec(self.scenario, self.spec)
        t0 = compiled["intervention"]["at_day"]
        window = compiled["window_days"]
        original = nn._window_events(compiled, t0 - window, t0)
        remapped = [
            event
            for event in nn.desynchronized_pre_stimuli(compiled)
            if t0 - window <= event["at_day"] < t0
        ]
        self.assertEqual(len(original), len(remapped))
        self.assertAlmostEqual(
            sum(e["amplitude"] * e["duration_days"] for e in original),
            sum(e["amplitude"] * e["duration_days"] for e in remapped),
            places=12,
        )


    def test_household_group_input_preserves_total_amplitude(self):
        scenario = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_scenario.json"
        )
        spec = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_spec.json"
        )
        compiled = nn.compile_spec(scenario, spec)
        event = next(
            e for e in compiled["observed_stimuli"]
            if e["source_group_id"] == "household2_family3"
        )
        timeline = nn.timeline_from_spec(
            compiled,
            include_relief=False,
            stimuli=[event],
        )
        expanded = [
            e for e in timeline["events"]
            if e["id"].startswith(event["id"])
        ]
        self.assertEqual(len(expanded), 3)
        self.assertAlmostEqual(
            sum(e["drive_add"] for e in expanded),
            event["amplitude"],
            places=12,
        )

    def test_household_probe_compares_equal_total_input(self):
        scenario = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_scenario.json"
        )
        spec = cal.load_json(
            ROOT / "examples" / "neighbor_net1_households_spec.json"
        )
        result = nn.analyze(scenario, spec)
        households = result["household_transfer_probe"]["households"]
        amplitudes = {
            round(item["total_input_amplitude"], 12)
            for item in households.values()
        }
        self.assertEqual(len(amplitudes), 1)
        self.assertEqual(
            set(result["household_topology_effect"]),
            {
                "household1_solo",
                "household2_family3",
                "household3_couple",
            },
        )


if __name__ == "__main__":
    unittest.main()
