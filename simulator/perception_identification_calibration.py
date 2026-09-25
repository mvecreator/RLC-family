#!/usr/bin/env python3
"""PERCEPTION-ID-CAL1 calibration gates."""

from __future__ import annotations

import json
from pathlib import Path

from simulator import perception_identification as pid


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def suite():
    scenario = load_json(
        ROOT / "examples" / "perception_id1_synthetic_target.json"
    )
    low_spec = load_json(
        ROOT / "examples" / "perception_id1_low_prior_spec.json"
    )
    high_spec = load_json(
        ROOT / "examples" / "perception_id1_high_prior_spec.json"
    )

    low = pid.analyze(scenario, low_spec)
    high = pid.analyze(scenario, high_spec)

    actual = low["actual_theta"]
    low_hat = low["perceived_theta_from_brief_window"]
    high_hat = high["perceived_theta_from_brief_window"]

    checks = {
        "PI01_SYNTHETIC_TARGET_IS_LOW_C_HIGH_RL_VS_NOMINAL": (
            low["actual_vs_nominal"]["C"] < 1.0
            and low["actual_vs_nominal"]["R"] > 1.0
            and low["actual_vs_nominal"]["L"] > 1.0
        ),
        "PI02_BRIEF_WINDOW_IS_AMBIGUOUS": (
            low["brief_identifiability"]["candidate_count"] > 1
        ),
        "PI03_BRIEF_WINDOW_IDENTIFIES_C_BETTER_THAN_RL": (
            abs(low["brief_identifiability"]["C_span"]["ratio"] - 1.0)
            < 1e-12
            and low["brief_identifiability"]["R_span"]["ratio"] > 1.2
            and low["brief_identifiability"]["L_span"]["ratio"] > 2.0
        ),
        "PI04_LONG_WINDOW_COLLAPSES_AMBIGUITY": (
            low["full_identifiability"]["candidate_count"]
            < low["brief_identifiability"]["candidate_count"]
            and low["full_identifiability"]["candidate_count"] == 1
        ),
        "PI05_LOW_RL_PRIOR_UNDERESTIMATES_PERSISTENCE_PARAMETERS": (
            low_hat["R"] < actual["R"]
            and low_hat["L"] < actual["L"]
            and abs(low_hat["C"] - actual["C"]) < 1e-12
        ),
        "PI06_HIGH_RL_PRIOR_OVERESTIMATES_PERSISTENCE_PARAMETERS": (
            high_hat["R"] > actual["R"]
            and high_hat["L"] > actual["L"]
            and abs(high_hat["C"] - actual["C"]) < 1e-12
        ),
        "PI07_SAME_TRACE_SUPPORTS_OPPOSITE_PRIOR_BIASES": (
            low_hat["R"] < high_hat["R"]
            and low_hat["L"] < high_hat["L"]
        ),
        "PI08_LOW_PRIOR_PREDICTS_FASTER_DECAY_THAN_ACTUAL": (
            low["strategy_probe"]["perceived_residual_fraction"]
            < low["strategy_probe"]["actual_residual_fraction"]
        ),
        "PI09_HIGH_PRIOR_PREDICTS_SLOWER_DECAY_THAN_ACTUAL": (
            high["strategy_probe"]["perceived_residual_fraction"]
            > high["strategy_probe"]["actual_residual_fraction"]
        ),
        "PI10_LOW_PRIOR_CHOOSES_DIFFERENT_REPEAT_POLICY": (
            low["strategy_probe"]["policy_mismatch"] is True
            and low["strategy_probe"]["policy_from_perceived_model"]
            == "repeat_short_input_assuming_decay"
            and low["strategy_probe"]["policy_if_actual_model_were_known"]
            == "avoid_or_space_repeated_input"
        ),
        "PI11_HIGH_PRIOR_DOES_NOT_SHARE_LOW_PRIOR_POLICY_ERROR": (
            high["strategy_probe"]["policy_mismatch"] is False
            and high["strategy_probe"]["policy_from_perceived_model"]
            == "avoid_or_space_repeated_input"
        ),
        "PI12_LOW_PRIOR_UNDERPREDICTS_REPEATED_INPUT_PEAK": (
            low["repeated_input_prediction_error"][
                "predicted_peak_abs_voltage"
            ]
            < low["repeated_input_prediction_error"][
                "actual_peak_abs_voltage"
            ]
        ),
        "PI13_RESULTS_DO_NOT_CLAIM_REAL_OBSERVER_BELIEFS": (
            low["real_world_belief_inference"] is False
            and high["real_world_belief_inference"] is False
            and "does not show what any real observer believed"
            in low["interpretation_boundary"]
        ),
        "PI14_GROUND_TRUTH_IS_EXPLICITLY_SYNTHETIC": (
            low["synthetic_ground_truth_known"] is True
            and high["synthetic_ground_truth_known"] is True
        ),
    }

    return {
        "benchmark": "PERCEPTION-ID-CAL1",
        "model_version": pid.VERSION,
        "reference": {
            "actual_theta": actual,
            "actual_vs_nominal": low["actual_vs_nominal"],
            "brief_identifiability": low["brief_identifiability"],
            "full_identifiability": low["full_identifiability"],
            "low_prior_perceived_theta": low_hat,
            "high_prior_perceived_theta": high_hat,
            "low_prior_strategy_probe": low["strategy_probe"],
            "high_prior_strategy_probe": high["strategy_probe"],
            "low_prior_repeated_input_error": low[
                "repeated_input_prediction_error"
            ],
            "high_prior_repeated_input_error": high[
                "repeated_input_prediction_error"
            ],
        },
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
