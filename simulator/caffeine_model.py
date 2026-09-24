#!/usr/bin/env python3
"""CAFFEINE1: configurable first-order caffeine burden model.

This is a research feature layer for RLC-family. It is not a medical dosing
calculator and does not diagnose or predict a sleep disorder.
"""

from __future__ import annotations

import math

VERSION = "RLC-FAMILY-CAFFEINE1-0.1"
DEFAULT_HALF_LIFE_HOURS = 5.0
REFERENCE_DOSE_MG = 100.0


def positive(value, name):
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def nonnegative(value, name):
    value = float(value)
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def elimination_constant(half_life_hours=DEFAULT_HALF_LIFE_HOURS):
    half_life_hours = positive(half_life_hours, "half_life_hours")
    return math.log(2.0) / half_life_hours


def remaining_fraction(hours_after_dose, half_life_hours=DEFAULT_HALF_LIFE_HOURS):
    hours_after_dose = nonnegative(hours_after_dose, "hours_after_dose")
    return math.exp(
        -elimination_constant(half_life_hours) * hours_after_dose
    )


def remaining_mg(dose_mg, hours_after_dose, half_life_hours=DEFAULT_HALF_LIFE_HOURS):
    dose_mg = nonnegative(dose_mg, "dose_mg")
    return dose_mg * remaining_fraction(hours_after_dose, half_life_hours)


def residual_at_sleep(events, half_life_hours=DEFAULT_HALF_LIFE_HOURS):
    """Sum residual caffeine at a sleep-onset reference point.

    Each event is {"dose_mg": ..., "hours_before_sleep": ...}.
    Bolus absorption is an intentional simplification.
    """
    total = 0.0
    contributions = []
    for idx, event in enumerate(events):
        dose = nonnegative(event.get("dose_mg", 0.0), f"event {idx}.dose_mg")
        lead = nonnegative(
            event.get("hours_before_sleep", 0.0),
            f"event {idx}.hours_before_sleep",
        )
        residual = remaining_mg(dose, lead, half_life_hours)
        total += residual
        contributions.append({
            "dose_mg": dose,
            "hours_before_sleep": lead,
            "residual_mg_at_sleep": residual,
            "residual_fraction": residual / dose if dose > 0 else 0.0,
        })
    return {
        "half_life_hours": float(half_life_hours),
        "residual_mg_at_sleep": total,
        "residual_reference_units": total / REFERENCE_DOSE_MG,
        "contributions": contributions,
    }


def simulate_absolute_events(
    events,
    sample_hours,
    half_life_hours=DEFAULT_HALF_LIFE_HOURS,
):
    """Superpose first-order elimination from absolute-hour bolus events."""
    compiled = []
    for idx, event in enumerate(events):
        at = nonnegative(event.get("at_hour", 0.0), f"event {idx}.at_hour")
        dose = nonnegative(event.get("dose_mg", 0.0), f"event {idx}.dose_mg")
        compiled.append((at, dose))

    rows = []
    for t in sample_hours:
        t = nonnegative(t, "sample_hour")
        burden = 0.0
        for at, dose in compiled:
            if at <= t:
                burden += remaining_mg(dose, t - at, half_life_hours)
        rows.append({
            "hour": t,
            "burden_mg_equivalent": burden,
            "burden_reference_units": burden / REFERENCE_DOSE_MG,
        })
    return rows
