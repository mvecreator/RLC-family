#!/usr/bin/env python3
"""Qualitative sleep-architecture trajectory for SOLO/OUTCOME-BLIND1.

The trajectory represents an observed sequence:
monophasic -> gradual split -> mature biphasic -> secondary bout fades while
its temporal separation stretches -> monophasic again.

Exact calendar timing and bout duration remain unidentified.
"""

from __future__ import annotations

VERSION = "RLC-FAMILY-SLEEP-TRAJECTORY1-0.1"


def clip01(x):
    return max(0.0, min(1.0, float(x)))


def smoothstep(x):
    x = clip01(x)
    return x * x * (3.0 - 2.0 * x)


def state(progress):
    """Return qualitative sleep state for normalized history progress [0,1]."""
    u = clip01(progress)

    if u < 0.25:
        stage = "MONOPHASIC_BASELINE"
        split = 0.0
        secondary = 0.0
        gap = 0.0
        stretch = 0.0
    elif u < 0.50:
        stage = "SPLIT_EMERGING"
        x = smoothstep((u - 0.25) / 0.25)
        split = x
        secondary = x
        gap = 2.5 * x
        stretch = 0.0
    elif u < 0.70:
        stage = "BIPHASIC_MATURE"
        split = 1.0
        secondary = 1.0
        gap = 2.5
        stretch = 0.0
    else:
        stage = "SECONDARY_BOUT_RESOLVING"
        x = smoothstep((u - 0.70) / 0.30)
        split = 1.0 - x
        secondary = 1.0 - x
        # We do not invent a final gap in hours. The user observation only
        # identifies increasing temporal separation/stretch while the second
        # bout fades, so expose a dimensionless index.
        gap = None
        stretch = x

    if u >= 0.995:
        stage = "MONOPHASIC_RECOVERED"
        split = 0.0
        secondary = 0.0
        gap = None
        stretch = 1.0

    return {
        "progress": u,
        "stage": stage,
        "split_strength": split,
        "secondary_bout_weight": secondary,
        "inter_bout_gap_hours_when_identified": gap,
        "secondary_temporal_stretch_index": stretch,
        "secondary_bout_present": secondary > 0.10,
    }


def trajectory(points=21):
    points = max(2, int(points))
    return [state(i / (points - 1)) for i in range(points)]
