import unittest
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_solo_calibration as solo
from simulator import person_time_solver as pts
from simulator import thermal_recovery as therm


ROOT = Path(__file__).resolve().parents[1]


class LinkSemiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = solo.load_json(
            ROOT / "examples" / "link_semi1_work_social_scenario.json"
        )
        self.timeline = solo.load_json(
            ROOT / "examples" / "link_semi1_work_social_timeline.json"
        )

    def test_timeline_exposes_gate_changes(self):
        result = pts.simulate_person_timeline(
            self.scenario,
            self.timeline,
        )

        def sample_at(day):
            return min(
                result["samples"],
                key=lambda row: abs(float(row["day"]) - day),
            )

        def work_link(sample):
            return next(
                link for link in sample["links"]
                if {link["from"], link["to"]}
                == {"employer", "employee"}
            )

        open_link = work_link(sample_at(2.0))
        relief_link = work_link(sample_at(8.0))

        self.assertEqual(open_link["element_type"], "MOSFET")
        self.assertAlmostEqual(open_link["gate"], 0.90, places=12)
        self.assertAlmostEqual(relief_link["gate"], 0.20, places=12)

    def test_family_safety_preserves_nonlinear_vi_power(self):
        result = family_safety.assess(
            self.scenario,
            self.timeline,
        )
        row = result["trajectory"][10]

        work = row["links"]["employee->employer"]
        self.assertEqual(work["element_type"], "MOSFET")
        self.assertAlmostEqual(
            work["dissipation_power_proxy"],
            abs(work["delta_v_raw"] * work["current_abs_raw"]),
            places=12,
        )

    def test_resistive_link_retains_i2r_identity(self):
        result = family_safety.assess(
            self.scenario,
            self.timeline,
        )
        row = result["trajectory"][10]
        coworker = row["links"]["coworker->employee"]

        vi = abs(
            coworker["delta_v_raw"]
            * coworker["current_abs_raw"]
        )
        i2r = (
            coworker["current_abs_raw"]
            * coworker["current_abs_raw"]
            * coworker["R_link"]
        )
        self.assertAlmostEqual(vi, i2r, places=10)
        self.assertAlmostEqual(
            coworker["dissipation_power_proxy"],
            vi,
            places=10,
        )

    def test_thermal_layer_accepts_mixed_link_types(self):
        family = family_safety.assess(
            self.scenario,
            self.timeline,
        )
        thermal = therm.integrate_thermal(
            self.scenario,
            family["trajectory"],
        )
        self.assertTrue(thermal)
        self.assertIn("employee->employer", thermal[-1]["links"])
        self.assertIn("coworker->employee", thermal[-1]["links"])
        self.assertIn("employee->friend", thermal[-1]["links"])


if __name__ == "__main__":
    unittest.main()
