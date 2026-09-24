#!/usr/bin/env python3
"""Synthetic OUTCOME-BLIND1 calibration.

The synthetic cases validate blindness and scoring. They are not evidence that
the family model predicts real human outcomes.
"""

from __future__ import annotations

import json

from simulator import outcome_blind as blind


def make_row(day, person_state, person_load, link_state, link_load):
    return {
        "day": float(day),
        "persons": {
            "p": {
                "accumulated_load": float(person_state),
                "combined": float(person_load),
            }
        },
        "links": {
            "p->q": {
                "accumulated_strain": float(link_state),
                "combined": float(link_load),
            }
        },
    }


def generate_case(
    prefix_load,
    future_load,
    days=12,
    initial_person_state=0.20,
    initial_link_state=0.15,
):
    rows = []
    ps = float(initial_person_state)
    ls = float(initial_link_state)
    for day in range(days + 1):
        load = prefix_load if day <= 5 else future_load
        rows.append(make_row(day, ps, load, ls, load))
        ps = blind.project_accumulator(
            ps, load, 1.0, blind.PERSON_A, blind.PERSON_R
        )
        ls = blind.project_accumulator(
            ls, load, 1.0, blind.LINK_A, blind.LINK_R
        )
    return rows


def suite():
    accumulating = generate_case(0.55, 0.55)
    recovering = generate_case(
        0.05,
        0.05,
        initial_person_state=0.70,
        initial_link_state=0.70,
    )

    # Same prefix as accumulating, but future load reverses after cutoff.
    hidden_reversal = generate_case(0.55, 0.02)

    acc = blind.run_blind(accumulating, cutoff_day=5, horizon_days=5)
    rec = blind.run_blind(recovering, cutoff_day=5, horizon_days=5)
    rev = blind.run_blind(hidden_reversal, cutoff_day=5, horizon_days=5)

    # Strong blindness check: prediction must be identical when only suffix differs.
    p1, _ = blind.split_rows(accumulating, 5, 5)
    p2, _ = blind.split_rows(hidden_reversal, 5, 5)
    pred1 = blind.predict_prefix(p1, 5)
    pred2 = blind.predict_prefix(p2, 5)

    model_correct = (
        acc["model"]["person_direction_score"]["correct"]
        + rec["model"]["person_direction_score"]["correct"]
        + rev["model"]["person_direction_score"]["correct"]
    )
    baseline_correct = (
        acc["persistence_baseline"]["person_direction_score"]["correct"]
        + rec["persistence_baseline"]["person_direction_score"]["correct"]
        + rev["persistence_baseline"]["person_direction_score"]["correct"]
    )

    checks = {
        "OB01_PREFIX_ONLY": (
            acc["blindness_contract"]["prediction_future_rows_seen"] == 0
            and rev["blindness_contract"]["prediction_future_rows_seen"] == 0
        ),
        "OB02_SUFFIX_MUTATION_CANNOT_CHANGE_PREDICTION": pred1 == pred2,
        "OB03_ACCUMULATION_DIRECTION": (
            acc["model"]["actual"]["persons"]["p"]["direction"]
            == "ACCUMULATING"
            and acc["model"]["prediction"]["persons"]["p"]["direction"]
            == "ACCUMULATING"
        ),
        "OB04_RECOVERY_DIRECTION": (
            rec["model"]["actual"]["persons"]["p"]["direction"]
            == "RECOVERING"
            and rec["model"]["prediction"]["persons"]["p"]["direction"]
            == "RECOVERING"
        ),
        "OB05_HIDDEN_REVERSAL_CAN_FAIL": (
            rev["model"]["actual"]["persons"]["p"]["direction"]
            == "RECOVERING"
            and rev["model"]["prediction"]["persons"]["p"]["direction"]
            == "ACCUMULATING"
        ),
        "OB06_MODEL_SCORE_EXPOSED": model_correct >= 0,
        "OB07_BASELINE_SCORE_EXPOSED": baseline_correct >= 0,
        "OB08_NO_PERFECT_SCORE_REQUIRED": (
            rev["model"]["person_direction_score"]["accuracy"] < 1.0
        ),
    }

    return {
        "model_version": blind.VERSION,
        "cases": {
            "accumulating": acc,
            "recovering": rec,
            "hidden_reversal": rev,
        },
        "aggregate_person_correct": {
            "model": model_correct,
            "persistence_baseline": baseline_correct,
            "total_case_entities": 3,
        },
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
        "scientific_boundary": (
            "Passing this suite validates blindness/scoring mechanics, not "
            "real-world predictive validity."
        ),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
