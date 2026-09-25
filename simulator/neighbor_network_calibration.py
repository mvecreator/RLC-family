#!/usr/bin/env python3
"""NEIGHBOR-NET-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
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
        "NN05_DESYNC_DOES_NOT_INCREASE_PRE_PEAK_LOAD": (
            desync_pre_response["peak_accumulated_load"]["value"]
            <= actual_pre_peak + 1e-12
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
            "central_pre_disconnected": disconnected_result[
                "central_response"
            ]["pre_actual"],
            "central_pre_no_stimulus": no_stimulus[
                "central_response"
            ]["pre_actual"],
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
