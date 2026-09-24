#!/usr/bin/env python3
"""CAFFEINE1 calibration and sensitivity checks."""

from __future__ import annotations

import json

from simulator import caffeine_model as caffeine
from simulator import sleep_trajectory_model as sleep


def suite():
    early = caffeine.residual_at_sleep([
        {"dose_mg": 100, "hours_before_sleep": 10}
    ])
    six = caffeine.residual_at_sleep([
        {"dose_mg": 100, "hours_before_sleep": 6}
    ])
    late = caffeine.residual_at_sleep([
        {"dose_mg": 100, "hours_before_sleep": 3}
    ])

    absolute_events = [
        {"at_hour": 0, "dose_mg": 100},
        {"at_hour": 24, "dose_mg": 100},
        {"at_hour": 48, "dose_mg": 100},
    ]
    carry = caffeine.simulate_absolute_events(
        absolute_events,
        [0, 24, 48, 54],
    )

    tr = sleep.trajectory(21)
    stages = {row["stage"] for row in tr}

    checks = {
        "CAF01_HALF_LIFE": abs(
            caffeine.remaining_fraction(5.0) - 0.5
        ) < 1e-12,
        "CAF02_TIMING_ORDER": (
            late["residual_mg_at_sleep"]
            > six["residual_mg_at_sleep"]
            > early["residual_mg_at_sleep"]
        ),
        "CAF03_SUPERPOSITION": (
            carry[2]["burden_mg_equivalent"] > 100.0
        ),
        "CAF04_SLEEP_SPLIT_EMERGES": "SPLIT_EMERGING" in stages,
        "CAF05_BIPHASIC_MATURE": "BIPHASIC_MATURE" in stages,
        "CAF06_SECONDARY_RESOLVES": (
            "SECONDARY_BOUT_RESOLVING" in stages
            and tr[-1]["stage"] == "MONOPHASIC_RECOVERED"
        ),
        "CAF07_SECONDARY_WEIGHT_FADES": (
            sleep.state(0.75)["secondary_bout_weight"]
            > sleep.state(0.90)["secondary_bout_weight"]
            > sleep.state(1.00)["secondary_bout_weight"]
        ),
        "CAF08_TEMPORAL_STRETCH_GROWS": (
            sleep.state(0.75)["secondary_temporal_stretch_index"]
            < sleep.state(0.90)["secondary_temporal_stretch_index"]
            < sleep.state(1.00)["secondary_temporal_stretch_index"]
        ),
    }

    return {
        "model": caffeine.VERSION,
        "half_life_reference_hours": caffeine.DEFAULT_HALF_LIFE_HOURS,
        "timing_reference_100mg": {
            "10h_before_sleep_residual_mg": early["residual_mg_at_sleep"],
            "6h_before_sleep_residual_mg": six["residual_mg_at_sleep"],
            "3h_before_sleep_residual_mg": late["residual_mg_at_sleep"],
        },
        "sleep_trajectory": tr,
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
