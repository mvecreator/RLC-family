#!/usr/bin/env python3
"""PERSON-SAFETY1: non-diagnostic accumulated-load and care-escalation layer.

This module intentionally does NOT estimate probability of psychosis.
It tracks a project-internal stress/load index and keeps clinical red flags
separate from RLC state.

Safety policy:
- persistent unusual sleep disruption -> suggest routine clinician/GP review;
- explicit psychosis-type symptoms -> urgent medical review;
- immediate danger / inability to stay safe -> emergency help.

The numeric thresholds are engineering guardrails for RLC-family, not validated
medical cut-offs.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    from simulator import person_solo_calibration as solo
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import person_solo_calibration as solo
    import rlc_family_sim as core

VERSION = "RLC-FAMILY-PERSON-SAFETY1-0.1"

RED_FLAG_KEYS = (
    "hallucinations",
    "delusions",
    "confused_or_disordered_thinking",
)

EMERGENCY_KEYS = (
    "cannot_keep_self_safe",
    "risk_of_harm_to_self_or_others",
)


def _clip01(x):
    return max(0.0, min(1.0, float(x)))


def _timeline_days(timeline):
    cfg = timeline.get("моделирование", timeline.get("simulation", {}))
    if not isinstance(cfg, dict):
        raise core.ScenarioError("timeline simulation config must be object")
    return core.positive(cfg.get("дней", cfg.get("days", 7)), "timeline days")


def load_components(scenario, observations, timeline):
    wake = solo.estimate_wake_period(observations)
    sleep = solo.estimate_sleep_architecture(
        observations, wake["effective_period_hours"]
    )
    budget = solo.budget_summary(scenario)
    forcing = solo.forcing_area(timeline)
    days = _timeline_days(timeline)

    # Internal normalized engineering proxies, not medical scales.
    phase_instability = _clip01(
        abs(wake["wake_offset_slope_hours_per_calendar_day"]) / 2.0
    )
    if sleep.get("available"):
        fragmentation = _clip01(
            0.35
            + sleep["inter_bout_gap_fraction_of_cycle_midpoint"]
        )
    else:
        fragmentation = 0.0

    forcing_density = forcing["event_drive_area"] / days
    forcing_load = _clip01(forcing_density / 0.40)
    financial_load = _clip01(budget["financial_stress"])

    combined = _clip01(
        0.25 * phase_instability
        + 0.30 * fragmentation
        + 0.20 * financial_load
        + 0.25 * forcing_load
    )
    return {
        "phase_instability": phase_instability,
        "sleep_fragmentation": fragmentation,
        "financial_load": financial_load,
        "forcing_load": forcing_load,
        "forcing_density_per_day": forcing_density,
        "combined_daily_load": combined,
    }


def stress_trajectory(
    components,
    days=30,
    initial_stress=0.20,
    accumulation_gain=0.30,
    recovery_gain=0.12,
):
    """Integrate a bounded engineering load index once per day.

    s[t+1] = s[t] + a*L*(1-s[t]) - r*s[t]

    The saturation term prevents unbounded growth. This is a project heuristic,
    not a physiological stress equation.
    """
    days = int(core.positive(days, "stress days"))
    s = _clip01(initial_stress)
    load = _clip01(components["combined_daily_load"])
    rows = []
    for day in range(days + 1):
        rows.append({
            "day": day,
            "stress_load": s,
            "combined_daily_load": load,
        })
        s = _clip01(
            s
            + accumulation_gain * load * (1.0 - s)
            - recovery_gain * s
        )
    return rows


def first_crossing(rows, threshold):
    for row in rows:
        if row["stress_load"] >= threshold:
            return row["day"]
    return None


def _truthy_flag(flags, key):
    value = flags.get(key)
    return value is True


def clinical_safety(flags=None):
    """Interpret only explicitly supplied clinical observations.

    Missing keys mean UNKNOWN, never "absent".
    """
    flags = flags or {}
    if not isinstance(flags, dict):
        raise core.ScenarioError("clinical_flags must be object")

    emergency = [k for k in EMERGENCY_KEYS if _truthy_flag(flags, k)]
    psychosis_red = [k for k in RED_FLAG_KEYS if _truthy_flag(flags, k)]
    functioning = _truthy_flag(flags, "daily_functioning_impairment")

    if emergency:
        return {
            "level": "EMERGENCY",
            "triggered_by": emergency,
            "message": (
                "Seek emergency medical help now; do not use the RLC score "
                "to delay care."
            ),
        }
    if psychosis_red:
        return {
            "level": "URGENT_MEDICAL_REVIEW",
            "triggered_by": psychosis_red,
            "message": (
                "Seek urgent medical assessment. Explicit psychosis-type "
                "symptoms override all numeric RLC/load scores."
            ),
        }
    if functioning:
        return {
            "level": "GP_REVIEW",
            "triggered_by": ["daily_functioning_impairment"],
            "message": (
                "Arrange a clinician/GP review because sleep or stress is "
                "affecting day-to-day functioning."
            ),
        }
    return {
        "level": "NOT_ASSESSED_FOR_RED_FLAGS",
        "triggered_by": [],
        "message": (
            "No clinical red flag was supplied to the model. This is unknown, "
            "not a negative medical screen."
        ),
    }


def care_signals(rows, observations, clinical=None):
    """Generate conservative project guardrails.

    Numeric thresholds are internal engineering signals only.
    """
    sleep = observations.get("sleep_architecture")
    persistent_pattern = isinstance(sleep, dict) and (
        sleep.get("transition") == "gradual_monophasic_to_biphasic"
    )

    monitor_day = first_crossing(rows, 0.45)
    elevated_day = first_crossing(rows, 0.55)

    signals = []
    if monitor_day is not None:
        signals.append({
            "level": "SELF_MONITOR",
            "day": monitor_day,
            "reason": "accumulated_load",
            "message": (
                "Load is accumulating: protect recovery, reduce avoidable "
                "forcing and keep the sleep pattern under observation."
            ),
        })

    # Conservative project rule: persistent unusual sleep architecture plus
    # sustained elevated load for two weeks should trigger routine clinician
    # review. 14 days is a project guardrail, not a medical diagnostic cutoff.
    if persistent_pattern and elevated_day is not None and len(rows) > 14:
        signals.append({
            "level": "GP_REVIEW",
            "day": max(14, elevated_day),
            "reason": "persistent_sleep_disruption_plus_accumulated_load",
            "message": (
                "If this unusual sleep pattern is persisting, arrange a "
                "routine clinician/GP review rather than waiting for the "
                "numeric load to become extreme."
            ),
        })

    clinical_result = clinical_safety(clinical)
    if clinical_result["level"] in {
        "GP_REVIEW", "URGENT_MEDICAL_REVIEW", "EMERGENCY"
    }:
        signals.append({
            "level": clinical_result["level"],
            "day": 0,
            "reason": "explicit_clinical_observation",
            "message": clinical_result["message"],
            "triggered_by": clinical_result["triggered_by"],
        })

    return {
        "signals": signals,
        "clinical_red_flags": clinical_result,
        "numeric_score_is_diagnostic": False,
        "psychosis_probability_computed": False,
    }


def assess(scenario, observations, timeline, days=30, clinical=None):
    components = load_components(scenario, observations, timeline)
    rows = stress_trajectory(components, days=days)
    care = care_signals(rows, observations, clinical)
    return {
        "model_version": VERSION,
        "components": components,
        "trajectory": rows,
        "summary": {
            "initial_stress_load": rows[0]["stress_load"],
            "stress_load_day_7": rows[min(7, len(rows)-1)]["stress_load"],
            "stress_load_day_14": rows[min(14, len(rows)-1)]["stress_load"],
            "final_stress_load": rows[-1]["stress_load"],
            "first_self_monitor_day": first_crossing(rows, 0.45),
            "first_elevated_load_day": first_crossing(rows, 0.55),
        },
        "care": care,
        "limitations": [
            "stress_load is an internal engineering index, not a clinical scale",
            "the model does not calculate psychosis probability",
            "clinical red flags must be explicitly observed/reported, not inferred from RLC state",
            "sleep fragmentation and 25-hour drift are inputs, not diagnoses",
        ],
    }


def main():
    p = argparse.ArgumentParser(description="PERSON-SAFETY1 accumulated-load layer")
    p.add_argument("scenario")
    p.add_argument("observations")
    p.add_argument("timeline")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--clinical-flags")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    scenario = solo.load_json(args.scenario)
    observations = solo.load_json(args.observations)
    timeline = solo.load_json(args.timeline)
    clinical = (
        solo.load_json(args.clinical_flags)
        if args.clinical_flags else None
    )
    result = assess(
        scenario, observations, timeline, args.days, clinical
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
