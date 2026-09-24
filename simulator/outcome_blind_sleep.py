#!/usr/bin/env python3
"""Blind directional check for the qualitative SOLO sleep trajectory."""

from __future__ import annotations

from simulator import sleep_trajectory_model as sleep


def classify(delta, eps=0.10):
    if delta > eps:
        return "INCREASING"
    if delta < -eps:
        return "DECREASING"
    return "STABLE"


def recent_linear_prediction(rows, field, horizon_progress, lookback=5):
    prefix = rows[-max(2, int(lookback)):]
    x0 = float(prefix[0]["progress"])
    x1 = float(prefix[-1]["progress"])
    y0 = float(prefix[0][field])
    y1 = float(prefix[-1][field])
    slope = 0.0 if x1 == x0 else (y1 - y0) / (x1 - x0)
    delta = slope * float(horizon_progress)
    return {
        "recent_slope": slope,
        "projected_delta": delta,
        "direction": classify(delta),
    }


def personal_history_feature_status(observations):
    hist = observations.get("historical_caffeine", {})
    dose_known = hist.get("dose_mg_per_cup_observed") is not None
    timing_known = hist.get("timing_relative_to_sleep_observed") is not None
    return {
        "caffeine_dose_identified": dose_known,
        "caffeine_timing_identified": timing_known,
        "caffeine_feature_usable_without_assumption": (
            dose_known and timing_known
        ),
    }


def run(observations, cutoff_progress=0.65, horizon_progress=0.35):
    full = sleep.trajectory(101)
    prefix = [
        row for row in full
        if row["progress"] <= cutoff_progress + 1e-12
    ]
    future = [
        row for row in full
        if cutoff_progress < row["progress"]
        <= cutoff_progress + horizon_progress + 1e-12
    ]
    if not prefix or not future:
        raise ValueError("invalid cutoff/horizon")

    prediction = recent_linear_prediction(
        prefix,
        "secondary_bout_weight",
        horizon_progress,
    )
    start = prefix[-1]["secondary_bout_weight"]
    end = future[-1]["secondary_bout_weight"]
    actual_delta = end - start
    actual_direction = classify(actual_delta)

    return {
        "cutoff_progress": cutoff_progress,
        "horizon_progress": horizon_progress,
        "prefix_stage": prefix[-1]["stage"],
        "prediction": prediction,
        "actual": {
            "start_secondary_bout_weight": start,
            "end_secondary_bout_weight": end,
            "delta": actual_delta,
            "direction": actual_direction,
            "final_stage": future[-1]["stage"],
        },
        "direction_correct": prediction["direction"] == actual_direction,
        "caffeine_feature_status": personal_history_feature_status(
            observations
        ),
        "interpretation": (
            "A miss here is informative: the mature biphasic prefix alone does "
            "not identify the later resolution. Personal caffeine dose/timing "
            "must not be invented to rescue the prediction."
        ),
    }


def main():
    import argparse
    import json
    from simulator import person_solo_calibration as solo

    p = argparse.ArgumentParser(
        description="Run blind SOLO sleep-resolution check"
    )
    p.add_argument(
        "observations",
        nargs="?",
        default="examples/person_solo_wake_observations.json",
    )
    p.add_argument("--cutoff-progress", type=float, default=0.65)
    p.add_argument("--horizon-progress", type=float, default=0.35)
    args = p.parse_args()

    result = run(
        solo.load_json(args.observations),
        cutoff_progress=args.cutoff_progress,
        horizon_progress=args.horizon_progress,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
