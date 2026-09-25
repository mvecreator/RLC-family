#!/usr/bin/env python3
"""RHYTHM-25H-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import personal_rhythm as rhythm
from simulator import thermal_recovery as therm


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _node(sample, pid):
    return next(row for row in sample["nodes"] if row["id"] == pid)


def _clone_with_central_rhythm(scenario, intrinsic, schedule_lock):
    out = copy.deepcopy(scenario)
    central = next(
        p for p in out["персонажи"] if p["id"] == "central"
    )
    central["rhythm"]["intrinsic_day_hours"] = intrinsic
    central["rhythm"]["schedule_lock"] = schedule_lock
    return out


def suite():
    scenario = load_json(
        ROOT / "examples" / "rhythm_25h_personal_scenario.json"
    )
    timeline = load_json(
        ROOT / "examples" / "rhythm_25h_personal_timeline.json"
    )

    locked25 = pts.simulate_person_timeline(scenario, timeline)

    free25_scenario = _clone_with_central_rhythm(
        scenario, 25.0, 0.0
    )
    free25 = pts.simulate_person_timeline(
        free25_scenario, timeline
    )

    matched24_scenario = _clone_with_central_rhythm(
        scenario, 24.0, 0.70
    )
    matched24 = pts.simulate_person_timeline(
        matched24_scenario, timeline
    )

    matched24_free_scenario = _clone_with_central_rhythm(
        scenario, 24.0, 0.0
    )
    matched24_free = pts.simulate_person_timeline(
        matched24_free_scenario, timeline
    )

    compiled = pm.compile_person_network(scenario)
    by_id = {node["id"]: node for node in compiled["nodes"]}
    central_rhythm = by_id["central"]["rhythm"]
    n1_rhythm = by_id["n1"]["rhythm"]

    day1 = rhythm.state(central_rhythm, 1.0)
    day12 = rhythm.state(central_rhythm, 12.0)
    day25 = rhythm.state(central_rhythm, 25.0)

    family = family_safety.assess(scenario, timeline)
    thermal = therm.integrate_thermal(
        scenario,
        family["trajectory"],
    )

    first_family = family["trajectory"][0]["persons"]
    first_thermal = thermal[0]["persons"]

    final_locked = _node(
        locked25["samples"][-1], "central"
    )
    final_free = _node(
        free25["samples"][-1], "central"
    )
    final_24 = _node(
        matched24["samples"][-1], "central"
    )
    final_24_free = _node(
        matched24_free["samples"][-1], "central"
    )

    checks = {
        "R25_01_CENTRAL_INTRINSIC_PERIOD_IS_25H": (
            abs(
                central_rhythm["intrinsic_day_hours"] - 25.0
            ) < 1e-12
        ),
        "R25_02_NEIGHBOR_DEFAULT_COMPARISON_IS_24H": (
            abs(n1_rhythm["intrinsic_day_hours"] - 24.0)
            < 1e-12
        ),
        "R25_03_25H_RELATIVE_PHASE_DRIFTS_ABOUT_0_96H_PER_DAY": (
            abs(
                rhythm.daily_phase_drift_hours(central_rhythm)
                + 0.96
            ) < 1e-12
            and abs(
                day1["relative_phase_hours_external"] + 0.96
            ) < 1e-12
        ),
        "R25_04_25H_PHASE_REALIGNS_AFTER_25_EXTERNAL_DAYS": (
            abs(day25["relative_phase_cycles"]) < 1e-12
            and day25["phase_mismatch"] < 1e-12
        ),
        "R25_05_25H_FREE_RUNNING_HAS_ZERO_SCHEDULE_LOAD": (
            all(
                abs(
                    _node(sample, "central")["rhythm"][
                        "schedule_mismatch_load"
                    ]
                ) < 1e-12
                for sample in free25["samples"]
            )
        ),
        "R25_06_24H_MATCHED_HAS_ZERO_PHASE_MISMATCH": (
            all(
                abs(
                    _node(sample, "central")["rhythm"][
                        "phase_mismatch"
                    ]
                ) < 1e-12
                for sample in matched24["samples"]
            )
        ),
        "R25_07_FREE_25H_AND_FREE_24H_HAVE_IDENTICAL_DYNAMICS": (
            abs(final_free["memory"] - final_24_free["memory"])
            < 1e-12
            and abs(final_free["voltage"] - final_24_free["voltage"])
            < 1e-12
        ),
        "R25_08_LOCKED_25H_ACCUMULATES_MORE_MEMORY_THAN_MATCHED_24H": (
            final_locked["memory"] > final_24["memory"]
        ),
        "R25_09_LOCKED_25H_HAS_NONZERO_MISMATCH_BY_DAY12": (
            day12["phase_mismatch"] > 0.95
            and day12["schedule_mismatch_load"] > 0.0
        ),
        "R25_10_INITIAL_ACCUMULATED_LOAD_IS_PERSON_SPECIFIC": (
            abs(first_family["central"]["accumulated_load"] - 0.20)
            < 1e-12
            and abs(first_family["n1"]["accumulated_load"] - 0.34)
            < 1e-12
            and abs(first_family["n2"]["accumulated_load"] - 0.38)
            < 1e-12
            and abs(first_family["n3"]["accumulated_load"] - 0.32)
            < 1e-12
        ),
        "R25_11_INITIAL_HEAT_AND_DEBT_ARE_PERSON_SPECIFIC": (
            abs(first_thermal["central"]["heat"] - 0.15)
            < 1e-12
            and abs(first_thermal["n2"]["heat"] - 0.28)
            < 1e-12
            and abs(
                first_thermal["n2"]["recovery_debt_heat_days"]
                - 0.12
            ) < 1e-12
        ),
        "R25_12_ELEVATED_NEIGHBOR_PRIOR_STATE_IS_INDEPENDENT_OF_RHYTHM": (
            first_family["n2"]["accumulated_load"]
            > first_family["central"]["accumulated_load"]
            and abs(
                _node(locked25["samples"][0], "n2")["rhythm"][
                    "phase_mismatch"
                ]
            ) < 1e-12
        ),
        "R25_13_RHYTHM_STATE_IS_EXPOSED_IN_PERSON_TIME2": (
            "rhythm" in _node(locked25["samples"][0], "central")
            and "daily_phase_drift_hours"
            in _node(locked25["samples"][0], "central")["rhythm"]
        ),
        "R25_14_RHYTHM_STATE_IS_EXPOSED_IN_FAMILY_COMPONENTS": (
            abs(
                first_family["central"]["intrinsic_day_hours"]
                - 25.0
            ) < 1e-12
            and "schedule_mismatch_load"
            in first_family["central"]["rhythm"]
        ),
    }

    return {
        "benchmark": "RHYTHM-25H-CAL1",
        "model_version": rhythm.VERSION,
        "reference": {
            "central_rhythm": central_rhythm,
            "daily_phase_drift_hours": (
                rhythm.daily_phase_drift_hours(central_rhythm)
            ),
            "day1_state": day1,
            "day12_state": day12,
            "day25_state": day25,
            "final_memory_locked_25h": final_locked["memory"],
            "final_memory_free_25h": final_free["memory"],
            "final_memory_matched_24h": final_24["memory"],
            "initial_accumulated_loads": {
                pid: item["accumulated_load"]
                for pid, item in first_family.items()
            },
            "initial_heat": {
                pid: item["heat"]
                for pid, item in first_thermal.items()
            },
        },
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
        "causal_boundary": (
            "A 25-hour intrinsic cycle is not modeled as harmful by itself. "
            "Additional load appears only through explicit external-schedule "
            "locking. Elevated initial states are independent hypotheses and "
            "are not automatically attributed to smoking, alcohol, or any "
            "other behavior."
        ),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
