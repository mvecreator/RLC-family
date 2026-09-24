#!/usr/bin/env python3
"""PERSON-SOLO1: calibrate a single PERSON2 RLC node from wake-phase drift.

This layer intentionally separates:
1) observed wake-phase drift, which identifies an effective period;
2) PERSON2 R/L/C, which defines the node's normalized dynamics;
3) a fitted time-scale mapping between normalized RLC time and hours;
4) coffee/project events, which remain external forcing in PERSON-TIME2.

It is an internal satirical/system-model calibration, not a medical sleep model.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    from simulator import person_model as pm
    from simulator import person_time_solver as pts
    from simulator import rlc_family_sim as core
    from simulator import time_solver as legacy_time
except ModuleNotFoundError:
    import person_model as pm
    import person_time_solver as pts
    import rlc_family_sim as core
    import time_solver as legacy_time

VERSION = "RLC-FAMILY-PERSON-SOLO1-0.1"


def load_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise core.ScenarioError(str(e)) from e
    if not isinstance(value, dict):
        raise core.ScenarioError(f"{path}: root must be object")
    return value


def linear_fit(points):
    if len(points) < 2:
        raise core.ScenarioError("at least two wake observations are required")
    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    var = sum((x - xbar) ** 2 for x in xs)
    if var <= 0:
        raise core.ScenarioError("wake observation days must not all be identical")
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / var
    intercept = ybar - slope * xbar
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    rmse = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    return slope, intercept, rmse


def estimate_wake_period(observations):
    raw = observations.get("wake_observations")
    if not isinstance(raw, list) or len(raw) < 2:
        raise core.ScenarioError("wake_observations must contain at least two points")
    points = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise core.ScenarioError(f"wake observation {idx}: expected object")
        points.append((
            float(item.get("day", idx)),
            float(item["wake_offset_hours"]),
        ))
    calendar = core.positive(
        observations.get("calendar_day_interval_hours", 24.0),
        "calendar_day_interval_hours",
    )
    slope, intercept, rmse = linear_fit(points)
    period = calendar + slope
    if period <= 0:
        raise core.ScenarioError("inferred effective period must be positive")
    return {
        "wake_offset_slope_hours_per_calendar_day": slope,
        "wake_offset_intercept_hours": intercept,
        "fit_rmse_hours": rmse,
        "calendar_day_interval_hours": calendar,
        "effective_period_hours": period,
        "observation_count": len(points),
    }


def require_single_person(scenario):
    pir = pm.compile_person_network(scenario)
    if pir["mode"] != "PERSON2":
        raise core.ScenarioError("PERSON-SOLO1 requires PERSON2 персонажи")
    if len(pir["nodes"]) != 1:
        raise core.ScenarioError("PERSON-SOLO1 requires exactly one person")
    if pir["links"]:
        raise core.ScenarioError("PERSON-SOLO1 requires zero person links")
    return pir["nodes"][0], pir


def rlc_calibration(node, effective_period_hours):
    r = float(node["R"])
    c = float(node["C"])
    l = float(node["L"])
    omega0 = 1.0 / math.sqrt(l * c)
    period_model = 2.0 * math.pi / omega0

    # PERSON2 uses normalized time. SOLO1 fits exactly one conversion factor
    # instead of pretending that normalized units were already hours.
    hours_per_model_unit = effective_period_hours / period_model

    # Parallel RLC characteristic:
    # s^2 + (1/RC)s + 1/(LC) = 0
    zeta = math.sqrt(l / c) / (2.0 * r)
    envelope_tau_model = 2.0 * r * c
    envelope_tau_hours = envelope_tau_model * hours_per_model_unit
    if zeta < 1.0:
        omega_d = omega0 * math.sqrt(1.0 - zeta * zeta)
        damped_period_hours = (
            2.0 * math.pi / omega_d
        ) * hours_per_model_unit
    else:
        damped_period_hours = None

    return {
        "R": r,
        "C": c,
        "L": l,
        "C_over_L": c / l,
        "omega0_model": omega0,
        "undamped_period_model_units": period_model,
        "hours_per_model_time_unit": hours_per_model_unit,
        "parallel_damping_ratio": zeta,
        "envelope_efold_hours": envelope_tau_hours,
        "damped_period_hours": damped_period_hours,
    }


def budget_summary(scenario):
    ir = core.compile_scenario(scenario)
    finance = ir["finance"]
    stress, income, load = legacy_time._financial_stress(
        ir, finance["reserve"]
    )
    return {
        "income_monthly_normalized": income,
        "load_monthly_normalized": load,
        "net_monthly_normalized": income - load,
        "reserve_normalized": finance["reserve"],
        "runway_months": finance["reserve"] / load if load > 0 else math.inf,
        "financial_stress": stress,
    }


def forcing_area(timeline):
    events = timeline.get("события", timeline.get("events", []))
    total = 0.0
    coffee = 0
    project = 0
    for item in events:
        duration = float(item.get("длительность_дней", item.get("duration_days", 0.0)))
        drive = float(item.get("добавить_возбуждение", item.get("drive_add", 0.0)))
        total += max(0.0, duration) * max(0.0, drive)
        ident = str(item.get("id", "")).lower()
        if ident.startswith("coffee"):
            coffee += 1
        if ident.startswith("project"):
            project += 1
    return {
        "event_drive_area": total,
        "coffee_event_count": coffee,
        "project_event_count": project,
    }


def run_forcing(scenario, timeline):
    result = pts.simulate_person_timeline(scenario, timeline)
    pid = next(iter(result["summary"]["persons"]))
    p = result["summary"]["persons"][pid]
    out = forcing_area(timeline)
    out.update({
        "peak_voltage_abs": p["peak_voltage_abs"],
        "peak_voltage_day": p["peak_voltage_day"],
        "peak_memory": p["peak_memory"],
        "final_memory": p["final_memory"],
        "final_voltage": p["final_voltage"],
        "peak_financial_stress": result["summary"]["peak_financial_stress"],
    })
    return out


def calibrate(scenario, observations, historical=None, current=None):
    node, pir = require_single_person(scenario)
    wake = estimate_wake_period(observations)
    result = {
        "model_version": VERSION,
        "scenario_name": scenario.get("название", "PERSON-SOLO1"),
        "person_id": node["id"],
        "person_ir": {
            "R": node["R"],
            "C": node["C"],
            "L": node["L"],
            "role_balance": node.get("role_balance"),
            "effective_orientation": node.get("effective_orientation"),
            "gender_prior_used": node.get("legacy_orientation"),
        },
        "wake_period_fit": wake,
        "rlc_time_calibration": rlc_calibration(
            node, wake["effective_period_hours"]
        ),
        "budget": budget_summary(scenario),
        "limitations": [
            "The 25-hour value is inferred from the supplied wake-phase observations.",
            "Coffee/project events are forcing proxies, not identified causal coefficients.",
            "The fitted hours-per-model-unit scale is an internal calibration convention.",
            "PERSON-SOLO1 is not a medical or psychological sleep predictor.",
        ],
    }
    if historical is not None:
        result["historical_forcing"] = run_forcing(scenario, historical)
    if current is not None:
        result["current_forcing"] = run_forcing(scenario, current)
    return result


def report(result):
    w = result["wake_period_fit"]
    r = result["rlc_time_calibration"]
    b = result["budget"]
    lines = [
        "# PERSON-SOLO1 calibration report",
        "",
        f"**Person:** {result['person_id']}",
        f"**Model:** {result['model_version']}",
        "",
        "## PERSON2 node",
        "",
        f"- R = {r['R']:.6f}",
        f"- C = {r['C']:.6f}",
        f"- L = {r['L']:.6f}",
        f"- C/L = {r['C_over_L']:.6f}",
        f"- parallel damping ratio = {r['parallel_damping_ratio']:.6f}",
        "",
        "## Wake-phase calibration",
        "",
        f"- observed wake drift = {w['wake_offset_slope_hours_per_calendar_day']:.6f} h/day",
        f"- inferred effective period = {w['effective_period_hours']:.6f} h",
        f"- fit RMSE = {w['fit_rmse_hours']:.6f} h",
        f"- calibrated time scale = {r['hours_per_model_time_unit']:.6f} h/model-unit",
        f"- RLC envelope e-fold = {r['envelope_efold_hours']:.6f} h",
        "",
        "## Minimal budget",
        "",
        f"- normalized income = {b['income_monthly_normalized']:.6f}",
        f"- normalized load = {b['load_monthly_normalized']:.6f}",
        f"- net = {b['net_monthly_normalized']:.6f}",
        f"- runway = {b['runway_months']:.6f} months",
        f"- financial stress = {b['financial_stress']:.6f}",
    ]
    for key, title in (
        ("historical_forcing", "Historical daily-coffee forcing"),
        ("current_forcing", "Current sparse-coffee forcing"),
    ):
        if key not in result:
            continue
        x = result[key]
        lines += [
            "",
            f"## {title}",
            "",
            f"- coffee events = {x['coffee_event_count']}",
            f"- project events = {x['project_event_count']}",
            f"- event drive area = {x['event_drive_area']:.6f}",
            f"- peak |v| = {x['peak_voltage_abs']:.6f}",
            f"- peak day = {x['peak_voltage_day']:.6f}",
            f"- final memory = {x['final_memory']:.6f}",
        ]
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This calibration reproduces the supplied phase drift by fitting the PERSON2 time scale.",
        "It does not infer that caffeine caused the drift and does not diagnose a sleep disorder.",
        "",
    ]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="PERSON-SOLO1 one-person calibration")
    p.add_argument("scenario")
    p.add_argument("observations")
    p.add_argument("--historical-timeline")
    p.add_argument("--current-timeline")
    p.add_argument("--out", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    scenario = load_json(args.scenario)
    observations = load_json(args.observations)
    historical = load_json(args.historical_timeline) if args.historical_timeline else None
    current = load_json(args.current_timeline) if args.current_timeline else None
    result = calibrate(scenario, observations, historical, current)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "person_solo_calibration.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.out / "person_solo_report.md").write_text(
            report(result), encoding="utf-8"
        )

    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else report(result))


if __name__ == "__main__":
    main()
