#!/usr/bin/env python3
"""RECOVERY-SCENARIO1: compare hypothetical recovery interventions.

The bundled profiles are mechanism bundles, not empirically calibrated claims
about vacations, mountains, therapy, or medical recovery.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import thermal_recovery as therm


ROOT = Path(__file__).resolve().parents[1]


PROFILES = {
    "continue_7d": {
        "name": "continue_7d",
        "days": 7.0,
        "person_load_multiplier": 1.0,
        "person_cooling_boost": 0.0,
        "link_power_multiplier": 1.0,
        "link_cooling_boost": 0.0,
    },
    "three_day_break_then_return": {
        "name": "three_day_break_then_return",
        "segments": [
            {
                "days": 3.0,
                "person_load_multiplier": 0.50,
                "person_cooling_boost": 0.20,
                "link_power_multiplier": 0.70,
                "link_cooling_boost": 0.15,
            },
            {
                "days": 4.0,
                "person_load_multiplier": 1.0,
                "person_cooling_boost": 0.0,
                "link_power_multiplier": 1.0,
                "link_cooling_boost": 0.0,
            },
        ],
    },
    "work_disconnect_7d": {
        "name": "work_disconnect_7d",
        "days": 7.0,
        "person_load_multiplier": 0.25,
        "person_cooling_boost": 0.35,
        "link_power_multiplier": 0.75,
        "link_cooling_boost": 0.20,
    },
    "deep_recovery_7d": {
        "name": "deep_recovery_7d",
        "days": 7.0,
        "person_load_multiplier": 0.15,
        "person_cooling_boost": 0.55,
        "link_power_multiplier": 0.60,
        "link_cooling_boost": 0.30,
    },
    "mountain_style_7d": {
        "name": "mountain_style_7d",
        "days": 7.0,
        "person_load_multiplier": 0.15,
        "person_cooling_boost": 0.55,
        "link_power_multiplier": 0.55,
        "link_cooling_boost": 0.35,
        "interpretation": (
            "Mechanism bundle: work disconnect, fewer interruptions, more "
            "recovery opportunity and lower heavy-interaction load. It does "
            "not assign a special causal coefficient to mountains or altitude."
        ),
    },
    "cool_then_shared_7d": {
        "name": "cool_then_shared_7d",
        "segments": [
            {
                "days": 2.0,
                "person_load_multiplier": 0.15,
                "person_cooling_boost": 0.55,
                "link_power_multiplier": 0.25,
                "link_cooling_boost": 0.45,
            },
            {
                "days": 5.0,
                "person_load_multiplier": 0.25,
                "person_cooling_boost": 0.45,
                "link_power_multiplier": 0.65,
                "link_cooling_boost": 0.25,
            },
        ],
        "interpretation": (
            "First reduce heavy interaction and cool separately, then return "
            "to moderate shared interaction during continued low-demand recovery."
        ),
    },
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cut_rows(rows, cutoff_day):
    out = [
        row for row in rows
        if float(row["day"]) <= float(cutoff_day) + 1e-12
    ]
    if not out:
        raise ValueError("cutoff produces empty history")
    return out


def _profile_summary(result):
    final = result["final"]
    person_heat = {
        pid: item["heat"]
        for pid, item in final["persons"].items()
    }
    person_debt = {
        pid: item["recovery_debt_heat_days"]
        for pid, item in final["persons"].items()
    }
    link_heat = {
        key: item["heat"]
        for key, item in final["links"].items()
    }
    link_damage = {
        key: item["damage"]
        for key, item in final["links"].items()
    }
    link_debt = {
        key: item["recovery_debt_heat_days"]
        for key, item in final["links"].items()
    }
    return {
        "projected_days": result["projected_days"],
        "max_person_heat": max(person_heat.values()) if person_heat else 0.0,
        "max_person_recovery_debt": max(person_debt.values()) if person_debt else 0.0,
        "max_link_heat": max(link_heat.values()) if link_heat else 0.0,
        "max_link_damage": max(link_damage.values()) if link_damage else 0.0,
        "max_link_recovery_debt": max(link_debt.values()) if link_debt else 0.0,
        "persons": final["persons"],
        "links": final["links"],
    }


def compare_profiles(
    scenario,
    timeline,
    cutoff_day,
    profile_names=None,
    lookback_days=3.0,
):
    full = family_safety.assess(scenario, timeline)
    family_rows = full["trajectory"]
    thermal_rows = therm.integrate_thermal(scenario, family_rows)

    cut_family = _cut_rows(family_rows, cutoff_day)
    cut_thermal = _cut_rows(thermal_rows, cutoff_day)
    actual_cutoff = float(cut_thermal[-1]["day"])

    names = profile_names or list(PROFILES)
    results = {}
    for name in names:
        if name not in PROFILES:
            raise ValueError(f"unknown recovery profile: {name}")
        projected = therm.project_recovery(
            scenario,
            cut_thermal,
            cut_family,
            actual_cutoff,
            PROFILES[name],
            lookback_days=lookback_days,
        )
        results[name] = {
            "profile": PROFILES[name],
            "summary": _profile_summary(projected),
        }

    def best(metric):
        if not results:
            return None
        return min(
            results,
            key=lambda name: results[name]["summary"][metric],
        )

    return {
        "model_version": therm.VERSION,
        "scenario_name": full["scenario_name"],
        "requested_cutoff_day": float(cutoff_day),
        "actual_cutoff_day": actual_cutoff,
        "thermal_at_cutoff": cut_thermal[-1],
        "profiles": results,
        "lowest_max_person_heat": best("max_person_heat"),
        "lowest_max_person_recovery_debt": best(
            "max_person_recovery_debt"
        ),
        "lowest_max_link_heat": best("max_link_heat"),
        "lowest_max_link_damage": best("max_link_damage"),
        "boundary": (
            "The planner compares declared hypothetical mechanism bundles. "
            "It does not prove that a holiday, mountain trip, or any other "
            "real-world intervention will produce the assumed multipliers."
        ),
    }


def main():
    p = argparse.ArgumentParser(
        description="Compare RECOVERY-SCENARIO1 profiles"
    )
    p.add_argument("scenario")
    p.add_argument("timeline")
    p.add_argument("--cutoff-day", type=float, required=True)
    p.add_argument("--profiles", nargs="*")
    args = p.parse_args()

    result = compare_profiles(
        load_json(args.scenario),
        load_json(args.timeline),
        args.cutoff_day,
        profile_names=args.profiles,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
