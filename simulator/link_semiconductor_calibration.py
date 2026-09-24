#!/usr/bin/env python3
"""LINK-SEMI-CAL1: calibration gates for nonlinear relationship links."""

from __future__ import annotations

import json

from simulator import link_semiconductor as semi
from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core


def _link(kind, **kwargs):
    base = {
        "R_link": 1.0,
        "element_type": kind,
    }
    base.update(kwargs)
    return base


def _two_adults(link):
    return {
        "person_model": {"gender_prior_strength": 0},
        "персонажи": [
            {"id": "a", "type": "adult", "gender": "male"},
            {"id": "b", "type": "adult", "gender": "female"},
        ],
        "связи_персонажей": [
            dict({"from": "a", "to": "b", "quality": 0.80}, **link)
        ],
    }


def suite():
    resistor = _link("RESISTIVE")
    diode = _link(
        "DIODE",
        forward_threshold=0.05,
        softness=0.02,
        reverse_ratio=0.05,
    )
    mos_off = _link(
        "MOSFET",
        gate=0.10,
        gate_threshold=0.50,
        gate_softness=0.08,
        off_ratio=0.02,
        reverse_ratio=0.20,
    )
    mos_on = dict(mos_off)
    mos_on["gate"] = 0.90
    breakdown = _link(
        "BREAKDOWN_DIODE",
        forward_threshold=0.05,
        softness=0.02,
        reverse_ratio=0.01,
        breakdown_threshold=0.35,
        breakdown_softness=0.03,
        breakdown_gain=1.50,
    )

    r_forward = semi.current(resistor, 0.20, 0.0)
    r_reverse = semi.current(resistor, -0.20, 0.0)
    d_forward = semi.current(diode, 0.20, 0.0)
    d_reverse = semi.current(diode, -0.20, 0.0)
    mos_low = semi.current(mos_off, 0.20, 0.0)
    mos_high = semi.current(mos_on, 0.20, 0.0)
    mos_high_reverse = semi.current(mos_on, -0.20, 0.0)
    bd_sub = semi.current(breakdown, -0.20, 0.0)
    bd_over = semi.current(breakdown, -0.60, 0.0)

    compiled_legacy = pm.compile_person_network(
        _two_adults({})
    )["links"][0]
    compiled_mos = pm.compile_person_network(
        _two_adults({
            "element_type": "MOSFET",
            "gate": 0.80,
            "gate_semantics": "authority_contract",
        })
    )["links"][0]

    events = pts._compile_events(
        {
            "события": [{
                "id": "gate-close",
                "день": 0,
                "длительность_дней": 1,
                "связь": ["a", "b"],
                "gate_set": 0.15,
            }]
        },
        {"a", "b"},
        {("a", "b")},
    )
    base_ir = pm.compile_person_network(
        _two_adults({
            "element_type": "MOSFET",
            "gate": 0.80,
        })
    )
    _, changed_links, _ = pts._network_at(
        _two_adults({
            "element_type": "MOSFET",
            "gate": 0.80,
        }),
        base_ir,
        events,
        0.5,
    )

    bad_gate_rejected = False
    try:
        bad_ir = pm.compile_person_network(_two_adults({}))
        bad_events = pts._compile_events(
            {
                "события": [{
                    "id": "bad-gate",
                    "день": 0,
                    "длительность_дней": 1,
                    "связь": ["a", "b"],
                    "gate_set": 0.90,
                }]
            },
            {"a", "b"},
            {("a", "b")},
        )
        pts._network_at(
            _two_adults({}),
            bad_ir,
            bad_events,
            0.5,
        )
    except core.ScenarioError:
        bad_gate_rejected = True

    resistor_power = semi.power(resistor, 0.20, 0.0)
    i2r = r_forward * r_forward * resistor["R_link"]

    checks = {
        "SEMI01_RESISTOR_SYMMETRIC": (
            abs(r_forward + r_reverse) < 1e-12
        ),
        "SEMI02_DIODE_DIRECTIONAL": (
            abs(d_forward) > 5.0 * abs(d_reverse)
        ),
        "SEMI03_ZERO_BIAS_ZERO_CURRENT": (
            abs(semi.current(diode, 0.0, 0.0)) < 1e-15
            and abs(semi.current(mos_on, 0.0, 0.0)) < 1e-15
        ),
        "SEMI04_MOSFET_GATE_CONTROLS_CHANNEL": (
            abs(mos_high) > 10.0 * abs(mos_low)
        ),
        "SEMI05_MOSFET_REVERSE_IS_REDUCED": (
            abs(mos_high) > 3.0 * abs(mos_high_reverse)
        ),
        "SEMI06_BREAKDOWN_OPENS_REVERSE_PATH": (
            abs(bd_over) > 5.0 * abs(bd_sub)
        ),
        "SEMI07_RESISTOR_POWER_IDENTITY": (
            abs(resistor_power - i2r) < 1e-12
        ),
        "SEMI08_LEGACY_LINK_REMAINS_RESISTIVE": (
            compiled_legacy["element_type"] == "RESISTIVE"
            and compiled_legacy["nonlinear"] is False
        ),
        "SEMI09_MOSFET_METADATA_COMPILES": (
            compiled_mos["element_type"] == "MOSFET"
            and compiled_mos["nonlinear"] is True
            and abs(compiled_mos["gate"] - 0.80) < 1e-12
        ),
        "SEMI10_GATE_EVENT_IS_TARGETED": (
            abs(changed_links[0]["gate"] - 0.15) < 1e-12
            and bad_gate_rejected
        ),
    }

    return {
        "model_version": semi.VERSION,
        "reference": {
            "resistor": {
                "forward_current": r_forward,
                "reverse_current": r_reverse,
            },
            "diode": {
                "forward_current": d_forward,
                "reverse_current": d_reverse,
            },
            "mosfet": {
                "gate_0_10_current": mos_low,
                "gate_0_90_current": mos_high,
                "gate_0_90_reverse_current": mos_high_reverse,
            },
            "breakdown_diode": {
                "reverse_below_breakdown": bd_sub,
                "reverse_above_breakdown": bd_over,
            },
            "resistor_power_vi": resistor_power,
            "resistor_power_i2r": i2r,
        },
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
