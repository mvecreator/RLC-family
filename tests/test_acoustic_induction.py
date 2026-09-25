import copy
import unittest
from pathlib import Path

from simulator import acoustic_induction as ai
from simulator import acoustic_induction_calibration as cal


ROOT = Path(__file__).resolve().parents[1]


class AcousticInductionTests(unittest.TestCase):
    def test_calibration_suite_passes(self):
        result = cal.suite()
        self.assertTrue(result["all_pass"])
        self.assertEqual(result["passed"], 16)

    def test_constant_source_has_no_derivative_term(self):
        scenario = {
            "acoustic_induction": {
                "couplings": [{
                    "id": "wall",
                    "source_zone": "z",
                    "target_person": "central",
                    "transmission": 0.4,
                    "derivative_coupling_days": 0.004,
                }]
            }
        }
        timeline = {
            "acoustic_sources": [{
                "id": "steady",
                "source_zone": "z",
                "waveform": "constant",
                "amplitude": 0.5,
                "at_day": 0.0,
                "duration_days": 1.0,
                "edge_days": 0.01,
            }]
        }
        compiled = ai.compile_acoustic(
            scenario, timeline, {"central"}
        )
        drive = ai.drive_at(compiled, 0.5, {"central"})
        self.assertAlmostEqual(
            drive["direct"]["central"], 0.2, places=12
        )
        self.assertAlmostEqual(
            drive["inductive"]["central"], 0.0, places=12
        )

    def test_pulse_derivative_changes_sign(self):
        scenario = {
            "acoustic_induction": {
                "couplings": [{
                    "id": "wall",
                    "source_zone": "z",
                    "target_person": "central",
                    "transmission": 0.0,
                    "derivative_coupling_days": 0.004,
                }]
            }
        }
        timeline = {
            "acoustic_sources": [{
                "id": "p",
                "source_zone": "z",
                "waveform": "pulse",
                "amplitude": 0.5,
                "at_day": 0.2,
                "duration_days": 0.2,
                "edge_days": 0.02,
            }]
        }
        compiled = ai.compile_acoustic(
            scenario, timeline, {"central"}
        )
        self.assertGreater(
            ai.drive_at(compiled, 0.21, {"central"})[
                "inductive"
            ]["central"],
            0.0,
        )
        self.assertLess(
            ai.drive_at(compiled, 0.39, {"central"})[
                "inductive"
            ]["central"],
            0.0,
        )

    def test_unknown_target_rejected(self):
        scenario = {
            "acoustic_induction": {
                "couplings": [{
                    "id": "wall",
                    "source_zone": "z",
                    "target_person": "unknown",
                    "transmission": 0.4,
                    "derivative_coupling_days": 0.004,
                }]
            }
        }
        with self.assertRaises(ValueError):
            ai.compile_acoustic(
                scenario,
                {"acoustic_sources": []},
                {"central"},
            )


if __name__ == "__main__":
    unittest.main()
