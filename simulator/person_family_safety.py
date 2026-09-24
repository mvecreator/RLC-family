#!/usr/bin/env python3
"""PERSON-FAMILY-SAFETY1: accumulated stress and relationship-strain guardrails.

This layer consumes PERSON-TIME2 trajectories and adds slow state variables for:
- accumulated load per person;
- accumulated strain per relationship/link;
- transparent early-warning signals and repair recommendations.

It does NOT predict divorce, compatibility, abuse, or psychiatric diagnoses.
A BREAKDOWN_RISK_REVIEW signal means sustained model strain deserves attention;
it is not a probability or forecast.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from simulator import person_time_solver as pts
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import person_time_solver as pts
    import rlc_family_sim as core

VERSION = "RLC-FAMILY-PERSON-FAMILY-SAFETY1-0.1"

SAFETY_FLAGS = (
    "violence_or_threats",
    "coercive_control",
    "fear_for_safety",
)


def clip01(value):
    return max(0.0, min(1.0, float(value)))


def norm(value, scale):
    if scale <= 0:
        raise core.ScenarioError("normalization scale must be > 0")
    return clip01(abs(float(value)) / scale)


def _node_map(sample):
    return {x["id"]: x for x in sample["nodes"]}


def _link_key(link):
    return "->".join(sorted((str(link["from"]), str(link["to"]))))


def _incident_link_load(sample, pid):
    values = []
    for link in sample["links"]:
        if pid not in (link["from"], link["to"]):
            continue
        poor = 1.0 - clip01(link["quality"])
        flow = norm(link["current_abs"], 0.15)
        values.append(poor * flow)
    return sum(values) / len(values) if values else 0.0


def instantaneous_components(sample):
    nodes = _node_map(sample)
    financial = clip01(sample["financial_stress"])

    persons = {}
    for pid, node in nodes.items():
        excitation = norm(node["voltage"], 0.30)
        memory = clip01(node["memory"])
        incident = _incident_link_load(sample, pid)
        combined = clip01(
            0.25 * excitation
            + 0.35 * memory
            + 0.20 * incident
            + 0.20 * financial
        )
        persons[pid] = {
            "excitation": excitation,
            "memory": memory,
            "incident_link_stress": incident,
            "financial_stress": financial,
            "combined": combined,
        }

    links = {}
    for link in sample["links"]:
        a = str(link["from"])
        b = str(link["to"])
        key = _link_key(link)
        quality = clip01(link["quality"])
        poor = 1.0 - quality
        flow = norm(link["current_abs"], 0.15)
        mem = 0.5 * (
            clip01(nodes[a]["memory"]) + clip01(nodes[b]["memory"])
        )
        gap = norm(nodes[a]["voltage"] - nodes[b]["voltage"], 0.20)

        # High current is not itself conflict. Interaction contributes to
        # strain mainly when the channel is poor.
        stressed_interaction = flow * (0.20 + 0.80 * poor)
        combined = clip01(
            0.30 * poor
            + 0.25 * stressed_interaction
            + 0.25 * mem
            + 0.10 * gap
            + 0.10 * financial
        )
        links[key] = {
            "from": a,
            "to": b,
            "quality": quality,
            "poor_quality": poor,
            "interaction": flow,
            "stressed_interaction": stressed_interaction,
            "memory_mean": mem,
            "voltage_gap": gap,
            "financial_stress": financial,
            "combined": combined,
        }

    return {"persons": persons, "links": links}


def _advance(state, load, dt, accumulation=0.45, recovery=0.14):
    return clip01(
        state
        + dt * accumulation * load * (1.0 - state)
        - dt * recovery * state
    )


def integrate_trajectory(person_time_result):
    samples = person_time_result["samples"]
    if not samples:
        raise core.ScenarioError("PERSON-TIME2 returned no samples")

    first = instantaneous_components(samples[0])
    person_state = {pid: 0.20 for pid in first["persons"]}
    link_state = {key: 0.15 for key in first["links"]}

    rows = []
    prev_day = float(samples[0]["day"])
    for index, sample in enumerate(samples):
        day = float(sample["day"])
        dt = max(0.0, day - prev_day) if index else 0.0
        comp = instantaneous_components(sample)

        if dt > 0:
            for pid, item in comp["persons"].items():
                person_state[pid] = _advance(
                    person_state[pid], item["combined"], dt
                )
            for key, item in comp["links"].items():
                link_state[key] = _advance(
                    link_state[key], item["combined"], dt,
                    accumulation=0.50,
                    recovery=0.10,
                )

        rows.append({
            "day": day,
            "persons": {
                pid: {
                    **comp["persons"][pid],
                    "accumulated_load": person_state[pid],
                }
                for pid in comp["persons"]
            },
            "links": {
                key: {
                    **comp["links"][key],
                    "accumulated_strain": link_state[key],
                }
                for key in comp["links"]
            },
            "financial_stress": sample["financial_stress"],
            "active_events": sample["active_events"],
        })
        prev_day = day
    return rows


def _first_crossing(rows, group, key, threshold):
    for row in rows:
        item = row[group].get(key)
        if item and item[
            "accumulated_load" if group == "persons" else "accumulated_strain"
        ] >= threshold:
            return row["day"]
    return None


def _max_state(rows, group, key):
    field = "accumulated_load" if group == "persons" else "accumulated_strain"
    peak = max(
        ((row["day"], row[group][key][field]) for row in rows),
        key=lambda x: x[1],
    )
    return {"day": peak[0], "value": peak[1]}


def _mean_components(rows, key):
    fields = (
        "poor_quality",
        "stressed_interaction",
        "memory_mean",
        "voltage_gap",
        "financial_stress",
    )
    out = {}
    for field in fields:
        values = [row["links"][key][field] for row in rows]
        out[field] = sum(values) / len(values)
    return out


def safety_override(flags=None):
    flags = flags or {}
    if not isinstance(flags, dict):
        raise core.ScenarioError("relationship_flags must be object")
    triggered = [k for k in SAFETY_FLAGS if flags.get(k) is True]
    if triggered:
        return {
            "active": True,
            "triggered_by": triggered,
            "message": (
                "Safety concerns override relationship-optimization advice. "
                "Prioritize personal safety and individual professional/support "
                "resources; do not use a joint repair recommendation to delay help."
            ),
        }
    return {
        "active": False,
        "triggered_by": [],
        "message": (
            "No explicit relationship-safety flag was supplied. Missing flags "
            "remain unknown, not automatically false."
        ),
    }


def recommendations_for_link(key, summary, safety):
    if safety["active"]:
        return [{
            "action": "SAFETY_FIRST",
            "reason": "explicit_safety_flag",
            "message": safety["message"],
        }]

    mean = summary["mean_components"]
    peak = summary["peak_strain"]["value"]
    actions = []

    if mean["financial_stress"] >= 0.25:
        actions.append({
            "action": "REDUCE_SHARED_FINANCIAL_PRESSURE",
            "reason": "financial_stress",
            "message": (
                "Treat financial pressure as a shared external load before "
                "interpreting all strain as an interpersonal failure."
            ),
        })
    if mean["poor_quality"] >= 0.30:
        actions.append({
            "action": "PROTECT_COMMUNICATION_CHANNEL",
            "reason": "poor_link_quality",
            "message": (
                "Create lower-conflict communication windows and avoid repeating "
                "the same high-load exchange while the channel is degraded."
            ),
        })
    if mean["memory_mean"] >= 0.45:
        actions.append({
            "action": "ALLOW_RECOVERY_BEFORE_REPLAY",
            "reason": "high_accumulated_memory",
            "message": (
                "The model carries substantial memory from prior events; allow "
                "recovery before replaying the same dispute."
            ),
        })
    if peak >= 0.50:
        actions.append({
            "action": "RELATIONSHIP_REPAIR_REVIEW",
            "reason": "sustained_link_strain",
            "message": (
                "Schedule a deliberate repair conversation; if repeated attempts "
                "do not reduce strain, consider a qualified relationship counsellor."
            ),
        })
    if peak >= 0.65:
        actions.append({
            "action": "BREAKDOWN_RISK_REVIEW",
            "reason": "persistent_high_accumulated_strain",
            "message": (
                "The link is in the project's sustained high-strain region. "
                "Review whether the relationship is recovering or progressively "
                "disconnecting. This is an early-warning guardrail, not a divorce "
                "prediction or probability."
            ),
        })
    return actions


def summarize(rows, relationship_flags=None):
    safety = safety_override(relationship_flags)
    person_ids = list(rows[0]["persons"])
    link_keys = list(rows[0]["links"])

    persons = {}
    for pid in person_ids:
        persons[pid] = {
            "peak_load": _max_state(rows, "persons", pid),
            "first_monitor_day": _first_crossing(
                rows, "persons", pid, 0.45
            ),
            "first_overload_review_day": _first_crossing(
                rows, "persons", pid, 0.60
            ),
            "final_load": rows[-1]["persons"][pid]["accumulated_load"],
        }

    links = {}
    for key in link_keys:
        summary = {
            "peak_strain": _max_state(rows, "links", key),
            "first_strain_day": _first_crossing(
                rows, "links", key, 0.40
            ),
            "first_repair_review_day": _first_crossing(
                rows, "links", key, 0.50
            ),
            "first_breakdown_risk_day": _first_crossing(
                rows, "links", key, 0.65
            ),
            "final_strain": rows[-1]["links"][key]["accumulated_strain"],
            "mean_components": _mean_components(rows, key),
        }
        summary["recommendations"] = recommendations_for_link(
            key, summary, safety
        )
        summary["breakdown_probability_computed"] = False
        links[key] = summary

    highest = (
        max(links.items(), key=lambda kv: kv[1]["peak_strain"]["value"])[0]
        if links else None
    )
    return {
        "persons": persons,
        "links": links,
        "highest_strain_link": highest,
        "relationship_safety_override": safety,
        "family_stress_is_diagnostic": False,
        "breakdown_probability_computed": False,
    }


def assess(scenario, timeline, relationship_flags=None):
    time_result = pts.simulate_person_timeline(scenario, timeline)
    if len(time_result["summary"]["persons"]) < 2:
        raise core.ScenarioError(
            "PERSON-FAMILY-SAFETY1 requires at least two persons"
        )
    rows = integrate_trajectory(time_result)
    return {
        "model_version": VERSION,
        "scenario_name": time_result["scenario_name"],
        "timeline_model_version": time_result["model_version"],
        "trajectory": rows,
        "summary": summarize(rows, relationship_flags),
        "limitations": [
            "accumulated_load and accumulated_strain are project engineering indices",
            "the model does not predict divorce or calculate relationship-breakdown probability",
            "high interaction current alone is not treated as conflict",
            "explicit safety concerns override joint repair recommendations",
        ],
    }


def _load(path):
    text = Path(path).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise core.ScenarioError(f"{path}: root must be object")
    return value


def main():
    p = argparse.ArgumentParser(
        description="PERSON-FAMILY-SAFETY1 accumulated relationship strain"
    )
    p.add_argument("scenario")
    p.add_argument("timeline")
    p.add_argument("--relationship-flags")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    scenario = _load(args.scenario)
    timeline = _load(args.timeline)
    flags = _load(args.relationship_flags) if args.relationship_flags else None
    result = assess(scenario, timeline, flags)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
