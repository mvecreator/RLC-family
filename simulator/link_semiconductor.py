#!/usr/bin/env python3
"""LINK-SEMI1 nonlinear relationship-channel elements.

The element models are normalized engineering analogies. They are not literal
electronic devices and do not assign social meaning automatically.

Supported:
- RESISTIVE
- DIODE
- MOSFET
- BREAKDOWN_DIODE
"""

from __future__ import annotations

import math

VERSION = "RLC-FAMILY-LINK-SEMI1-0.1"

ELEMENT_TYPES = {
    "RESISTIVE",
    "DIODE",
    "MOSFET",
    "BREAKDOWN_DIODE",
}


def clip(value, lo, hi):
    return max(lo, min(hi, float(value)))


def sigmoid(x):
    x = clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + math.exp(-x))


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


def normalize_type(value):
    kind = str(value or "RESISTIVE").strip().upper()
    aliases = {
        "R": "RESISTIVE",
        "RESISTOR": "RESISTIVE",
        "D": "DIODE",
        "TRANSISTOR": "MOSFET",
        "FET": "MOSFET",
        "ZENER": "BREAKDOWN_DIODE",
        "AVALANCHE_DIODE": "BREAKDOWN_DIODE",
    }
    kind = aliases.get(kind, kind)
    if kind not in ELEMENT_TYPES:
        raise ValueError(
            "element_type must be one of "
            + ", ".join(sorted(ELEMENT_TYPES))
        )
    return kind


def compile_element(item, r_link):
    kind = normalize_type(
        item.get("element_type", item.get("link_element", "RESISTIVE"))
    )
    r_link = positive(r_link, "R_link")

    out = {
        "element_type": kind,
        "nonlinear": kind != "RESISTIVE",
    }

    if kind == "RESISTIVE":
        return out

    if kind == "DIODE":
        out.update({
            "forward_threshold": nonnegative(
                item.get("forward_threshold", 0.05),
                "forward_threshold",
            ),
            "softness": positive(
                item.get("softness", 0.02),
                "softness",
            ),
            "reverse_ratio": clip(
                item.get("reverse_ratio", 0.05),
                0.0,
                1.0,
            ),
        })
        return out

    if kind == "MOSFET":
        out.update({
            "gate": clip(item.get("gate", 0.5), 0.0, 1.0),
            "gate_threshold": clip(
                item.get("gate_threshold", 0.5),
                0.0,
                1.0,
            ),
            "gate_softness": positive(
                item.get("gate_softness", 0.08),
                "gate_softness",
            ),
            "off_ratio": clip(
                item.get("off_ratio", 0.02),
                0.0,
                1.0,
            ),
            "reverse_ratio": clip(
                item.get("reverse_ratio", 0.20),
                0.0,
                1.0,
            ),
            "gate_semantics": str(
                item.get(
                    "gate_semantics",
                    "external authority/contract/permission factor",
                )
            ),
        })
        return out

    if kind == "BREAKDOWN_DIODE":
        out.update({
            "forward_threshold": nonnegative(
                item.get("forward_threshold", 0.05),
                "forward_threshold",
            ),
            "softness": positive(
                item.get("softness", 0.02),
                "softness",
            ),
            "reverse_ratio": clip(
                item.get("reverse_ratio", 0.01),
                0.0,
                1.0,
            ),
            "breakdown_threshold": positive(
                item.get("breakdown_threshold", 0.35),
                "breakdown_threshold",
            ),
            "breakdown_softness": positive(
                item.get("breakdown_softness", 0.03),
                "breakdown_softness",
            ),
            "breakdown_gain": positive(
                item.get("breakdown_gain", 1.5),
                "breakdown_gain",
            ),
        })
        return out

    raise AssertionError(kind)


def _direction_factor(delta_v, reverse_ratio, softness=0.02):
    """1 in forward direction, reverse_ratio in reverse, smooth at zero."""
    s = sigmoid(float(delta_v) / positive(softness, "softness"))
    return reverse_ratio + (1.0 - reverse_ratio) * s


def conductance(link, delta_v):
    """Instantaneous normalized conductance at a real-valued delta V."""
    kind = normalize_type(link.get("element_type", "RESISTIVE"))
    base_g = 1.0 / positive(link["R_link"], "R_link")
    dv = float(delta_v)

    if kind == "RESISTIVE":
        return base_g

    if kind == "DIODE":
        threshold = float(link["forward_threshold"])
        softness = float(link["softness"])
        reverse = float(link["reverse_ratio"])
        forward_open = sigmoid((dv - threshold) / softness)
        return base_g * (
            reverse + (1.0 - reverse) * forward_open
        )

    if kind == "MOSFET":
        gate = clip(link.get("gate", 0.5), 0.0, 1.0)
        gate_threshold = clip(
            link.get("gate_threshold", 0.5), 0.0, 1.0
        )
        gate_softness = positive(
            link.get("gate_softness", 0.08),
            "gate_softness",
        )
        off_ratio = clip(link.get("off_ratio", 0.02), 0.0, 1.0)
        reverse_ratio = clip(
            link.get("reverse_ratio", 0.20), 0.0, 1.0
        )
        gate_open = sigmoid(
            (gate - gate_threshold) / gate_softness
        )
        gate_factor = off_ratio + (1.0 - off_ratio) * gate_open
        direction = _direction_factor(
            dv, reverse_ratio, softness=0.02
        )
        return base_g * gate_factor * direction

    if kind == "BREAKDOWN_DIODE":
        threshold = float(link["forward_threshold"])
        softness = float(link["softness"])
        reverse = float(link["reverse_ratio"])
        forward_open = sigmoid((dv - threshold) / softness)
        g = base_g * (
            reverse + (1.0 - reverse) * forward_open
        )

        # In reverse direction, large |delta V| can open an avalanche-like
        # path. The current remains zero at delta V = 0 because I = G * dV.
        reverse_magnitude = max(0.0, -dv)
        breakdown_open = sigmoid(
            (
                reverse_magnitude
                - float(link["breakdown_threshold"])
            )
            / float(link["breakdown_softness"])
        )
        g += (
            base_g
            * float(link["breakdown_gain"])
            * breakdown_open
        )
        return g

    raise AssertionError(kind)


def current(link, v_from, v_to):
    dv = float(v_from) - float(v_to)
    return dv * conductance(link, dv)


def power(link, v_from, v_to):
    """Universal dissipative power proxy |delta V * I|."""
    dv = float(v_from) - float(v_to)
    i = current(link, v_from, v_to)
    return abs(dv * i)


def probe(link, deltas):
    return [
        {
            "delta_v": float(dv),
            "current": current(link, float(dv), 0.0),
            "conductance": conductance(link, float(dv)),
            "power": power(link, float(dv), 0.0),
        }
        for dv in deltas
    ]


def is_nonlinear(link):
    return normalize_type(
        link.get("element_type", "RESISTIVE")
    ) != "RESISTIVE"
