import json
import math
import unittest
from pathlib import Path

from simulator import person_solo_calibration as solo


ROOT = Path(__file__).resolve().parents[1]


class PersonSoloCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(ROOT / "examples" / "person_solo_scenario.json")
        self.obs = solo.load_json(ROOT / "examples" / "person_solo_wake_observations.json")
        self.hist = solo.load_json(ROOT / "examples" / "person_solo_historical_timeline.json")
        self.current = solo.load_json(ROOT / "examples" / "person_solo_current_timeline.json")

    def test_single_node_no_links(self):
        node, ir = solo.require_single_person(self.scenario)
        self.assertEqual(node["id"], "solo")
        self.assertEqual(len(ir["nodes"]), 1)
        self.assertEqual(ir["links"], [])

    def test_exact_25_hour_drift_fit(self):
        fit = solo.estimate_wake_period(self.obs)
        self.assertAlmostEqual(fit["wake_offset_slope_hours_per_calendar_day"], 1.0, places=12)
        self.assertAlmostEqual(fit["effective_period_hours"], 25.0, places=12)
        self.assertAlmostEqual(fit["fit_rmse_hours"], 0.0, places=12)

    def test_biphasic_sleep_constraint(self):
        wake = solo.estimate_wake_period(self.obs)
        s = solo.estimate_sleep_architecture(
            self.obs, wake["effective_period_hours"]
        )
        self.assertTrue(s["gradual_split"])
        self.assertTrue(s["requires_split_state"])
        self.assertEqual(s["final_sleep_bout_count"], 2)
        self.assertAlmostEqual(s["final_bout_sleep_fraction_each"], 0.5, places=12)
        self.assertAlmostEqual(s["inter_bout_wake_gap_hours_midpoint"], 2.5, places=12)
        self.assertAlmostEqual(s["inter_bout_gap_fraction_of_cycle_min"], 2/25, places=12)
        self.assertAlmostEqual(s["inter_bout_gap_fraction_of_cycle_max"], 3/25, places=12)
        self.assertIsNone(s["total_sleep_hours_per_cycle"])
        self.assertIsNone(s["each_bout_hours_if_total_known"])

    def test_person_rlc_is_positive_and_underdamped(self):
        node, _ = solo.require_single_person(self.scenario)
        cal = solo.rlc_calibration(node, 25.0)
        self.assertGreater(cal["R"], 0)
        self.assertGreater(cal["C"], 0)
        self.assertGreater(cal["L"], 0)
        self.assertGreater(cal["hours_per_model_time_unit"], 0)
        self.assertGreater(cal["parallel_damping_ratio"], 0)
        self.assertLess(cal["parallel_damping_ratio"], 1)

    def test_minimal_budget_is_break_even_but_thin(self):
        b = solo.budget_summary(self.scenario)
        self.assertAlmostEqual(b["net_monthly_normalized"], 0.0, places=12)
        self.assertAlmostEqual(b["runway_months"], 0.20, places=12)
        self.assertGreater(b["financial_stress"], 0)

    def test_current_profile_has_fewer_coffee_events(self):
        a = solo.forcing_area(self.hist)
        b = solo.forcing_area(self.current)
        self.assertEqual(a["project_event_count"], b["project_event_count"])
        self.assertGreater(a["coffee_event_count"], b["coffee_event_count"])
        self.assertGreater(a["event_drive_area"], b["event_drive_area"])

    def test_full_calibration_is_finite_and_deterministic(self):
        a = solo.calibrate(self.scenario, self.obs, self.hist, self.current)
        b = solo.calibrate(self.scenario, self.obs, self.hist, self.current)
        self.assertEqual(a, b)
        self.assertTrue(math.isfinite(a["historical_forcing"]["peak_voltage_abs"]))
        self.assertTrue(math.isfinite(a["current_forcing"]["peak_voltage_abs"]))


if __name__ == "__main__":
    unittest.main()
