#!/usr/bin/env python3
"""ACOUSTIC-INDUCTION-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from simulator import acoustic_induction as ai
from simulator import person_family_safety as family_safety
from simulator import person_time_solver as pts


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _central_series(result, field):
    out = []
    for sample in result["samples"]:
        row = next(x for x in sample["nodes"] if x["id"] == "central")
        out.append((float(sample["day"]), float(row[field])))
    return out


def _rmse(a, b):
    if len(a) != len(b):
        raise AssertionError("series lengths differ")
    return math.sqrt(
        sum((x[1] - y[1]) ** 2 for x, y in zip(a, b)) / len(a)
    )


def _set_all_couplings(scenario, transmission, derivative_days):
    out = copy.deepcopy(scenario)
    for coupling in out["acoustic_induction"]["couplings"]:
        coupling["transmission"] = float(transmission)
        coupling["derivative_coupling_days"] = float(derivative_days)
    return out


def _single_step_timeline():
    return {
        "simulation": {
            "days": 1.0,
            "dt_days": 0.002,
            "sample_every_days": 0.01,
        },
        "events": [],
        "acoustic_sources": [
            {
                "id": "synthetic-step",
                "source_zone": "household2_family3",
                "waveform": "step",
                "at_day": 0.25,
                "duration_days": 0.0,
                "amplitude": 0.40,
                "edge_days": 0.02,
            }
        ],
    }


def suite():
    scenario = load_json(
        ROOT / "examples" / "acoustic_induction1_households_scenario.json"
    )
    timeline = load_json(
        ROOT / "examples" / "acoustic_induction1_households_timeline.json"
    )
    node_ids = {
        str(p["id"]) for p in scenario["персонажи"]
    }

    # Signal-level probes.
    probe_scenario = {
        "acoustic_induction": {
            "couplings": [
                {
                    "id": "wall",
                    "source_zone": "zone",
                    "target_person": "central",
                    "transmission": 0.40,
                    "derivative_coupling_days": 0.003,
                }
            ]
        }
    }

    constant_timeline = {
        "acoustic_sources": [
            {
                "id": "steady",
                "source_zone": "zone",
                "waveform": "constant",
                "amplitude": 0.50,
                "at_day": 0.0,
                "duration_days": 1.0,
                "edge_days": 0.01,
            }
        ]
    }
    constant_ir = ai.compile_acoustic(
        probe_scenario, constant_timeline, {"central"}
    )
    constant_drive = ai.drive_at(
        constant_ir, 0.50, {"central"}
    )

    step_timeline = {
        "acoustic_sources": [
            {
                "id": "step",
                "source_zone": "zone",
                "waveform": "step",
                "amplitude": 0.50,
                "at_day": 0.20,
                "duration_days": 0.0,
                "edge_days": 0.02,
            }
        ]
    }
    step_ir = ai.compile_acoustic(
        probe_scenario, step_timeline, {"central"}
    )
    step_edge = ai.drive_at(step_ir, 0.21, {"central"})
    step_steady = ai.drive_at(step_ir, 0.30, {"central"})

    pulse_timeline = {
        "acoustic_sources": [
            {
                "id": "pulse",
                "source_zone": "zone",
                "waveform": "pulse",
                "amplitude": 0.50,
                "at_day": 0.20,
                "duration_days": 0.20,
                "edge_days": 0.02,
            }
        ]
    }
    pulse_ir = ai.compile_acoustic(
        probe_scenario, pulse_timeline, {"central"}
    )
    pulse_rise = ai.drive_at(pulse_ir, 0.21, {"central"})
    pulse_fall = ai.drive_at(pulse_ir, 0.39, {"central"})

    # Signed derivative integral over the complete smooth pulse.
    dt_int = 0.0002
    signed_inductive_integral = 0.0
    t = 0.15
    while t < 0.45 - 1e-15:
        signed_inductive_integral += (
            ai.drive_at(pulse_ir, t, {"central"})["inductive"]["central"]
            * dt_int
        )
        t += dt_int

    # Insulation / M scaling at the exact same source instant.
    low_t = copy.deepcopy(probe_scenario)
    high_t = copy.deepcopy(probe_scenario)
    low_t["acoustic_induction"]["couplings"][0]["transmission"] = 0.20
    high_t["acoustic_induction"]["couplings"][0]["transmission"] = 0.60
    low_t_ir = ai.compile_acoustic(low_t, constant_timeline, {"central"})
    high_t_ir = ai.compile_acoustic(high_t, constant_timeline, {"central"})
    low_t_drive = ai.drive_at(low_t_ir, 0.50, {"central"})
    high_t_drive = ai.drive_at(high_t_ir, 0.50, {"central"})

    low_m = copy.deepcopy(probe_scenario)
    high_m = copy.deepcopy(probe_scenario)
    low_m["acoustic_induction"]["couplings"][0][
        "derivative_coupling_days"
    ] = 0.001
    high_m["acoustic_induction"]["couplings"][0][
        "derivative_coupling_days"
    ] = 0.006
    low_m_ir = ai.compile_acoustic(low_m, step_timeline, {"central"})
    high_m_ir = ai.compile_acoustic(high_m, step_timeline, {"central"})
    low_m_drive = ai.drive_at(low_m_ir, 0.21, {"central"})
    high_m_drive = ai.drive_at(high_m_ir, 0.21, {"central"})

    # H0 / HT / HM / HTM through full PERSON-TIME2.
    step_full = _single_step_timeline()
    base_coupling = next(
        c for c in scenario["acoustic_induction"]["couplings"]
        if c["source_zone"] == "household2_family3"
    )
    t_ref = float(base_coupling["transmission"])
    m_ref = float(base_coupling["derivative_coupling_days"])

    h0_scenario = _set_all_couplings(scenario, 0.0, 0.0)
    ht_scenario = _set_all_couplings(scenario, t_ref, 0.0)
    hm_scenario = _set_all_couplings(scenario, 0.0, m_ref)
    htm_scenario = _set_all_couplings(scenario, t_ref, m_ref)

    h0 = pts.simulate_person_timeline(h0_scenario, step_full)
    ht = pts.simulate_person_timeline(ht_scenario, step_full)
    hm = pts.simulate_person_timeline(hm_scenario, step_full)
    htm = pts.simulate_person_timeline(htm_scenario, step_full)

    truth = _central_series(htm, "voltage")
    hypothesis_rmse = {
        "H0": _rmse(truth, _central_series(h0, "voltage")),
        "HT": _rmse(truth, _central_series(ht, "voltage")),
        "HM": _rmse(truth, _central_series(hm, "voltage")),
        "HTM": _rmse(truth, _central_series(htm, "voltage")),
    }

    # Household accumulation under repeated observed acoustic sources.
    actual_family = family_safety.assess(scenario, timeline)
    zero_family = family_safety.assess(
        _set_all_couplings(scenario, 0.0, 0.0),
        timeline,
    )
    actual_central = [
        row["persons"]["central"]["accumulated_load"]
        for row in actual_family["trajectory"]
    ]
    zero_central = [
        row["persons"]["central"]["accumulated_load"]
        for row in zero_family["trajectory"]
    ]

    # Direct-transmission monotonicity in the full household scenario.
    low_wall_scenario = copy.deepcopy(scenario)
    high_wall_scenario = copy.deepcopy(scenario)
    for coupling in low_wall_scenario["acoustic_induction"]["couplings"]:
        coupling["transmission"] *= 0.50
    for coupling in high_wall_scenario["acoustic_induction"]["couplings"]:
        coupling["transmission"] = min(
            1.0, coupling["transmission"] * 1.50
        )
    low_wall_family = family_safety.assess(low_wall_scenario, timeline)
    high_wall_family = family_safety.assess(high_wall_scenario, timeline)
    low_wall_final = low_wall_family["trajectory"][-1][
        "persons"
    ]["central"]["accumulated_load"]
    high_wall_final = high_wall_family["trajectory"][-1][
        "persons"
    ]["central"]["accumulated_load"]

    # Legacy parity: no acoustic block vs explicit empty acoustic layer.
    legacy_scenario = copy.deepcopy(scenario)
    legacy_scenario.pop("acoustic_induction", None)
    legacy_timeline = copy.deepcopy(timeline)
    legacy_timeline.pop("acoustic_sources", None)

    empty_scenario = copy.deepcopy(legacy_scenario)
    empty_scenario["acoustic_induction"] = {"couplings": []}
    empty_timeline = copy.deepcopy(legacy_timeline)
    empty_timeline["acoustic_sources"] = []

    legacy = pts.simulate_person_timeline(
        legacy_scenario, legacy_timeline
    )
    empty = pts.simulate_person_timeline(
        empty_scenario, empty_timeline
    )
    legacy_v = _central_series(legacy, "voltage")
    empty_v = _central_series(empty, "voltage")
    legacy_m = _central_series(legacy, "memory")
    empty_m = _central_series(empty, "memory")

    sample_central = next(
        x for x in htm["samples"][30]["nodes"]
        if x["id"] == "central"
    )

    checks = {
        "AI01_CONSTANT_SOURCE_HAS_DIRECT_BUT_NO_INDUCTIVE_TERM": (
            constant_drive["direct"]["central"] > 0.0
            and abs(constant_drive["inductive"]["central"]) < 1e-15
        ),
        "AI02_STEP_EDGE_HAS_NONZERO_INDUCTIVE_TERM": (
            abs(step_edge["inductive"]["central"]) > 0.0
        ),
        "AI03_STEP_STEADY_STATE_HAS_ZERO_INDUCTIVE_TERM": (
            abs(step_steady["inductive"]["central"]) < 1e-15
            and step_steady["direct"]["central"] > 0.0
        ),
        "AI04_PULSE_RISE_AND_FALL_HAVE_OPPOSITE_INDUCTIVE_SIGN": (
            pulse_rise["inductive"]["central"] > 0.0
            and pulse_fall["inductive"]["central"] < 0.0
        ),
        "AI05_COMPLETE_PULSE_DERIVATIVE_HAS_NEAR_ZERO_SIGNED_AREA": (
            abs(signed_inductive_integral) < 5e-5
        ),
        "AI06_POORER_INSULATION_INCREASES_DIRECT_DRIVE": (
            high_t_drive["direct"]["central"]
            > low_t_drive["direct"]["central"]
        ),
        "AI07_LARGER_DERIVATIVE_COUPLING_INCREASES_EDGE_TRANSIENT": (
            abs(high_m_drive["inductive"]["central"])
            > abs(low_m_drive["inductive"]["central"])
        ),
        "AI08_H0_HAS_ZERO_ACOUSTIC_DRIVE": (
            all(
                abs(
                    next(
                        x for x in sample["nodes"]
                        if x["id"] == "central"
                    )["acoustic_total_drive"]
                ) < 1e-15
                for sample in h0["samples"]
            )
        ),
        "AI09_HTM_SYNTHETIC_TRUTH_FITS_EXACTLY": (
            hypothesis_rmse["HTM"] < 1e-15
        ),
        "AI10_HT_MISSES_A_NONZERO_TRANSIENT_COMPONENT": (
            hypothesis_rmse["HT"] > 1e-8
        ),
        "AI11_HM_MISSES_A_NONZERO_STEADY_COMPONENT": (
            hypothesis_rmse["HM"] > 1e-8
        ),
        "AI12_REPEATED_ACOUSTIC_SOURCES_RAISE_CENTRAL_ACCUMULATED_LOAD": (
            max(actual_central) > max(zero_central)
            and actual_central[-1] > zero_central[-1]
        ),
        "AI13_POORER_WALL_TRANSMISSION_RAISES_FINAL_CENTRAL_LOAD": (
            high_wall_final > low_wall_final
        ),
        "AI14_PERSON_TIME_EXPOSES_ACOUSTIC_PROVENANCE": (
            "acoustic_direct_drive" in sample_central
            and "acoustic_inductive_drive" in sample_central
            and "acoustic_total_drive" in sample_central
            and "acoustic_effects" in htm["samples"][30]
        ),
        "AI15_25H_RHYTHM_AND_ACOUSTIC_LAYER_COEXIST": (
            abs(sample_central["rhythm"]["intrinsic_day_hours"] - 25.0)
            < 1e-12
        ),
        "AI16_LEGACY_NO_ACOUSTIC_EQUALS_EXPLICIT_EMPTY_LAYER": (
            _rmse(legacy_v, empty_v) < 1e-15
            and _rmse(legacy_m, empty_m) < 1e-15
        ),
    }

    return {
        "benchmark": "ACOUSTIC-INDUCTION-CAL1",
        "model_version": ai.VERSION,
        "reference": {
            "constant_drive": constant_drive,
            "step_edge_drive": step_edge,
            "step_steady_drive": step_steady,
            "pulse_rise_drive": pulse_rise,
            "pulse_fall_drive": pulse_fall,
            "signed_inductive_pulse_area": signed_inductive_integral,
            "hypothesis_rmse": hypothesis_rmse,
            "central_peak_load_with_acoustics": max(actual_central),
            "central_peak_load_without_acoustics": max(zero_central),
            "central_final_load_with_acoustics": actual_central[-1],
            "central_final_load_without_acoustics": zero_central[-1],
            "low_wall_final_load": low_wall_final,
            "high_wall_final_load": high_wall_final,
        },
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
        "interpretation_boundary": (
            "ACOUSTIC-INDUCTION1 models transmission and transient response "
            "to observable sound. It does not infer that a sound was directed "
            "at the listener, intentional, hostile, coordinated, or caused by "
            "a particular psychological state. Synthetic HTM fit superiority "
            "only verifies identifiability mechanics; real predictive value "
            "requires prospective observed acoustic data."
        ),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
