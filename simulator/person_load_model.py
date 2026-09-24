#!/usr/bin/env python3
"""PERSON-LOAD1: calibrated accumulated-load semantics for individual family members.

This module is non-diagnostic. It provides project-internal engineering bands
for accumulated load and requires persistence before stronger review signals.
"""

from __future__ import annotations

VERSION = "RLC-FAMILY-PERSON-LOAD1-0.1"

COMPONENT_WEIGHTS = {
    "excitation": 0.20,
    "memory": 0.25,
    "incident_link_stress": 0.15,
    "financial_stress": 0.15,
    "forcing_exposure": 0.25,
}

FORCING_SCALE = 0.35

RECOVERY_ATTENTION = 0.35
SUSTAINED_LOAD_REVIEW = 0.50
HIGH_LOAD_REVIEW = 0.65

SUSTAINED_DWELL_DAYS = 5.0
HIGH_DWELL_DAYS = 3.0

ACCUMULATION_GAIN = 0.45
RECOVERY_GAIN = 0.14
INITIAL_LOAD = 0.20


def clip01(value):
    return max(0.0, min(1.0, float(value)))


def combine_components(
    excitation,
    memory,
    incident_link_stress,
    financial_stress,
    forcing_exposure=0.0,
):
    values = {
        "excitation": clip01(excitation),
        "memory": clip01(memory),
        "incident_link_stress": clip01(incident_link_stress),
        "financial_stress": clip01(financial_stress),
        "forcing_exposure": clip01(forcing_exposure),
    }
    return clip01(sum(
        COMPONENT_WEIGHTS[key] * values[key]
        for key in COMPONENT_WEIGHTS
    ))


def advance(
    state,
    load,
    dt,
    accumulation=ACCUMULATION_GAIN,
    recovery=RECOVERY_GAIN,
):
    state = clip01(state)
    load = clip01(load)
    dt = max(0.0, float(dt))
    return clip01(
        state
        + dt * accumulation * load * (1.0 - state)
        - dt * recovery * state
    )


def equilibrium_for_constant_load(load):
    """Closed-form equilibrium for the continuous PERSON-LOAD1 accumulator."""
    load = clip01(load)
    denom = ACCUMULATION_GAIN * load + RECOVERY_GAIN
    if denom <= 0:
        return 0.0
    return (ACCUMULATION_GAIN * load) / denom


def required_constant_load_for_equilibrium(state):
    """Inverse equilibrium map, useful for explaining calibration thresholds."""
    state = clip01(state)
    if state >= 1.0:
        return 1.0
    if state <= 0.0:
        return 0.0
    return (
        RECOVERY_GAIN * state
        / (ACCUMULATION_GAIN * (1.0 - state))
    )


def _person_value(row, pid):
    return float(row["persons"][pid]["accumulated_load"])


def first_crossing(rows, pid, threshold):
    for row in rows:
        if _person_value(row, pid) >= threshold:
            return float(row["day"])
    return None


def first_sustained_crossing(rows, pid, threshold, dwell_days):
    """Return the day on which a continuous above-threshold dwell completes."""
    start = None
    for row in rows:
        day = float(row["day"])
        value = _person_value(row, pid)
        if value >= threshold:
            if start is None:
                start = day
            if day - start + 1e-12 >= dwell_days:
                return start + dwell_days
        else:
            start = None
    return None


def _component_means(rows, pid):
    fields = (
        "excitation",
        "memory",
        "incident_link_stress",
        "financial_stress",
        "forcing_exposure",
    )
    out = {}
    for field in fields:
        values = [
            float(row["persons"][pid].get(field, 0.0))
            for row in rows
        ]
        out[field] = sum(values) / len(values)
    return out


def _component_peaks(rows, pid):
    fields = (
        "excitation",
        "memory",
        "incident_link_stress",
        "financial_stress",
        "forcing_exposure",
    )
    return {
        field: max(float(row["persons"][pid].get(field, 0.0)) for row in rows)
        for field in fields
    }


def _dominant_component(means):
    return max(means, key=means.get) if means else None


def classify(rows, pid):
    values = [
        (float(row["day"]), _person_value(row, pid))
        for row in rows
    ]
    peak_day, peak = max(values, key=lambda x: x[1])
    final = values[-1][1]

    recovery_day = first_crossing(rows, pid, RECOVERY_ATTENTION)
    sustained_day = first_sustained_crossing(
        rows, pid, SUSTAINED_LOAD_REVIEW, SUSTAINED_DWELL_DAYS
    )
    high_day = first_sustained_crossing(
        rows, pid, HIGH_LOAD_REVIEW, HIGH_DWELL_DAYS
    )

    if high_day is not None:
        band = "HIGH_LOAD_REVIEW"
    elif sustained_day is not None:
        band = "SUSTAINED_LOAD_REVIEW"
    elif recovery_day is not None:
        band = "RECOVERY_ATTENTION"
    else:
        band = "STABLE"

    means = _component_means(rows, pid)
    peaks = _component_peaks(rows, pid)
    return {
        "band": band,
        "peak_load": {"day": peak_day, "value": peak},
        "final_load": final,
        "first_recovery_attention_day": recovery_day,
        "first_sustained_load_review_day": sustained_day,
        "first_high_load_review_day": high_day,
        "mean_components": means,
        "peak_components": peaks,
        "dominant_mean_component": _dominant_component(means),
        "thresholds": {
            "recovery_attention": RECOVERY_ATTENTION,
            "sustained_load_review": SUSTAINED_LOAD_REVIEW,
            "high_load_review": HIGH_LOAD_REVIEW,
            "sustained_dwell_days": SUSTAINED_DWELL_DAYS,
            "high_dwell_days": HIGH_DWELL_DAYS,
        },
    }


def recommendations(summary, kind="adult"):
    """Translate calibrated state into non-clinical load-management actions."""
    band = summary["band"]
    means = summary["mean_components"]
    kind = str(kind or "adult").lower()
    child = kind == "child"
    actions = []

    if means["forcing_exposure"] >= 0.25:
        actions.append({
            "action": "REDUCE_AVOIDABLE_FORCING",
            "reason": "forcing_exposure",
            "message": (
                "Sustained direct forcing is a major contributor; reduce or "
                "redistribute avoidable demands before relying on transient voltage alone."
            ),
        })
    if means["financial_stress"] >= 0.25:
        actions.append({
            "action": "REDUCE_SHARED_FINANCIAL_PRESSURE",
            "reason": "financial_stress",
            "message": (
                "Treat financial pressure as an external shared load rather than "
                "as a personal failure."
            ),
        })
    if means["incident_link_stress"] >= 0.20:
        actions.append({
            "action": "REDUCE_RELATIONSHIP_LOAD_AROUND_PERSON",
            "reason": "incident_link_stress",
            "message": (
                "Reduce repeated high-friction exchanges around this person and "
                "protect lower-conflict communication windows."
            ),
        })
    if means["memory"] >= 0.35:
        actions.append({
            "action": "PROTECT_RECOVERY_WINDOW",
            "reason": "memory",
            "message": (
                "Accumulated memory is a major load contributor; allow recovery "
                "before replaying the same stressor."
            ),
        })
    if means["excitation"] >= 0.35:
        actions.append({
            "action": "REDUCE_TRANSIENT_EXCITATION",
            "reason": "excitation",
            "message": (
                "Transient local excitation is a major contributor; protect a "
                "recovery window before adding more stimulation."
            ),
        })

    if band == "RECOVERY_ATTENTION":
        actions.append({
            "action": (
                "CAREGIVER_RECOVERY_ATTENTION" if child
                else "RECOVERY_ATTENTION"
            ),
            "reason": "accumulated_load",
            "message": (
                "The accumulated load has left the stable band. Protect recovery "
                "and watch whether it returns below the threshold."
            ),
        })
    elif band == "SUSTAINED_LOAD_REVIEW":
        actions.append({
            "action": (
                "CAREGIVER_LOAD_REVIEW" if child
                else "SUSTAINED_LOAD_REVIEW"
            ),
            "reason": "persistent_accumulated_load",
            "message": (
                "The load stayed elevated long enough to count as sustained in "
                "the project model. Review the dominant causes and recovery."
            ),
        })
    elif band == "HIGH_LOAD_REVIEW":
        actions.append({
            "action": (
                "CAREGIVER_HIGH_LOAD_REVIEW" if child
                else "HIGH_LOAD_REVIEW"
            ),
            "reason": "persistent_high_accumulated_load",
            "message": (
                "The load stayed in the high model band. Reduce major stressors "
                "and review whether the person is actually recovering."
            ),
        })

    return actions
