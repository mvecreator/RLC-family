#!/usr/bin/env python3
"""RHYTHM-25H1: per-person intrinsic-day / external-schedule phase model.

The layer is deliberately non-clinical. It models a person's declared internal
cycle length and the mismatch against an external schedule. A 25-hour intrinsic
cycle is not itself treated as stress. Load appears only when schedule_lock > 0.

No medical diagnosis or claim about sleep disorders is made.
"""

from __future__ import annotations

import math

VERSION = "RLC-FAMILY-RHYTHM-25H1-0.1"

DEFAULT_EXTERNAL_DAY_HOURS = 24.0
DEFAULT_INTRINSIC_DAY_HOURS = 24.0


def clip01(value):
    return max(0.0, min(1.0, float(value)))


def _positive(value, name):
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def _unit(value, name):
    value = float(value)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0,1]")
    return value


def compile_person_rhythm(person, model=None):
    model = model or {}
    rhythm = person.get("rhythm") or {}
    if not isinstance(rhythm, dict):
        raise ValueError("person.rhythm must be object")

    external = _positive(
        model.get("external_day_hours", DEFAULT_EXTERNAL_DAY_HOURS),
        "rhythm_model.external_day_hours",
    )
    intrinsic = _positive(
        rhythm.get(
            "intrinsic_day_hours",
            DEFAULT_INTRINSIC_DAY_HOURS,
        ),
        "rhythm.intrinsic_day_hours",
    )
    schedule_lock = _unit(
        rhythm.get("schedule_lock", 0.0),
        "rhythm.schedule_lock",
    )
    mismatch_load_gain = _unit(
        rhythm.get("mismatch_load_gain", 0.20),
        "rhythm.mismatch_load_gain",
    )
    recovery_penalty_gain = _unit(
        rhythm.get("recovery_penalty_gain", 0.25),
        "rhythm.recovery_penalty_gain",
    )
    phase_offset_hours = float(rhythm.get("phase_offset_hours", 0.0))

    return {
        "intrinsic_day_hours": intrinsic,
        "external_day_hours": external,
        "schedule_lock": schedule_lock,
        "mismatch_load_gain": mismatch_load_gain,
        "recovery_penalty_gain": recovery_penalty_gain,
        "phase_offset_hours": phase_offset_hours,
        "enabled": bool(
            abs(intrinsic - external) > 1e-12
            or schedule_lock > 0.0
            or abs(phase_offset_hours) > 1e-12
        ),
    }


def relative_phase_cycles(compiled, t_days):
    """Internal minus external phase, wrapped to [-0.5, 0.5)."""
    ext_h = compiled["external_day_hours"]
    int_h = compiled["intrinsic_day_hours"]
    elapsed_h = 24.0 * float(t_days)

    internal_cycles = (
        elapsed_h + compiled["phase_offset_hours"]
    ) / int_h
    external_cycles = elapsed_h / ext_h
    diff = internal_cycles - external_cycles
    return ((diff + 0.5) % 1.0) - 0.5


def phase_mismatch(compiled, t_days):
    """0 when phases align, 1 at half-cycle opposition."""
    diff = relative_phase_cycles(compiled, t_days)
    return 0.5 * (1.0 - math.cos(2.0 * math.pi * diff))


def state(compiled, t_days):
    diff_cycles = relative_phase_cycles(compiled, t_days)
    mismatch = phase_mismatch(compiled, t_days)
    schedule_lock = compiled["schedule_lock"]

    schedule_mismatch_load = (
        schedule_lock
        * compiled["mismatch_load_gain"]
        * mismatch
    )
    recovery_inertia_add = (
        schedule_lock
        * compiled["recovery_penalty_gain"]
        * mismatch
    )

    external_phase_hours = (
        diff_cycles * compiled["external_day_hours"]
    )

    return {
        "relative_phase_cycles": diff_cycles,
        "relative_phase_hours_external": external_phase_hours,
        "phase_mismatch": mismatch,
        "schedule_mismatch_load": schedule_mismatch_load,
        "recovery_inertia_add": recovery_inertia_add,
    }


def daily_phase_drift_hours(compiled):
    """Signed relative phase drift per external day, in external-clock hours."""
    ext = compiled["external_day_hours"]
    intr = compiled["intrinsic_day_hours"]
    drift_cycles = ext / intr - 1.0
    return drift_cycles * ext
