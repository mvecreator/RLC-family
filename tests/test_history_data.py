import unittest
from pathlib import Path

from simulator import history_data as hd


ROOT = Path(__file__).resolve().parents[1]


class HistoryDataTests(unittest.TestCase):
    def test_retrospective_solo_history_is_not_blind_evidence(self):
        record = hd.load_json(
            ROOT / "examples" / "history_solo_retrospective_sleep.json"
        )
        status = hd.blind_eligibility(record)
        self.assertFalse(status["eligible"])
        self.assertEqual(
            status["evidence_class"],
            "retrospective_hypothesis_record",
        )
        self.assertIn("not_prospective", status["reasons"])
        self.assertIn(
            "future_outcome_already_known",
            status["reasons"],
        )
        self.assertIn(
            "missing_or_invalid_preregistration",
            status["reasons"],
        )

    def test_synthetic_prospective_demo_is_blind_eligible(self):
        record = hd.load_json(
            ROOT / "examples" / "history_prospective_demo.json"
        )
        status = hd.blind_eligibility(record)
        self.assertTrue(status["eligible"])
        self.assertEqual(status["reasons"], [])

    def test_split_hides_future_suffix_from_predictor(self):
        record = hd.load_json(
            ROOT / "examples" / "history_prospective_demo.json"
        )
        split = hd.split_blind_record(record)
        self.assertEqual([x["day"] for x in split["prefix"]], [0,1,2,3,4])
        self.assertEqual([x["day"] for x in split["hidden_suffix"]], [5,6,7])
        self.assertFalse(
            split["contract"]["hidden_suffix_available_to_predictor"]
        )

    def test_template_is_never_blind_eligible(self):
        record = hd.load_json(
            ROOT / "examples" / "history_prospective_template.json"
        )
        status = hd.blind_eligibility(record)
        self.assertFalse(status["eligible"])
        self.assertIn("template_record", status["reasons"])

    def test_noncontemporaneous_rows_block_blind_eligibility(self):
        record = hd.load_json(
            ROOT / "examples" / "history_prospective_demo.json"
        )
        record["observations"][2]["recorded_contemporaneously"] = False
        status = hd.blind_eligibility(record)
        self.assertFalse(status["eligible"])
        self.assertIn(
            "noncontemporaneous_observations",
            status["reasons"],
        )


if __name__ == "__main__":
    unittest.main()
