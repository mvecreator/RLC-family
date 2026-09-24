#!/usr/bin/env python3
"""THERM-CAL1: calibration gates for PERSON/LINK thermal memory."""

from __future__ import annotations

import json

from simulator import thermal_recovery as therm


def run_steps_person(
    heat,
    debt,
    load,
    cooling,
    days,
    dt=0.01,
):
    t = 0.0
    while t < days - 1e-12:
        step = min(dt, days - t)
        heat = therm.advance_heat(
            heat,
            load,
            cooling,
            step,
            therm.PERSON_HEAT_GAIN,
            therm.PERSON_COOL_GAIN,
        )
        debt = therm.advance_debt(
            debt,
            heat,
            therm.PERSON_COMFORT_HEAT,
            cooling,
            step,
        )
        t += step
    return heat, debt


def run_steps_link(
    heat,
    damage,
    debt,
    power,
    cooling,
    days,
    dt=0.01,
):
    t = 0.0
    while t < days - 1e-12:
        step = min(dt, days - t)
        heat = therm.advance_heat(
            heat,
            power,
            cooling,
            step,
            therm.LINK_HEAT_GAIN,
            therm.LINK_COOL_GAIN,
        )
        damage = therm.advance_damage(
            damage,
            heat,
            cooling,
            step,
        )
        debt = therm.advance_debt(
            debt,
            heat,
            therm.LINK_COMFORT_HEAT,
            cooling,
            step,
        )
        t += step
    return heat, damage, debt


def suite():
    p_low = run_steps_person(0.15, 0.0, 0.10, 0.50, 14)
    p_high = run_steps_person(0.15, 0.0, 0.50, 0.50, 14)

    l_low = run_steps_link(0.15, 0.0, 0.0, 0.10, 0.50, 14)
    l_high = run_steps_link(0.15, 0.0, 0.0, 0.60, 0.50, 14)

    person_continue = run_steps_person(
        0.65, 1.50, 0.50, 0.50, 7
    )
    person_deep = run_steps_person(
        0.65, 1.50, 0.50 * 0.15, 1.0, 7
    )

    link_continue = run_steps_link(
        0.70, 0.25, 2.0, 0.60, 0.40, 7
    )
    link_deep = run_steps_link(
        0.70, 0.25, 2.0, 0.60 * 0.60, 0.70, 7
    )

    current = 0.20
    low_r_power = current * current * 0.30
    high_r_power = current * current * 1.50
    double_current_power = (2 * current) ** 2 * 0.30

    checks = {
        "TH01_HIGH_R_HIGHER_POWER_AT_SAME_I": (
            high_r_power > low_r_power
        ),
        "TH02_DOUBLE_CURRENT_QUADRUPLES_POWER": (
            abs(double_current_power - 4.0 * low_r_power) < 1e-12
        ),
        "TH03_LOW_PERSON_LOAD_STAYS_COMFORTABLE": (
            p_low[0] < therm.PERSON_COMFORT_HEAT
            and p_low[1] == 0.0
        ),
        "TH04_HIGH_PERSON_LOAD_CREATES_HEAT_AND_DEBT": (
            p_high[0] > therm.PERSON_OVERHEAT
            if hasattr(therm, "PERSON_OVERHEAT")
            else p_high[0] > 0.55
        ) and p_high[1] > 0.0,
        "TH05_LOW_LINK_POWER_DOES_NOT_DAMAGE": (
            l_low[0] < therm.LINK_OVERHEAT
            and l_low[1] == 0.0
        ),
        "TH06_SUSTAINED_LINK_POWER_OVERHEATS_AND_DAMAGES": (
            l_high[0] > therm.LINK_OVERHEAT
            and l_high[1] > 0.0
            and l_high[2] > 0.0
        ),
        "TH07_DEEP_RECOVERY_COOLS_PERSON": (
            person_deep[0] < person_continue[0]
            and person_deep[1] < person_continue[1]
        ),
        "TH08_DEEP_RECOVERY_COOLS_LINK": (
            link_deep[0] < link_continue[0]
            and link_deep[1] < link_continue[1]
            and link_deep[2] < link_continue[2]
        ),
        "TH09_HEAT_BANDS_ORDER": (
            therm.person_heat_band(0.20) == "COMFORT"
            and therm.person_heat_band(0.45) == "WARM"
            and therm.person_heat_band(0.60) == "OVERHEATED"
            and therm.person_heat_band(0.75) == "HIGH_HEAT"
        ),
        "TH10_DAMAGE_CAN_TRIGGER_RUPTURE_REVIEW": (
            therm.link_heat_band(0.40, 0.60)
            == "RUPTURE_RISK_REVIEW"
        ),
    }

    return {
        "model_version": therm.VERSION,
        "reference": {
            "person_low_14d": {
                "heat": p_low[0],
                "debt": p_low[1],
            },
            "person_high_14d": {
                "heat": p_high[0],
                "debt": p_high[1],
            },
            "link_low_14d": {
                "heat": l_low[0],
                "damage": l_low[1],
                "debt": l_low[2],
            },
            "link_high_14d": {
                "heat": l_high[0],
                "damage": l_high[1],
                "debt": l_high[2],
            },
            "person_continue_7d": {
                "heat": person_continue[0],
                "debt": person_continue[1],
            },
            "person_deep_recovery_7d": {
                "heat": person_deep[0],
                "debt": person_deep[1],
            },
            "link_continue_7d": {
                "heat": link_continue[0],
                "damage": link_continue[1],
                "debt": link_continue[2],
            },
            "link_deep_recovery_7d": {
                "heat": link_deep[0],
                "damage": link_deep[1],
                "debt": link_deep[2],
            },
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
