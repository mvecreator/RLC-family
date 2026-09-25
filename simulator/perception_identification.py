#!/usr/bin/env python3
"""PERCEPTION-ID1: brief-observation RLC identifiability benchmark.

This layer asks what an observer could infer from a short visible response of
another PERSON2 node. It separates true model parameters from observer-estimated
parameters and keeps uncertainty explicit.

It does not infer the beliefs, motives, or intentions of real people.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

from simulator import person_model as pm
from simulator import rlc_family_sim as core


VERSION = "RLC-FAMILY-PERCEPTION-ID1-0.1"


def _positive(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise core.ScenarioError(f"{name} must be number") from e
    if value <= 0:
        raise core.ScenarioError(f"{name} must be > 0")
    return value


def _derivative(state, t, theta, pulse):
    v, i_l = state
    active = pulse["at_day"] <= t < pulse["at_day"] + pulse["duration_days"]
    u = pulse["amplitude"] if active else 0.0
    return (
        (u - v / theta["R"] - i_l) / theta["C"],
        v / theta["L"],
    )


def simulate_response(theta, pulse, horizon_days, dt_days, repeat_times=None):
    repeat_times = list(repeat_times or [pulse["at_day"]])

    def forcing(t):
        return pulse["amplitude"] if any(
            start <= t < start + pulse["duration_days"]
            for start in repeat_times
        ) else 0.0

    def deriv(state, t):
        v, i_l = state
        return (
            (forcing(t) - v / theta["R"] - i_l) / theta["C"],
            v / theta["L"],
        )

    steps = int(math.ceil(horizon_days / dt_days))
    t = 0.0
    state = (0.0, 0.0)
    rows = []
    for _ in range(steps + 1):
        rows.append({
            "day": t,
            "voltage": state[0],
            "inductor_current": state[1],
        })
        if t >= horizon_days - 1e-15:
            break
        h = min(dt_days, horizon_days - t)

        k1 = deriv(state, t)
        s2 = (
            state[0] + 0.5 * h * k1[0],
            state[1] + 0.5 * h * k1[1],
        )
        k2 = deriv(s2, t + 0.5 * h)
        s3 = (
            state[0] + 0.5 * h * k2[0],
            state[1] + 0.5 * h * k2[1],
        )
        k3 = deriv(s3, t + 0.5 * h)
        s4 = (
            state[0] + h * k3[0],
            state[1] + h * k3[1],
        )
        k4 = deriv(s4, t + h)
        state = (
            state[0] + h * (
                k1[0] + 2*k2[0] + 2*k3[0] + k4[0]
            ) / 6.0,
            state[1] + h * (
                k1[1] + 2*k2[1] + 2*k3[1] + k4[1]
            ) / 6.0,
        )
        t += h
    return rows


def _rmse(reference, candidate, window_days):
    pairs = [
        (a, b)
        for a, b in zip(reference, candidate)
        if a["day"] <= window_days + 1e-12
    ]
    if not pairs:
        raise core.ScenarioError("observation window has no samples")
    return math.sqrt(
        sum((a["voltage"] - b["voltage"]) ** 2 for a, b in pairs)
        / len(pairs)
    )


def _peak_abs(rows, window_days):
    values = [
        abs(row["voltage"])
        for row in rows
        if row["day"] <= window_days + 1e-12
    ]
    return max(values) if values else 0.0


def _span(values):
    lo = min(values)
    hi = max(values)
    return {
        "min": lo,
        "max": hi,
        "ratio": hi / lo if lo > 0 else math.inf,
    }


def _nearest_to_prior(candidates, prior):
    def score(item):
        return sum(
            math.log(item[key] / prior[key]) ** 2
            for key in ("R", "C", "L")
        )
    return min(candidates, key=score)


def _derived(theta):
    alpha = 1.0 / (2.0 * theta["R"] * theta["C"])
    omega0 = 1.0 / math.sqrt(theta["L"] * theta["C"])
    tau_decay = 1.0 / alpha
    zeta = alpha / omega0
    return {
        "alpha": alpha,
        "omega0": omega0,
        "tau_decay": tau_decay,
        "zeta": zeta,
    }


def _residual_fraction(theta, pulse, interval, dt_days):
    horizon = max(interval, pulse["duration_days"] + dt_days)
    rows = simulate_response(theta, pulse, horizon, dt_days)
    peak = max(abs(row["voltage"]) for row in rows)
    final = min(rows, key=lambda row: abs(row["day"] - interval))
    return abs(final["voltage"]) / peak if peak > 0 else 0.0


def compile_spec(scenario, spec):
    if not isinstance(spec, dict):
        raise core.ScenarioError("perception_id1 spec must be object")

    ir = pm.compile_person_network(scenario)
    by_id = {node["id"]: node for node in ir["nodes"]}
    target_id = str(spec.get("target_person_id", "")).strip()
    if target_id not in by_id:
        raise core.ScenarioError(
            f"unknown target_person_id: {target_id}"
        )
    target = by_id[target_id]
    actual = {
        "R": float(target["R"]),
        "C": float(target["C"]),
        "L": float(target["L"]),
    }

    brief = _positive(
        spec.get("brief_observation_days", 0.10),
        "brief_observation_days",
    )
    full = _positive(
        spec.get("full_observation_days", 2.0),
        "full_observation_days",
    )
    if full <= brief:
        raise core.ScenarioError(
            "full_observation_days must exceed brief_observation_days"
        )
    dt = _positive(spec.get("dt_days", 0.002), "dt_days")
    if dt > brief / 5.0:
        raise core.ScenarioError(
            "dt_days too coarse for brief observation"
        )

    pulse_raw = spec.get("probe", {})
    if not isinstance(pulse_raw, dict):
        raise core.ScenarioError("probe must be object")
    pulse = {
        "at_day": 0.0,
        "duration_days": _positive(
            pulse_raw.get("duration_days", 0.08),
            "probe.duration_days",
        ),
        "amplitude": _positive(
            pulse_raw.get("amplitude", 0.45),
            "probe.amplitude",
        ),
    }

    factors = spec.get(
        "grid_factors",
        [0.50, 0.70, 0.85, 1.0, 1.20, 1.50, 2.0],
    )
    if not isinstance(factors, list) or 1.0 not in factors:
        raise core.ScenarioError(
            "grid_factors must be list containing 1.0"
        )
    factors = [_positive(x, "grid_factor") for x in factors]

    prior_raw = spec.get("observer_prior", {})
    if not isinstance(prior_raw, dict):
        raise core.ScenarioError("observer_prior must be object")
    prior = {
        "R": _positive(
            prior_raw.get("R", pm.DEFAULTS["adult_base_r"]),
            "observer_prior.R",
        ),
        "C": _positive(
            prior_raw.get("C", pm.DEFAULTS["adult_base_c"]),
            "observer_prior.C",
        ),
        "L": _positive(
            prior_raw.get("L", pm.DEFAULTS["adult_base_l"]),
            "observer_prior.L",
        ),
    }

    return {
        "model_version": VERSION,
        "target_person_id": target_id,
        "actual_theta": actual,
        "brief_observation_days": brief,
        "full_observation_days": full,
        "dt_days": dt,
        "probe": pulse,
        "grid_factors": factors,
        "observer_prior": prior,
        "noise_floor_fraction_of_peak": float(
            spec.get("noise_floor_fraction_of_peak", 0.01)
        ),
        "repeat_interval_days": _positive(
            spec.get("repeat_interval_days", 1.0),
            "repeat_interval_days",
        ),
        "repeat_count": int(spec.get("repeat_count", 4)),
        "strategy_residual_threshold": float(
            spec.get("strategy_residual_threshold", 0.20)
        ),
    }


def analyze(scenario, spec):
    cfg = compile_spec(scenario, spec)
    actual = cfg["actual_theta"]
    reference = simulate_response(
        actual,
        cfg["probe"],
        cfg["full_observation_days"],
        cfg["dt_days"],
    )

    candidates = []
    for fr, fc, fl in itertools.product(
        cfg["grid_factors"], repeat=3
    ):
        theta = {
            "R": actual["R"] * fr,
            "C": actual["C"] * fc,
            "L": actual["L"] * fl,
        }
        rows = simulate_response(
            theta,
            cfg["probe"],
            cfg["full_observation_days"],
            cfg["dt_days"],
        )
        candidates.append({
            **theta,
            "brief_rmse": _rmse(
                reference, rows, cfg["brief_observation_days"]
            ),
            "full_rmse": _rmse(
                reference, rows, cfg["full_observation_days"]
            ),
        })

    brief_peak = _peak_abs(
        reference, cfg["brief_observation_days"]
    )
    tolerance = (
        cfg["noise_floor_fraction_of_peak"] * brief_peak
    )
    brief_set = [
        row for row in candidates
        if row["brief_rmse"] <= tolerance + 1e-15
    ]
    if not brief_set:
        raise core.ScenarioError(
            "no brief-observation candidate within noise floor"
        )

    full_peak = _peak_abs(reference, cfg["full_observation_days"])
    full_tolerance = (
        cfg["noise_floor_fraction_of_peak"] * full_peak
    )
    full_set = [
        row for row in candidates
        if row["full_rmse"] <= full_tolerance + 1e-15
    ]

    perceived = _nearest_to_prior(
        brief_set,
        cfg["observer_prior"],
    )
    perceived_theta = {
        key: perceived[key] for key in ("R", "C", "L")
    }

    repeat_interval = cfg["repeat_interval_days"]
    perceived_residual = _residual_fraction(
        perceived_theta,
        cfg["probe"],
        repeat_interval,
        cfg["dt_days"],
    )
    actual_residual = _residual_fraction(
        actual,
        cfg["probe"],
        repeat_interval,
        cfg["dt_days"],
    )
    threshold = cfg["strategy_residual_threshold"]
    perceived_policy = (
        "repeat_short_input_assuming_decay"
        if perceived_residual < threshold
        else "avoid_or_space_repeated_input"
    )
    actual_policy_if_known = (
        "repeat_short_input_assuming_decay"
        if actual_residual < threshold
        else "avoid_or_space_repeated_input"
    )

    repeat_times = [
        k * repeat_interval for k in range(cfg["repeat_count"])
    ]
    horizon = repeat_times[-1] + repeat_interval + cfg["probe"][
        "duration_days"
    ]
    predicted_repeat = simulate_response(
        perceived_theta,
        cfg["probe"],
        horizon,
        cfg["dt_days"],
        repeat_times=repeat_times,
    )
    actual_repeat = simulate_response(
        actual,
        cfg["probe"],
        horizon,
        cfg["dt_days"],
        repeat_times=repeat_times,
    )

    nominal = {
        "R": pm.DEFAULTS["adult_base_r"],
        "C": pm.DEFAULTS["adult_base_c"],
        "L": pm.DEFAULTS["adult_base_l"],
    }

    return {
        "model_version": VERSION,
        "synthetic_ground_truth_known": True,
        "real_world_belief_inference": False,
        "target_person_id": cfg["target_person_id"],
        "actual_theta": actual,
        "actual_vs_nominal": {
            key: actual[key] / nominal[key]
            for key in ("R", "C", "L")
        },
        "brief_identifiability": {
            "window_days": cfg["brief_observation_days"],
            "noise_floor": tolerance,
            "candidate_count": len(brief_set),
            "R_span": _span([x["R"] for x in brief_set]),
            "C_span": _span([x["C"] for x in brief_set]),
            "L_span": _span([x["L"] for x in brief_set]),
        },
        "full_identifiability": {
            "window_days": cfg["full_observation_days"],
            "noise_floor": full_tolerance,
            "candidate_count": len(full_set),
            "R_span": _span([x["R"] for x in full_set]),
            "C_span": _span([x["C"] for x in full_set]),
            "L_span": _span([x["L"] for x in full_set]),
        },
        "observer_prior": cfg["observer_prior"],
        "perceived_theta_from_brief_window": perceived_theta,
        "perception_error_ratio": {
            key: perceived_theta[key] / actual[key]
            for key in ("R", "C", "L")
        },
        "derived_actual": _derived(actual),
        "derived_perceived": _derived(perceived_theta),
        "strategy_probe": {
            "repeat_interval_days": repeat_interval,
            "residual_threshold": threshold,
            "perceived_residual_fraction": perceived_residual,
            "actual_residual_fraction": actual_residual,
            "policy_from_perceived_model": perceived_policy,
            "policy_if_actual_model_were_known": actual_policy_if_known,
            "policy_mismatch": (
                perceived_policy != actual_policy_if_known
            ),
        },
        "repeated_input_prediction_error": {
            "repeat_count": cfg["repeat_count"],
            "predicted_peak_abs_voltage": max(
                abs(row["voltage"]) for row in predicted_repeat
            ),
            "actual_peak_abs_voltage": max(
                abs(row["voltage"]) for row in actual_repeat
            ),
        },
        "interpretation_boundary": (
            "This benchmark demonstrates parameter-identification ambiguity "
            "for a synthetic RLC target. It does not show what any real "
            "observer believed, noticed, intended, or consciously selected."
        ),
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="Run PERCEPTION-ID1")
    p.add_argument("scenario")
    p.add_argument("spec")
    args = p.parse_args()
    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    print(json.dumps(analyze(scenario, spec), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
