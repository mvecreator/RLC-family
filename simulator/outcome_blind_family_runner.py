#!/usr/bin/env python3
"""Run OUTCOME-BLIND1 on full PERSON-FAMILY-SAFETY1 trajectories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulator import outcome_blind as blind
from simulator import person_family_safety as family_safety


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_case(case, root=ROOT):
    scenario = load_json(root / case["scenario"])
    timeline = load_json(root / case["timeline"])
    full = family_safety.assess(scenario, timeline)
    result = blind.run_blind(
        full["trajectory"],
        cutoff_day=float(case["cutoff_day"]),
        horizon_days=float(case["horizon_days"]),
        lookback_days=float(case.get("lookback_days", 3.0)),
    )
    result["case_name"] = case["name"]
    result["scenario"] = case["scenario"]
    result["timeline"] = case["timeline"]
    return result


def run_spec(spec, root=ROOT):
    results = [run_case(case, root=root) for case in spec["cases"]]

    def collect(side, group):
        scores = [
            item[side][f"{group}_direction_score"]
            for item in results
            if item[side][f"{group}_direction_score"] is not None
        ]
        correct = sum(x["correct"] for x in scores)
        total = sum(x["total"] for x in scores)
        return {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else None,
        }

    return {
        "model_version": blind.VERSION,
        "cases": results,
        "aggregate": {
            "model_person_direction": collect("model", "person"),
            "baseline_person_direction": collect(
                "persistence_baseline", "person"
            ),
            "model_link_direction": collect("model", "link"),
            "baseline_link_direction": collect(
                "persistence_baseline", "link"
            ),
        },
        "claim_boundary": (
            "These cases use model-generated trajectories. They test blind "
            "evaluation mechanics and internal directional prediction, not "
            "external real-world predictive validity."
        ),
    }


def main():
    p = argparse.ArgumentParser(description="Run OUTCOME-BLIND1 family cases")
    p.add_argument(
        "spec",
        nargs="?",
        default=str(ROOT / "examples" / "outcome_blind_family_cases.json"),
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    result = run_spec(load_json(args.spec))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
