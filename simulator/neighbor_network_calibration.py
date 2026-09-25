#!/usr/bin/env python3
"""NEIGHBOR-NET-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from simulator import neighbor_network as nn
from simulator import person_family_safety as family_safety


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def suite():
    scenario = load_json(
        ROOT / "examples" / "neighbor_net1_synthetic_scenario.json"
    )
    spec = load_json(
        ROOT / "examples" / "neighbor_net1_synthetic_spec.json"
    )

    compiled = nn.compile_spec(scenario, spec)
    result = nn.analyze(scenario, spec)


    household_scenario = load_json(
        ROOT / "examples" / "neighbor_net1_households_scenario.json"
    )
    household_spec = load_json(
        ROOT / "examples" / "neighbor_net1_households_spec.json"
    )
    household_compiled = nn.compile_spec(
        household_scenario,
        household_spec,
    )
    household_result = nn.analyze(
        household_scenario,
        household_spec,
    )

    family_event = next(
        event for event in household_compiled["observed_stimuli"]
        if event["source_group_id"] == "household2_family3"
    )
    family_timeline = nn.timeline_from_spec(
        household_compiled,
        include_relief=False,
        stimuli=[family_event],
    )
    family_expanded = [
        event for event in family_timeline["events"]
        if event["id"].startswith(family_event["id"])
    ]

    t0 = compiled["intervention"]["at_day"]
    window = compiled["window_days"]
    pre = nn._window_events(compiled, t0 - window, t0)
    post = nn._window_events(compiled, t0, t0 + window)

    pre_metrics = nn.event_metrics(
        pre,
        compiled["neighbor_ids"],
        window,
        compiled["sync_tolerance_days"],
    )
    post_metrics = nn.event_metrics(
        post,
        compiled["neighbor_ids"],
        window,
        compiled["sync_tolerance_days"],
    )

    continuation = nn.continuation_stimuli(compiled)
    cf_post = [
        event for event in continuation
        if t0 <= event["at_day"] < t0 + window
    ]

    desync = nn.desynchronized_pre_stimuli(compiled)
    desync_pre = [
        event for event in desync
        if t0 - window <= event["at_day"] < t0
    ]
    desync_metrics = nn.event_metrics(
        desync_pre,
        compiled["neighbor_ids"],
        window,
        compiled["sync_tolerance_days"],
    )

    disconnected = copy.deepcopy(scenario)
    disconnected["связи_персонажей"] = [
        link
        for link in disconnected["связи_персонажей"]
        if link.get("channel_kind") != "environmental_observation"
    ]
    disconnected_result = nn.analyze(disconnected, spec)

    no_stimulus_spec = copy.deepcopy(spec)
    no_stimulus_spec["observed_stimuli"] = []
    no_stimulus = nn.analyze(scenario, no_stimulus_spec)

    actual_pre_peak = result["central_response"][
        "pre_actual"
    ]["peak_accumulated_load"]["value"]
    disconnected_pre_peak = disconnected_result[
        "central_response"
    ]["pre_actual"]["peak_accumulated_load"]["value"]
    baseline_pre_peak = no_stimulus[
        "central_response"
    ]["pre_actual"]["peak_accumulated_load"]["value"]

    actual_post = result["central_response"]["post_actual"]
    no_relief_post = result["central_response"][
        "post_no_relief_counterfactual"
    ]
    continuation_post = result["central_response"][
        "post_prepattern_continuation_counterfactual"
    ]
    desync_pre_response = result["central_response"][
        "pre_desynchronized_counterfactual"
    ]

    original_post_ids = [event["id"] for event in post]
    compiled_post_ids = [
        event["id"]
        for event in compiled["observed_stimuli"]
        if t0 <= event["at_day"] < t0 + window
    ]

    checks = {
        "NN01_PRE_EVENTS_REACH_CENTRAL_THROUGH_OBSERVATION_LINKS": (
            actual_pre_peak > disconnected_pre_peak
            and actual_pre_peak > baseline_pre_peak
        ),
        "NN02_REPEATED_EVENTS_ACCUMULATE_CENTRAL_LOAD": (
            result["central_response"]["pre_actual"][
                "final_accumulated_load"
            ] > no_stimulus["central_response"]["pre_actual"][
                "final_accumulated_load"
            ]
        ),
        "NN03_PRE_TIMING_IS_MORE_ALIGNED_THAN_POST": (
            pre_metrics["temporal_alignment_index"]
            > post_metrics["temporal_alignment_index"]
        ),
        "NN04_DESYNC_PRESERVES_EVENT_COUNT_AND_EXPOSURE": (
            desync_metrics["event_count"] == pre_metrics["event_count"]
            and abs(
                desync_metrics["exposure_area"]
                - pre_metrics["exposure_area"]
            ) < 1e-12
        ),
        "NN05_TIMING_COUNTERFACTUAL_IS_COMPUTED_WITHOUT_DIRECTION_ASSUMPTION": (
            desync_pre_response["peak_accumulated_load"]["value"] >= 0.0
            and actual_pre_peak >= 0.0
        ),
        "NN06_POST_EVENT_RATE_AND_EXPOSURE_DROP": (
            post_metrics["events_per_day"] < pre_metrics["events_per_day"]
            and post_metrics["exposure_area"] < pre_metrics["exposure_area"]
        ),
        "NN07_RELIEF_REDUCES_OR_PRESERVES_POST_FINAL_LOAD": (
            actual_post["final_accumulated_load"]
            <= no_relief_post["final_accumulated_load"] + 1e-12
        ),
        "NN08_CONTINUED_PRE_PATTERN_IS_HEAVIER_THAN_OBSERVED_POST": (
            continuation_post["final_accumulated_load"]
            >= actual_post["final_accumulated_load"] - 1e-12
        ),
        "NN09_INTERVENTION_MARKER_DOES_NOT_REWRITE_OBSERVED_POST_EVENTS": (
            original_post_ids == compiled_post_ids
        ),
        "NN10_CONTINUATION_REUSES_PRE_PATTERN_ONLY_AS_COUNTERFACTUAL": (
            len(cf_post) == len(pre)
            and all(
                event["id"].startswith("cf-continuation-")
                for event in cf_post
            )
        ),
        "NN11_TEMPORAL_ALIGNMENT_DOES_NOT_INFER_INTENT": (
            pre_metrics["intent_inferred"] is False
            and result["intent_inferred"] is False
        ),
        "NN12_ANALYSIS_KEEPS_CAUSAL_BOUNDARY_EXPLICIT": (
            "do not establish intent" in result["causal_boundary"]
            and "caused neighbors to change behavior"
            in result["causal_boundary"]
        ),
        "NN13_HOUSEHOLD_COMPOSITION_COMPILES": (
            {
                h["group_id"]: len(h["members"])
                for h in household_compiled["neighbor_households"]
            }
            == {
                "household1_solo": 1,
                "household2_family3": 3,
                "household3_couple": 2,
            }
        ),
        "NN14_GROUP_INPUT_IS_CONSERVED_WHEN_DISTRIBUTED": (
            len(family_expanded) == 3
            and abs(
                sum(event["drive_add"] for event in family_expanded)
                - family_event["amplitude"]
            ) < 1e-12
            and abs(sum(family_event["member_weights"].values()) - 1.0)
            < 1e-12
        ),
        "NN15_HOUSEHOLD_PROBE_USES_EQUAL_TOTAL_INPUT": (
            household_result["household_transfer_probe"]["probe"][
                "equal_total_input_across_households"
            ] is True
            and len({
                round(item["total_input_amplitude"], 12)
                for item in household_result["household_transfer_probe"][
                    "households"
                ].values()
            }) == 1
            and len({
                round(item["total_input_exposure_area"], 12)
                for item in household_result["household_transfer_probe"][
                    "households"
                ].values()
            }) == 1
        ),
        "NN16_HOUSEHOLD_TOPOLOGY_RESPONSES_ARE_ALL_COMPUTED": (
            set(
                household_result["household_transfer_probe"][
                    "central_peak_load_delta_ranking"
                ]
            )
            == {
                "household1_solo",
                "household2_family3",
                "household3_couple",
            }
            and all(
                item["central_response_delta"][
                    "peak_abs_load_delta"
                ]["abs_value"] >= 0.0
                for item in household_result[
                    "household_transfer_probe"
                ]["households"].values()
            )
        ),
        "NN17_SOLO_IS_INVARIANT_TO_REMOVING_HOUSEHOLD_INTERNAL_LINKS": (
            abs(
                household_result["household_topology_effect"][
                    "household1_solo"
                ]["difference"]
            ) < 1e-12
        ),
        "NN18_FAMILY_AND_COUPLE_INTERNAL_TOPOLOGY_COUNTERFACTUALS_EXIST": (
            set(household_result["household_topology_effect"])
            == {
                "household1_solo",
                "household2_family3",
                "household3_couple",
            }
            and all(
                math.isfinite(
                    household_result["household_topology_effect"][gid][
                        "difference"
                    ]
                )
                for gid in (
                    "household2_family3",
                    "household3_couple",
                )
            )
        ),
        "NN19_CROSS_HOUSEHOLD_SOCIAL_LINKS_ARE_EXPLICIT": (
            sum(
                1
                for link in household_scenario["связи_персонажей"]
                if link.get("channel_kind") == "cross_household_social"
            ) == 3
        ),
        "NN20_CROSS_HOUSEHOLD_TOPOLOGY_EFFECT_IS_MEASURED_WITHOUT_SIGN_ASSUMPTION": (
            math.isfinite(
                household_result["cross_household_social_effect"][
                    "difference"
                ]
            )
            and household_result["cross_household_social_effect"][
                "direction_precommitted"
            ] is False
        ),
    }

    return {
        "benchmark": "NEIGHBOR-NET-CAL1",
        "model_version": nn.VERSION,
        "reference": {
            "pre_event_metrics": pre_metrics,
            "post_event_metrics": post_metrics,
            "desynchronized_pre_metrics": desync_metrics,
            "central_pre_actual": result["central_response"]["pre_actual"],
            "central_post_actual": actual_post,
            "central_post_no_relief": no_relief_post,
            "central_post_continuation": continuation_post,
            "central_pre_desynchronized": desync_pre_response,
            "timing_peak_load_delta_actual_minus_desync": (
                actual_pre_peak
                - desync_pre_response["peak_accumulated_load"]["value"]
            ),
            "central_pre_disconnected": disconnected_result[
                "central_response"
            ]["pre_actual"],
            "central_pre_no_stimulus": no_stimulus[
                "central_response"
            ]["pre_actual"],
            "household_composition": household_compiled[
                "neighbor_households"
            ],
            "household_transfer_probe": household_result[
                "household_transfer_probe"
            ],
            "household_topology_effect": household_result[
                "household_topology_effect"
            ],
            "cross_household_social_effect": household_result[
                "cross_household_social_effect"
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
