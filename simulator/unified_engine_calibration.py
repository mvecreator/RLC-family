#!/usr/bin/env python3
"""UNIFIED-ENGINE-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from simulator import unified_engine as engine


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _node(sample, pid):
    return next(row for row in sample["nodes"] if row["id"] == pid)


def suite():
    scenario = load_json(
        ROOT / "examples" / "acoustic_induction1_households_scenario.json"
    )
    spec = load_json(
        ROOT / "examples" / "unified_engine1_spec.json"
    )
    full_spec = load_json(
        ROOT / "examples" / "unified_engine1_full_spec.json"
    )

    compiled_a = engine.compile_engine(scenario, spec)
    compiled_b = engine.compile_engine(scenario, spec)
    result = engine.run_engine(scenario, spec)

    full_compiled = engine.compile_engine(scenario, full_spec)

    changed = copy.deepcopy(scenario)
    central = next(
        p for p in changed["персонажи"] if p["id"] == "central"
    )
    central["rhythm"]["schedule_lock"] = (
        float(central["rhythm"]["schedule_lock"]) + 0.01
    )
    changed_compiled = engine.compile_engine(changed, spec)

    compile_only = engine.run_engine(scenario, {})

    contract = compiled_a["compiled_contract"]
    features = result["features_present"]
    outputs = result["outputs"]
    timeline = outputs["timeline"]
    family = outputs["family_safety"]
    thermal = outputs["thermal_recovery"]
    perception = outputs["perception_identification"][
        "central-brief-observer"
    ]

    first_central = _node(timeline["samples"][0], "central")

    checks = {
        "UE01_INPUT_DIGEST_IS_DETERMINISTIC": (
            compiled_a["input_digest"] == compiled_b["input_digest"]
        ),
        "UE02_COMPILED_CONTRACT_DIGEST_IS_DETERMINISTIC": (
            compiled_a["compiled_contract_digest"]
            == compiled_b["compiled_contract_digest"]
        ),
        "UE03_CAPABILITY_MANIFEST_CONTAINS_MERGED_STACK": (
            set([
                "MULTI_LINK_PARALLEL_CHANNELS",
                "CHANNEL_COUPLING",
                "RHYTHM_25H1",
                "ACOUSTIC_INDUCTION1",
                "NEIGHBOR_NET1_OPTIONAL",
                "PERCEPTION_ID1_OPTIONAL",
            ]).issubset(set(result["capabilities"]))
        ),
        "UE04_PERSON2_GRAPH_COMPILES_ALL_HOUSEHOLD_MEMBERS": (
            len(contract["person_ir"]["nodes"]) == 7
        ),
        "UE05_25H_RHYTHM_IS_VISIBLE_IN_COMPILED_GRAPH": (
            "central" in features["rhythm_node_ids"]
            and abs(
                next(
                    n for n in contract["person_ir"]["nodes"]
                    if n["id"] == "central"
                )["rhythm"]["intrinsic_day_hours"] - 25.0
            ) < 1e-12
        ),
        "UE06_ACOUSTIC_CONTRACT_COMPILES_ONCE": (
            features["acoustic_coupling_count"] == 3
            and features["acoustic_source_count"] == 5
        ),
        "UE07_TIMELINE_RUN_IS_PRESENT_AND_12_DAYS": (
            abs(timeline["integration"]["days"] - 12.0) < 1e-12
            and len(timeline["samples"]) > 2
        ),
        "UE08_FAMILY_REUSES_TIMELINE_SAMPLE_GRID": (
            len(family["trajectory"]) == len(timeline["samples"])
            and family["timeline_model_version"] == timeline["model_version"]
        ),
        "UE09_THERMAL_REUSES_FAMILY_TRAJECTORY_GRID": (
            len(thermal["trajectory"]) == len(family["trajectory"])
        ),
        "UE10_ACOUSTIC_AND_RHYTHM_PROVENANCE_SURVIVE_UNIFIED_RUN": (
            "acoustic_total_drive" in first_central
            and "rhythm" in first_central
            and abs(
                first_central["rhythm"]["intrinsic_day_hours"] - 25.0
            ) < 1e-12
        ),
        "UE11_PERCEPTION_PROJECTION_RUNS_WITH_BOUNDARY": (
            perception["target_person_id"] == "central"
            and perception["real_world_belief_inference"] is False
            and perception["brief_identifiability"]["candidate_count"] >= 1
        ),
        "UE12_NEIGHBOR_PROJECTION_IS_OPTIONAL_AND_COMPILED_EXPLICITLY": (
            compiled_a["compiled_contract"][
                "features_present"
            ]["neighbor_projection_requested"] is False
            and full_compiled["compiled_contract"][
                "features_present"
            ]["neighbor_projection_requested"] is True
        ),
        "UE13_SUMMARY_REFERENCES_REAL_DOWNSTREAM_OUTPUTS": (
            result["summary"]["family_safety"]["highest_load_person"]
            == family["summary"]["highest_load_person"]
            and result["summary"]["thermal_recovery"][
                "highest_peak_heat_person"
            ] in thermal["summary"]["persons"]
        ),
        "UE14_INPUT_CHANGE_CHANGES_REPRODUCIBILITY_DIGEST": (
            changed_compiled["input_digest"]
            != compiled_a["input_digest"]
        ),
        "UE15_COMPILE_ONLY_MODE_DOES_NOT_INVENT_TRAJECTORIES": (
            "person_ir" in compile_only["outputs"]
            and "timeline" not in compile_only["outputs"]
            and "family_safety" not in compile_only["outputs"]
            and "thermal_recovery" not in compile_only["outputs"]
        ),
        "UE16_INTERPRETATION_BOUNDARY_REMAINS_NONCLINICAL_NONCAUSAL": (
            "not medical" in result["interpretation_boundary"]
            and "causal" in result["interpretation_boundary"]
            and "intent" in result["interpretation_boundary"]
        ),
    }

    return {
        "benchmark": "UNIFIED-ENGINE-CAL1",
        "engine_version": engine.VERSION,
        "reference": {
            "input_digest": compiled_a["input_digest"],
            "compiled_contract_digest": compiled_a[
                "compiled_contract_digest"
            ],
            "capabilities": result["capabilities"],
            "features_present": features,
            "timeline_sample_count": len(timeline["samples"]),
            "family_trajectory_count": len(family["trajectory"]),
            "thermal_trajectory_count": len(thermal["trajectory"]),
            "perception_brief_candidate_count": perception[
                "brief_identifiability"
            ]["candidate_count"],
            "summary": result["summary"],
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
