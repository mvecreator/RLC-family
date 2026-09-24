#!/usr/bin/env python3
"""PERSON-LOAD-CAL1: synthetic calibration of individual accumulated load."""

from __future__ import annotations

import json

from simulator import person_load_model as pload


def rows_from_profile(profile, kind="adult", initial=pload.INITIAL_LOAD):
    state = float(initial)
    rows = []
    for day, load in enumerate(profile):
        component = float(load)
        rows.append({
            "day": float(day),
            "persons": {
                "p": {
                    "kind": kind,
                    "age": 35 if kind == "adult" else 12,
                    "excitation": component,
                    "memory": component,
                    "incident_link_stress": component,
                    "financial_stress": component,
                    "combined": component,
                    "accumulated_load": state,
                }
            },
        })
        state = pload.advance(state, component, 1.0)
    day = len(profile)
    component = float(profile[-1]) if profile else 0.0
    rows.append({
        "day": float(day),
        "persons": {
            "p": {
                "kind": kind,
                "age": 35 if kind == "adult" else 12,
                "excitation": component,
                "memory": component,
                "incident_link_stress": component,
                "financial_stress": component,
                "combined": component,
                "accumulated_load": state,
            }
        },
    })
    return rows


def run_case(name, profile, kind="adult"):
    rows = rows_from_profile(profile, kind=kind)
    summary = pload.classify(rows, "p")
    summary["recommendations"] = pload.recommendations(summary, kind=kind)
    return {
        "name": name,
        "profile_days": len(profile),
        "summary": summary,
    }


def suite():
    cases = {
        "calm": run_case("calm", [0.10] * 30),
        "short_strong_then_recovery": run_case(
            "short_strong_then_recovery",
            [0.10] * 3 + [0.65] * 3 + [0.10] * 24,
        ),
        "moderate_sustained": run_case(
            "moderate_sustained", [0.30] * 30
        ),
        "high_sustained": run_case(
            "high_sustained", [0.50] * 30
        ),
        "severe_sustained": run_case(
            "severe_sustained", [0.75] * 30
        ),
        "child_high_sustained": run_case(
            "child_high_sustained", [0.50] * 30, kind="child"
        ),
    }

    calm = cases["calm"]["summary"]
    short = cases["short_strong_then_recovery"]["summary"]
    moderate = cases["moderate_sustained"]["summary"]
    high = cases["high_sustained"]["summary"]
    severe = cases["severe_sustained"]["summary"]
    child = cases["child_high_sustained"]["summary"]

    child_actions = [x["action"] for x in child["recommendations"]]

    checks = {
        "PLCAL01_CALM_STABLE": (
            calm["band"] == "STABLE"
            and calm["peak_load"]["value"] < pload.RECOVERY_ATTENTION
        ),
        "PLCAL02_SHORT_STRESS_NOT_CHRONIC": (
            short["band"] == "RECOVERY_ATTENTION"
            and short["first_sustained_load_review_day"] is None
            and short["final_load"] < pload.RECOVERY_ATTENTION
        ),
        "PLCAL03_MODERATE_RECOVERY_ATTENTION_ONLY": (
            moderate["band"] == "RECOVERY_ATTENTION"
            and moderate["first_sustained_load_review_day"] is None
        ),
        "PLCAL04_HIGH_BECOMES_SUSTAINED": (
            high["band"] == "SUSTAINED_LOAD_REVIEW"
            and high["first_sustained_load_review_day"] is not None
            and high["first_high_load_review_day"] is None
        ),
        "PLCAL05_SEVERE_BECOMES_HIGH": (
            severe["band"] == "HIGH_LOAD_REVIEW"
            and severe["first_high_load_review_day"] is not None
        ),
        "PLCAL06_CHILD_USES_CAREGIVER_REVIEW": (
            "CAREGIVER_LOAD_REVIEW" in child_actions
            and "SUSTAINED_LOAD_REVIEW" not in child_actions
        ),
        "PLCAL07_THRESHOLD_ORDER": (
            pload.RECOVERY_ATTENTION
            < pload.SUSTAINED_LOAD_REVIEW
            < pload.HIGH_LOAD_REVIEW
        ),
        "PLCAL08_EQUILIBRIUM_ORDER": (
            pload.equilibrium_for_constant_load(0.10)
            < pload.equilibrium_for_constant_load(0.30)
            < pload.equilibrium_for_constant_load(0.50)
            < pload.equilibrium_for_constant_load(0.75)
        ),
    }

    return {
        "model": pload.VERSION,
        "thresholds": {
            "recovery_attention": pload.RECOVERY_ATTENTION,
            "sustained_load_review": pload.SUSTAINED_LOAD_REVIEW,
            "high_load_review": pload.HIGH_LOAD_REVIEW,
            "sustained_dwell_days": pload.SUSTAINED_DWELL_DAYS,
            "high_dwell_days": pload.HIGH_DWELL_DAYS,
        },
        "equilibrium_reference": {
            "load_0.10": pload.equilibrium_for_constant_load(0.10),
            "load_0.30": pload.equilibrium_for_constant_load(0.30),
            "load_0.50": pload.equilibrium_for_constant_load(0.50),
            "load_0.75": pload.equilibrium_for_constant_load(0.75),
        },
        "cases": cases,
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "all_pass": all(checks.values()),
    }


def main():
    print(json.dumps(suite(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
