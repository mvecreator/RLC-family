#!/usr/bin/env python3
"""OUTCOME-BLIND1: prefix-only directional prediction and hidden-suffix evaluation.

This evaluator is deliberately capable of reporting model failure.
Prediction functions receive only prefix rows. Future rows are passed only to
the evaluator after the prediction object has been produced.
"""

from __future__ import annotations

import math

VERSION = "RLC-FAMILY-OUTCOME-BLIND1-0.1"
DIRECTION_EPS = 0.03

PERSON_A = 0.45
PERSON_R = 0.14
LINK_A = 0.50
LINK_R = 0.10

PERSON_ATTENTION_THRESHOLD = 0.35
LINK_REPAIR_THRESHOLD = 0.50


def direction(delta, eps=DIRECTION_EPS):
    delta = float(delta)
    if delta > eps:
        return "ACCUMULATING"
    if delta < -eps:
        return "RECOVERING"
    return "STABLE"


def split_rows(rows, cutoff_day, horizon_days):
    if not rows:
        raise ValueError("rows must not be empty")
    cutoff_day = float(cutoff_day)
    horizon_days = float(horizon_days)
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0")

    prefix = [row for row in rows if float(row["day"]) <= cutoff_day + 1e-12]
    suffix = [
        row for row in rows
        if cutoff_day < float(row["day"]) <= cutoff_day + horizon_days + 1e-12
    ]
    if not prefix:
        raise ValueError("cutoff leaves empty prefix")
    if not suffix:
        raise ValueError("horizon leaves empty hidden suffix")
    return prefix, suffix


def project_accumulator(state, load, horizon_days, accumulation, recovery):
    state = max(0.0, min(1.0, float(state)))
    load = max(0.0, min(1.0, float(load)))
    horizon_days = max(0.0, float(horizon_days))
    rate = accumulation * load + recovery
    if rate <= 0:
        return state
    equilibrium = accumulation * load / rate
    return equilibrium + (state - equilibrium) * math.exp(-rate * horizon_days)


def _recent_mean(prefix, group, key, lookback_days):
    end = float(prefix[-1]["day"])
    start = end - float(lookback_days)
    values = [
        float(row[group][key]["combined"])
        for row in prefix
        if float(row["day"]) >= start - 1e-12
    ]
    if not values:
        values = [float(prefix[-1][group][key]["combined"])]
    return sum(values) / len(values)


def _time_to_threshold(
    state,
    load,
    threshold,
    accumulation,
    recovery,
    max_days,
    step=0.05,
):
    state = float(state)
    if state >= threshold:
        return 0.0
    t = step
    while t <= max_days + 1e-12:
        projected = project_accumulator(
            state, load, t, accumulation, recovery
        )
        if projected >= threshold:
            return t
        t += step
    return None


def predict_prefix(prefix, horizon_days, lookback_days=3.0):
    """Model projection using only prefix state and recent prefix load."""
    last = prefix[-1]
    persons = {}
    for pid, item in last["persons"].items():
        state = float(item["accumulated_load"])
        load = _recent_mean(prefix, "persons", pid, lookback_days)
        projected = project_accumulator(
            state, load, horizon_days, PERSON_A, PERSON_R
        )
        persons[pid] = {
            "state_at_cutoff": state,
            "recent_mean_load": load,
            "projected_state": projected,
            "projected_delta": projected - state,
            "direction": direction(projected - state),
            "time_to_attention_days": _time_to_threshold(
                state,
                load,
                PERSON_ATTENTION_THRESHOLD,
                PERSON_A,
                PERSON_R,
                horizon_days,
            ),
        }

    links = {}
    for key, item in last["links"].items():
        state = float(item["accumulated_strain"])
        load = _recent_mean(prefix, "links", key, lookback_days)
        projected = project_accumulator(
            state, load, horizon_days, LINK_A, LINK_R
        )
        links[key] = {
            "state_at_cutoff": state,
            "recent_mean_load": load,
            "projected_state": projected,
            "projected_delta": projected - state,
            "direction": direction(projected - state),
            "time_to_repair_threshold_days": _time_to_threshold(
                state,
                load,
                LINK_REPAIR_THRESHOLD,
                LINK_A,
                LINK_R,
                horizon_days,
            ),
        }

    person_crossers = [
        (v["time_to_attention_days"], k)
        for k, v in persons.items()
        if v["time_to_attention_days"] is not None
    ]
    link_crossers = [
        (v["time_to_repair_threshold_days"], k)
        for k, v in links.items()
        if v["time_to_repair_threshold_days"] is not None
    ]

    return {
        "model_version": VERSION,
        "cutoff_day": float(last["day"]),
        "horizon_days": float(horizon_days),
        "lookback_days": float(lookback_days),
        "persons": persons,
        "links": links,
        "predicted_first_person_attention": (
            min(person_crossers)[1] if person_crossers else None
        ),
        "predicted_first_link_repair": (
            min(link_crossers)[1] if link_crossers else None
        ),
        "future_rows_seen": 0,
    }


def persistence_baseline(prefix, horizon_days):
    last = prefix[-1]
    return {
        "persons": {
            pid: {"direction": "STABLE"}
            for pid in last["persons"]
        },
        "links": {
            key: {"direction": "STABLE"}
            for key in last["links"]
        },
        "future_rows_seen": 0,
    }


def _target_row(suffix):
    return suffix[-1]


def _actual_first_crossing(prefix, suffix, group, field, threshold):
    current = prefix[-1]
    already = {
        key for key, item in current[group].items()
        if float(item[field]) >= threshold
    }
    for row in suffix:
        for key, item in row[group].items():
            if key in already:
                continue
            if float(item[field]) >= threshold:
                return key, float(row["day"])
    return None, None


def actual_outcomes(prefix, suffix):
    start = prefix[-1]
    end = _target_row(suffix)

    persons = {}
    for pid, item in start["persons"].items():
        s0 = float(item["accumulated_load"])
        s1 = float(end["persons"][pid]["accumulated_load"])
        persons[pid] = {
            "state_at_cutoff": s0,
            "state_at_horizon": s1,
            "delta": s1 - s0,
            "direction": direction(s1 - s0),
        }

    links = {}
    for key, item in start["links"].items():
        s0 = float(item["accumulated_strain"])
        s1 = float(end["links"][key]["accumulated_strain"])
        links[key] = {
            "state_at_cutoff": s0,
            "state_at_horizon": s1,
            "delta": s1 - s0,
            "direction": direction(s1 - s0),
        }

    first_person, first_person_day = _actual_first_crossing(
        prefix, suffix, "persons", "accumulated_load",
        PERSON_ATTENTION_THRESHOLD,
    )
    first_link, first_link_day = _actual_first_crossing(
        prefix, suffix, "links", "accumulated_strain",
        LINK_REPAIR_THRESHOLD,
    )

    return {
        "horizon_day": float(end["day"]),
        "persons": persons,
        "links": links,
        "actual_first_person_attention": first_person,
        "actual_first_person_attention_day": first_person_day,
        "actual_first_link_repair": first_link,
        "actual_first_link_repair_day": first_link_day,
    }


def _accuracy(pred_map, actual_map):
    keys = sorted(set(pred_map) & set(actual_map))
    if not keys:
        return None
    correct = sum(
        pred_map[key]["direction"] == actual_map[key]["direction"]
        for key in keys
    )
    return {
        "correct": correct,
        "total": len(keys),
        "accuracy": correct / len(keys),
    }


def evaluate_prediction(prediction, prefix, suffix):
    actual = actual_outcomes(prefix, suffix)
    person_score = _accuracy(prediction["persons"], actual["persons"])
    link_score = _accuracy(prediction["links"], actual["links"])

    return {
        "prediction": prediction,
        "actual": actual,
        "person_direction_score": person_score,
        "link_direction_score": link_score,
        "first_person_attention_correct": (
            prediction.get("predicted_first_person_attention")
            == actual["actual_first_person_attention"]
        ),
        "first_link_repair_correct": (
            prediction.get("predicted_first_link_repair")
            == actual["actual_first_link_repair"]
        ),
    }


def run_blind(rows, cutoff_day, horizon_days, lookback_days=3.0):
    prefix, suffix = split_rows(rows, cutoff_day, horizon_days)

    # Prediction is created before suffix is supplied to evaluation.
    model_prediction = predict_prefix(
        prefix, horizon_days, lookback_days=lookback_days
    )
    baseline_prediction = persistence_baseline(prefix, horizon_days)

    model_eval = evaluate_prediction(
        model_prediction, prefix, suffix
    )
    baseline_eval = evaluate_prediction(
        baseline_prediction, prefix, suffix
    )

    return {
        "model_version": VERSION,
        "cutoff_day": float(prefix[-1]["day"]),
        "horizon_days": float(horizon_days),
        "prefix_rows": len(prefix),
        "hidden_suffix_rows": len(suffix),
        "model": model_eval,
        "persistence_baseline": baseline_eval,
        "blindness_contract": {
            "prediction_api_receives_prefix_only": True,
            "prediction_future_rows_seen": model_prediction["future_rows_seen"],
            "baseline_future_rows_seen": baseline_prediction["future_rows_seen"],
        },
    }
