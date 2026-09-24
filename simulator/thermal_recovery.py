#!/usr/bin/env python3
"""PERSON-THERM1 / LINK-THERM1 / RECOVERY-DEBT1.

Post-processes PERSON-FAMILY-SAFETY1 trajectories into bounded thermal-memory
states. Link heating uses the electrical dissipation proxy I^2 R.

All thresholds and recovery profiles are engineering calibration hypotheses,
not medical or relationship-outcome probabilities.
"""

from __future__ import annotations

import math

VERSION = "RLC-FAMILY-THERM1-0.1"

PERSON_HEAT_GAIN = 0.35
PERSON_COOL_GAIN = 0.25
PERSON_COMFORT_HEAT = 0.35
PERSON_OVERHEAT = 0.55
PERSON_HIGH_HEAT = 0.70

LINK_POWER_REF = 0.020
LINK_HEAT_GAIN = 0.50
LINK_COOL_GAIN = 0.25
LINK_COMFORT_HEAT = 0.35
LINK_OVERHEAT = 0.55

LINK_DAMAGE_GAIN = 0.25
LINK_DAMAGE_REPAIR = 0.05

DEBT_REPAY_GAIN = 0.15

INITIAL_PERSON_HEAT = 0.15
INITIAL_LINK_HEAT = 0.15
INITIAL_LINK_DAMAGE = 0.0
INITIAL_RECOVERY_DEBT = 0.0


def clip01(value):
    return max(0.0, min(1.0, float(value)))


def person_recovery_inertia(scenario, pid):
    for person in scenario.get("персонажи", []):
        if str(person.get("id")) != str(pid):
            continue
        role = person.get("role") or {}
        return clip01(
            person.get(
                "recovery_inertia",
                role.get("recovery_inertia", 0.5),
            )
        )
    return 0.5


def person_cooling_capacity(scenario, pid):
    return clip01(1.0 - person_recovery_inertia(scenario, pid))


def link_power_w_proxy(link_row):
    current = abs(float(link_row.get("current_abs_raw", 0.0)))
    resistance = max(0.0, float(link_row.get("R_link", 0.0)))
    return current * current * resistance


def normalized_link_power(link_row):
    return clip01(link_power_w_proxy(link_row) / LINK_POWER_REF)


def link_cooling_capacity(link_row):
    q = clip01(link_row.get("communication_quality", 0.5))
    interaction = clip01(link_row.get("interaction", 0.0))
    # A good channel and lower interaction intensity both make cooling easier.
    return clip01(0.60 * q + 0.40 * (1.0 - interaction))


def advance_heat(
    heat,
    power,
    cooling,
    dt,
    heat_gain,
    cool_gain,
):
    heat = clip01(heat)
    power = clip01(power)
    cooling = clip01(cooling)
    dt = max(0.0, float(dt))
    return clip01(
        heat
        + dt * heat_gain * power * (1.0 - heat)
        - dt * cool_gain * cooling * heat
    )


def advance_damage(damage, heat, cooling, dt):
    damage = clip01(damage)
    heat = clip01(heat)
    cooling = clip01(cooling)
    dt = max(0.0, float(dt))
    excess = max(0.0, heat - LINK_OVERHEAT)
    return clip01(
        damage
        + dt * LINK_DAMAGE_GAIN * excess * (1.0 - damage)
        - dt * LINK_DAMAGE_REPAIR * cooling * damage
    )


def advance_debt(debt, heat, comfort_heat, cooling, dt):
    debt = max(0.0, float(debt))
    heat = clip01(heat)
    cooling = clip01(cooling)
    dt = max(0.0, float(dt))
    accumulation = max(0.0, heat - comfort_heat)
    return max(
        0.0,
        debt
        + dt * accumulation
        - dt * DEBT_REPAY_GAIN * cooling * debt,
    )


def person_heat_band(heat):
    heat = clip01(heat)
    if heat >= PERSON_HIGH_HEAT:
        return "HIGH_HEAT"
    if heat >= PERSON_OVERHEAT:
        return "OVERHEATED"
    if heat >= 0.35:
        return "WARM"
    return "COMFORT"


def link_heat_band(heat, damage):
    heat = clip01(heat)
    damage = clip01(damage)
    if damage >= 0.50:
        return "RUPTURE_RISK_REVIEW"
    if damage >= 0.20:
        return "DAMAGE_ACCUMULATION"
    if heat >= LINK_OVERHEAT:
        return "OVERHEATED"
    if heat >= LINK_COMFORT_HEAT:
        return "WARM"
    return "COMFORT"


def integrate_thermal(scenario, family_rows):
    if not family_rows:
        raise ValueError("family_rows must not be empty")

    person_ids = sorted(family_rows[0]["persons"])
    link_keys = sorted(family_rows[0]["links"])

    person_heat = {
        pid: INITIAL_PERSON_HEAT for pid in person_ids
    }
    person_debt = {
        pid: INITIAL_RECOVERY_DEBT for pid in person_ids
    }
    link_heat = {
        key: INITIAL_LINK_HEAT for key in link_keys
    }
    link_damage = {
        key: INITIAL_LINK_DAMAGE for key in link_keys
    }
    link_debt = {
        key: INITIAL_RECOVERY_DEBT for key in link_keys
    }

    out = []
    prev_day = float(family_rows[0]["day"])

    for index, row in enumerate(family_rows):
        day = float(row["day"])
        dt = max(0.0, day - prev_day) if index else 0.0

        persons = {}
        for pid in person_ids:
            power = clip01(row["persons"][pid]["combined"])
            cooling = person_cooling_capacity(scenario, pid)
            if dt > 0:
                person_heat[pid] = advance_heat(
                    person_heat[pid],
                    power,
                    cooling,
                    dt,
                    PERSON_HEAT_GAIN,
                    PERSON_COOL_GAIN,
                )
                person_debt[pid] = advance_debt(
                    person_debt[pid],
                    person_heat[pid],
                    PERSON_COMFORT_HEAT,
                    cooling,
                    dt,
                )
            persons[pid] = {
                "load_power_proxy": power,
                "cooling_capacity": cooling,
                "heat": person_heat[pid],
                "recovery_debt_heat_days": person_debt[pid],
                "band": person_heat_band(person_heat[pid]),
            }

        links = {}
        for key in link_keys:
            link = row["links"][key]
            power_raw = link_power_w_proxy(link)
            power = normalized_link_power(link)
            cooling = link_cooling_capacity(link)
            if dt > 0:
                link_heat[key] = advance_heat(
                    link_heat[key],
                    power,
                    cooling,
                    dt,
                    LINK_HEAT_GAIN,
                    LINK_COOL_GAIN,
                )
                link_damage[key] = advance_damage(
                    link_damage[key],
                    link_heat[key],
                    cooling,
                    dt,
                )
                link_debt[key] = advance_debt(
                    link_debt[key],
                    link_heat[key],
                    LINK_COMFORT_HEAT,
                    cooling,
                    dt,
                )
            links[key] = {
                "dissipation_power_proxy": power_raw,
                "normalized_dissipation_power": power,
                "cooling_capacity": cooling,
                "heat": link_heat[key],
                "damage": link_damage[key],
                "recovery_debt_heat_days": link_debt[key],
                "band": link_heat_band(
                    link_heat[key], link_damage[key]
                ),
            }

        out.append({
            "day": day,
            "persons": persons,
            "links": links,
        })
        prev_day = day

    return out


def summarize_thermal(rows):
    if not rows:
        raise ValueError("rows must not be empty")
    person_ids = sorted(rows[0]["persons"])
    link_keys = sorted(rows[0]["links"])

    persons = {}
    for pid in person_ids:
        peak = max(
            ((row["day"], row["persons"][pid]["heat"]) for row in rows),
            key=lambda x: x[1],
        )
        persons[pid] = {
            "peak_heat": {"day": peak[0], "value": peak[1]},
            "final_heat": rows[-1]["persons"][pid]["heat"],
            "final_recovery_debt_heat_days": rows[-1]["persons"][pid][
                "recovery_debt_heat_days"
            ],
            "final_band": rows[-1]["persons"][pid]["band"],
        }

    links = {}
    for key in link_keys:
        peak_heat = max(
            ((row["day"], row["links"][key]["heat"]) for row in rows),
            key=lambda x: x[1],
        )
        peak_power = max(
            (
                (
                    row["day"],
                    row["links"][key]["dissipation_power_proxy"],
                )
                for row in rows
            ),
            key=lambda x: x[1],
        )
        peak_damage = max(
            ((row["day"], row["links"][key]["damage"]) for row in rows),
            key=lambda x: x[1],
        )
        links[key] = {
            "peak_dissipation_power_proxy": {
                "day": peak_power[0],
                "value": peak_power[1],
            },
            "peak_heat": {
                "day": peak_heat[0],
                "value": peak_heat[1],
            },
            "peak_damage": {
                "day": peak_damage[0],
                "value": peak_damage[1],
            },
            "final_heat": rows[-1]["links"][key]["heat"],
            "final_damage": rows[-1]["links"][key]["damage"],
            "final_recovery_debt_heat_days": rows[-1]["links"][key][
                "recovery_debt_heat_days"
            ],
            "final_band": rows[-1]["links"][key]["band"],
        }

    return {
        "persons": persons,
        "links": links,
    }


def recent_means(family_rows, cutoff_day, lookback_days=3.0):
    cutoff_day = float(cutoff_day)
    start = cutoff_day - float(lookback_days)
    rows = [
        row for row in family_rows
        if start - 1e-12 <= float(row["day"]) <= cutoff_day + 1e-12
    ]
    if not rows:
        raise ValueError("no rows in recent mean window")

    person_ids = sorted(rows[0]["persons"])
    link_keys = sorted(rows[0]["links"])

    persons = {
        pid: sum(
            clip01(row["persons"][pid]["combined"]) for row in rows
        ) / len(rows)
        for pid in person_ids
    }
    links = {
        key: {
            "power": sum(
                normalized_link_power(row["links"][key])
                for row in rows
            ) / len(rows),
            "cooling": sum(
                link_cooling_capacity(row["links"][key])
                for row in rows
            ) / len(rows),
        }
        for key in link_keys
    }
    return {"persons": persons, "links": links}


def _profile_value(profile, key, default):
    return float(profile.get(key, default))


def _segment_sequence(profile):
    if "segments" in profile:
        return profile["segments"]
    return [{
        "days": profile["days"],
        "person_load_multiplier": profile.get(
            "person_load_multiplier", 1.0
        ),
        "person_cooling_boost": profile.get(
            "person_cooling_boost", 0.0
        ),
        "link_power_multiplier": profile.get(
            "link_power_multiplier", 1.0
        ),
        "link_cooling_boost": profile.get(
            "link_cooling_boost", 0.0
        ),
    }]


def project_recovery(
    scenario,
    thermal_rows,
    family_rows,
    cutoff_day,
    profile,
    lookback_days=3.0,
    dt=0.05,
):
    eligible = [
        row for row in thermal_rows
        if float(row["day"]) <= float(cutoff_day) + 1e-12
    ]
    if not eligible:
        raise ValueError("cutoff before thermal history")
    initial = eligible[-1]
    means = recent_means(
        family_rows,
        cutoff_day,
        lookback_days=lookback_days,
    )

    person_heat = {
        pid: float(item["heat"])
        for pid, item in initial["persons"].items()
    }
    person_debt = {
        pid: float(item["recovery_debt_heat_days"])
        for pid, item in initial["persons"].items()
    }
    link_heat = {
        key: float(item["heat"])
        for key, item in initial["links"].items()
    }
    link_damage = {
        key: float(item["damage"])
        for key, item in initial["links"].items()
    }
    link_debt = {
        key: float(item["recovery_debt_heat_days"])
        for key, item in initial["links"].items()
    }

    elapsed = 0.0
    timeline = []

    for segment in _segment_sequence(profile):
        days = max(0.0, float(segment["days"]))
        person_mult = max(
            0.0,
            _profile_value(segment, "person_load_multiplier", 1.0),
        )
        person_boost = _profile_value(
            segment, "person_cooling_boost", 0.0
        )
        link_mult = max(
            0.0,
            _profile_value(segment, "link_power_multiplier", 1.0),
        )
        link_boost = _profile_value(
            segment, "link_cooling_boost", 0.0
        )

        segment_elapsed = 0.0
        while segment_elapsed < days - 1e-12:
            step = min(dt, days - segment_elapsed)

            for pid in person_heat:
                power = clip01(means["persons"][pid] * person_mult)
                cooling = clip01(
                    person_cooling_capacity(scenario, pid)
                    + person_boost
                )
                person_heat[pid] = advance_heat(
                    person_heat[pid],
                    power,
                    cooling,
                    step,
                    PERSON_HEAT_GAIN,
                    PERSON_COOL_GAIN,
                )
                person_debt[pid] = advance_debt(
                    person_debt[pid],
                    person_heat[pid],
                    PERSON_COMFORT_HEAT,
                    cooling,
                    step,
                )

            for key in link_heat:
                power = clip01(means["links"][key]["power"] * link_mult)
                cooling = clip01(
                    means["links"][key]["cooling"] + link_boost
                )
                link_heat[key] = advance_heat(
                    link_heat[key],
                    power,
                    cooling,
                    step,
                    LINK_HEAT_GAIN,
                    LINK_COOL_GAIN,
                )
                link_damage[key] = advance_damage(
                    link_damage[key],
                    link_heat[key],
                    cooling,
                    step,
                )
                link_debt[key] = advance_debt(
                    link_debt[key],
                    link_heat[key],
                    LINK_COMFORT_HEAT,
                    cooling,
                    step,
                )

            elapsed += step
            segment_elapsed += step
            timeline.append({
                "elapsed_days": elapsed,
                "persons": {
                    pid: {
                        "heat": person_heat[pid],
                        "recovery_debt_heat_days": person_debt[pid],
                        "band": person_heat_band(person_heat[pid]),
                    }
                    for pid in person_heat
                },
                "links": {
                    key: {
                        "heat": link_heat[key],
                        "damage": link_damage[key],
                        "recovery_debt_heat_days": link_debt[key],
                        "band": link_heat_band(
                            link_heat[key], link_damage[key]
                        ),
                    }
                    for key in link_heat
                },
            })

    return {
        "profile_name": profile.get("name", "unnamed"),
        "cutoff_day": float(initial["day"]),
        "projected_days": elapsed,
        "recent_means": means,
        "initial": {
            "persons": initial["persons"],
            "links": initial["links"],
        },
        "final": timeline[-1] if timeline else {
            "elapsed_days": 0.0,
            "persons": initial["persons"],
            "links": initial["links"],
        },
        "timeline": timeline,
        "hypothesis_boundary": (
            "Recovery multipliers/boosts are scenario assumptions for comparison, "
            "not empirically validated treatment effects."
        ),
    }
