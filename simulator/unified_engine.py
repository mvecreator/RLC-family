#!/usr/bin/env python3
"""UNIFIED-ENGINE1: one deterministic façade over the RLC-family stack.

The engine compiles one scenario contract and reuses one PERSON-TIME2 run for
Family Safety and Thermal/Recovery projections. Neighbor and perception
analyses are optional projections over the same scenario.

This module is an engineering/simulation façade. It does not turn project
indices into psychological, medical, or causal facts about real people.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from simulator import person_model as pm
    from simulator import person_time_solver as pts
    from simulator import person_family_safety as family_safety
    from simulator import thermal_recovery as thermal
    from simulator import neighbor_network as neighbor
    from simulator import perception_identification as perception
    from simulator import acoustic_induction as acoustic
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import person_model as pm
    import person_time_solver as pts
    import person_family_safety as family_safety
    import thermal_recovery as thermal
    import neighbor_network as neighbor
    import perception_identification as perception
    import acoustic_induction as acoustic
    import rlc_family_sim as core


VERSION = "RLC-FAMILY-UNIFIED-ENGINE1-0.1"

CAPABILITIES = [
    "PERSON2_RLC_NODES",
    "MULTI_LINK_PARALLEL_CHANNELS",
    "NONLINEAR_LINK_DEVICES",
    "CHANNEL_COUPLING",
    "PERSON_TIME2_RK4",
    "RHYTHM_25H1",
    "ACOUSTIC_INDUCTION1",
    "PERSON_FAMILY_SAFETY1",
    "PERSON_THERM1",
    "RECOVERY_DEBT1",
    "NEIGHBOR_NET1_OPTIONAL",
    "PERCEPTION_ID1_OPTIONAL",
]


def _canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value):
    return "sha256:" + hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _obj(value, name, allow_none=False):
    if value is None and allow_none:
        return None
    if not isinstance(value, dict):
        raise core.ScenarioError(f"{name} must be object")
    return value


def _compile_perception_specs(spec):
    raw = spec.get("perception_specs", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise core.ScenarioError("perception_specs must be list")

    out = []
    seen = set()
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise core.ScenarioError(
                f"perception_specs[{idx}] must be object"
            )
        aid = str(item.get("id", f"perception-{idx+1}")).strip()
        if not aid or aid in seen:
            raise core.ScenarioError(
                "perception analysis ids must be unique and non-empty"
            )
        seen.add(aid)
        pspec = item.get("spec")
        if not isinstance(pspec, dict):
            raise core.ScenarioError(
                f"{aid}.spec must be object"
            )
        out.append({"id": aid, "spec": pspec})
    return out


def compile_engine(scenario, engine_spec):
    _obj(scenario, "scenario")
    spec = _obj(engine_spec, "engine_spec")

    person_ir = pm.compile_person_network(scenario)
    if person_ir.get("mode") != "PERSON2":
        raise core.ScenarioError(
            "UNIFIED-ENGINE1 requires a PERSON2 scenario"
        )

    timeline = spec.get("timeline")
    if timeline is not None and not isinstance(timeline, dict):
        raise core.ScenarioError("engine_spec.timeline must be object")

    relationship_flags = spec.get("relationship_flags")
    if relationship_flags is not None and not isinstance(
        relationship_flags, dict
    ):
        raise core.ScenarioError(
            "engine_spec.relationship_flags must be object"
        )

    neighbor_spec = spec.get("neighbor_spec")
    if neighbor_spec is not None and not isinstance(neighbor_spec, dict):
        raise core.ScenarioError(
            "engine_spec.neighbor_spec must be object"
        )

    perception_specs = _compile_perception_specs(spec)

    node_ids = [node["id"] for node in person_ir["nodes"]]

    if timeline is None:
        acoustic_ir = {
            "model_version": acoustic.VERSION,
            "couplings": [],
            "sources": [],
        }
    else:
        try:
            acoustic_ir = acoustic.compile_acoustic(
                scenario,
                timeline,
                set(node_ids),
            )
        except ValueError as e:
            raise core.ScenarioError(
                f"acoustic_induction: {e}"
            ) from e

    links = person_ir.get("links", [])
    channel_kinds = sorted({
        str(link.get("channel_kind", "generic"))
        for link in links
    })
    element_types = sorted({
        str(link.get("element_type", "RESISTIVE"))
        for link in links
    })

    rhythm_nodes = [
        node["id"]
        for node in person_ir["nodes"]
        if bool((node.get("rhythm") or {}).get("enabled", False))
    ]

    features_present = {
        "parallel_link_pairs": sorted({
            str(link.get("pair_id"))
            for link in links
            if int(link.get("parallel_branch_count", 1)) > 1
        }),
        "nonlinear_link_ids": sorted([
            str(link.get("link_id"))
            for link in links
            if bool(link.get("nonlinear", False))
        ]),
        "channel_coupling_count": len(
            person_ir.get("channel_couplings", [])
        ),
        "rhythm_node_ids": rhythm_nodes,
        "acoustic_coupling_count": len(
            acoustic_ir.get("couplings", [])
        ),
        "acoustic_source_count": len(
            acoustic_ir.get("sources", [])
        ),
        "channel_kinds": channel_kinds,
        "element_types": element_types,
        "neighbor_projection_requested": neighbor_spec is not None,
        "perception_projection_count": len(perception_specs),
    }

    compiled_contract = {
        "engine_version": VERSION,
        "component_versions": {
            "person_model": pm.VERSION,
            "person_time": pts.VERSION,
            "family_safety": family_safety.VERSION,
            "thermal_recovery": thermal.VERSION,
            "neighbor_network": neighbor.VERSION,
            "perception_identification": perception.VERSION,
            "acoustic_induction": acoustic.VERSION,
        },
        "capabilities": list(CAPABILITIES),
        "person_ir": person_ir,
        "acoustic_ir": acoustic_ir,
        "features_present": features_present,
        "timeline_present": timeline is not None,
        "neighbor_spec_present": neighbor_spec is not None,
        "perception_analysis_ids": [
            item["id"] for item in perception_specs
        ],
    }

    return {
        "compiled_contract": compiled_contract,
        "timeline": timeline,
        "relationship_flags": relationship_flags,
        "neighbor_spec": neighbor_spec,
        "perception_specs": perception_specs,
        "input_digest": _digest({
            "scenario": scenario,
            "engine_spec": engine_spec,
        }),
        "compiled_contract_digest": _digest(compiled_contract),
    }


def _family_from_timeline(scenario, timeline_result, flags):
    rows = family_safety.integrate_trajectory(
        timeline_result,
        scenario=scenario,
    )
    return {
        "model_version": family_safety.VERSION,
        "scenario_name": timeline_result["scenario_name"],
        "timeline_model_version": timeline_result["model_version"],
        "trajectory": rows,
        "summary": family_safety.summarize(rows, flags),
        "limitations": [
            "accumulated_load and accumulated_strain are project engineering indices",
            "thresholds are synthetic calibration guardrails, not clinical cut-offs",
            "the model does not predict divorce or calculate relationship-breakdown probability",
            "high interaction current alone is not treated as conflict",
        ],
    }


def _thermal_from_family(scenario, family_result):
    rows = thermal.integrate_thermal(
        scenario,
        family_result["trajectory"],
    )
    return {
        "model_version": thermal.VERSION,
        "trajectory": rows,
        "summary": thermal.summarize_thermal(rows),
        "boundary": (
            "Thermal states are engineering analogies; they are not "
            "medical temperatures or relationship-outcome probabilities."
        ),
    }


def _summary(outputs):
    out = {}

    timeline = outputs.get("timeline")
    if timeline:
        out["timeline"] = {
            "days": timeline["integration"]["days"],
            "sample_count": len(timeline["samples"]),
            "person_count": len(timeline["summary"]["persons"]),
            "strongest_link": timeline["summary"]["strongest_link"],
            "peak_financial_stress": timeline["summary"][
                "peak_financial_stress"
            ],
        }

    family = outputs.get("family_safety")
    if family:
        out["family_safety"] = {
            "highest_load_person": family["summary"][
                "highest_load_person"
            ],
            "highest_strain_link": family["summary"][
                "highest_strain_link"
            ],
            "highest_dissipation_pair": family["summary"][
                "highest_dissipation_pair"
            ],
        }

    therm = outputs.get("thermal_recovery")
    if therm:
        persons = therm["summary"]["persons"]
        if persons:
            hottest = max(
                persons.items(),
                key=lambda kv: kv[1]["peak_heat"]["value"],
            )
            out["thermal_recovery"] = {
                "highest_peak_heat_person": hottest[0],
                "highest_peak_heat": hottest[1]["peak_heat"],
            }

    neigh = outputs.get("neighbor_network")
    if neigh:
        out["neighbor_network"] = {
            "central_person_id": neigh["central_person_id"],
            "intent_inferred": neigh["intent_inferred"],
            "pre_event_count": neigh["event_windows"]["pre"][
                "event_count"
            ],
            "post_event_count": neigh["event_windows"]["post"][
                "event_count"
            ],
        }

    perception_outputs = outputs.get("perception_identification")
    if perception_outputs:
        out["perception_identification"] = {
            key: {
                "target_person_id": item["target_person_id"],
                "brief_candidate_count": item[
                    "brief_identifiability"
                ]["candidate_count"],
                "full_candidate_count": item[
                    "full_identifiability"
                ]["candidate_count"],
                "real_world_belief_inference": item[
                    "real_world_belief_inference"
                ],
            }
            for key, item in perception_outputs.items()
        }

    return out


def run_engine(scenario, engine_spec):
    compiled = compile_engine(scenario, engine_spec)
    timeline = compiled["timeline"]

    outputs = {
        "person_ir": compiled["compiled_contract"]["person_ir"],
    }

    if timeline is not None:
        time_result = pts.simulate_person_timeline(
            scenario, timeline
        )
        outputs["timeline"] = time_result

        family = _family_from_timeline(
            scenario,
            time_result,
            compiled["relationship_flags"],
        )
        outputs["family_safety"] = family
        outputs["thermal_recovery"] = _thermal_from_family(
            scenario, family
        )

    if compiled["neighbor_spec"] is not None:
        outputs["neighbor_network"] = neighbor.analyze(
            scenario,
            compiled["neighbor_spec"],
        )

    if compiled["perception_specs"]:
        outputs["perception_identification"] = {
            item["id"]: perception.analyze(
                scenario, item["spec"]
            )
            for item in compiled["perception_specs"]
        }

    summary = _summary(outputs)
    reproducibility = {
        "input_digest": compiled["input_digest"],
        "compiled_contract_digest": compiled[
            "compiled_contract_digest"
        ],
        "engine_version": VERSION,
        "component_versions": compiled[
            "compiled_contract"
        ]["component_versions"],
    }

    return {
        "engine_version": VERSION,
        "scenario_name": scenario.get(
            "название", "RLC-family scenario"
        ),
        "capabilities": list(CAPABILITIES),
        "features_present": compiled[
            "compiled_contract"
        ]["features_present"],
        "reproducibility": reproducibility,
        "summary": summary,
        "outputs": outputs,
        "interpretation_boundary": (
            "UNIFIED-ENGINE1 composes project engineering models. "
            "Its states, thresholds, rankings and counterfactuals are "
            "simulation constructs, not medical, psychological, causal "
            "or intent findings about real people."
        ),
    }


def _load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise core.ScenarioError(f"{path}: root must be object")
    return data


def main():
    p = argparse.ArgumentParser(
        description="Run the unified RLC-family engine"
    )
    p.add_argument("scenario")
    p.add_argument("engine_spec")
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    scenario = _load(args.scenario)
    spec = _load(args.engine_spec)
    result = run_engine(scenario, spec)
    text = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")

    print(text, end="")


if __name__ == "__main__":
    main()
