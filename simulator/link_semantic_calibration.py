#!/usr/bin/env python3
"""LINK-SEM-CAL: directional calibration for LINK-SEM1 semantics."""

from __future__ import annotations

import json
import math

from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core


def two_adults(link):
    return {
        "person_model": {"gender_prior_strength": 0},
        "персонажи": [
            {"id": "a", "type": "adult", "gender": "male"},
            {"id": "b", "type": "adult", "gender": "female"},
        ],
        "связи_персонажей": [dict({"from": "a", "to": "b"}, **link)],
    }


def sample(link, current=0.15):
    return {
        "financial_stress": 0.0,
        "active_events": [],
        "nodes": [
            {"id": "a", "voltage": 0.10, "memory": 0.10},
            {"id": "b", "voltage": -0.10, "memory": 0.10},
        ],
        "links": [dict({
            "from": "a",
            "to": "b",
            "current_abs": current,
        }, **link)],
    }


def suite():
    legacy_ir = pm.compile_person_network(two_adults({"quality": 0.20}))
    legacy = legacy_ir["links"][0]

    rare = pm.compile_person_network(two_adults({
        "communication_quality": 0.95,
        "contact_frequency": 0.10,
        "availability": 0.80,
        "hostility": 0.02,
    }))["links"][0]

    frequent_good = pm.compile_person_network(two_adults({
        "communication_quality": 0.95,
        "contact_frequency": 1.0,
        "availability": 1.0,
        "hostility": 0.02,
    }))["links"][0]

    frequent_hostile = pm.compile_person_network(two_adults({
        "communication_quality": 0.95,
        "contact_frequency": 1.0,
        "availability": 1.0,
        "hostility": 0.90,
    }))["links"][0]

    rare_safety = family_safety.instantaneous_components(
        sample(rare)
    )["links"]["a->b"]
    good_safety = family_safety.instantaneous_components(
        sample(frequent_good)
    )["links"]["a->b"]
    hostile_safety = family_safety.instantaneous_components(
        sample(frequent_hostile)
    )["links"]["a->b"]

    node_ids = {"a", "b"}
    link_keys = {("a", "b")}
    event_spec = {
        "события": [{
            "id": "travel",
            "день": 0,
            "длительность_дней": 1,
            "связь": ["a", "b"],
            "availability_set": 0.10,
        }]
    }
    events = pts._compile_events(event_spec, node_ids, link_keys)
    base_ir = pm.compile_person_network(two_adults({
        "communication_quality": 0.90,
        "contact_frequency": 1.0,
        "availability": 1.0,
        "hostility": 0.05,
    }))
    _, mutated_links, _ = pts._network_at(
        two_adults({
            "communication_quality": 0.90,
            "contact_frequency": 1.0,
            "availability": 1.0,
            "hostility": 0.05,
        }),
        base_ir,
        events,
        0.5,
    )
    mutated = mutated_links[0]

    missing_target_rejected = False
    try:
        pts._compile_events(
            {"события": [{
                "id": "bad",
                "hostility_set": 0.8,
            }]},
            node_ids,
            link_keys,
        )
    except core.ScenarioError:
        missing_target_rejected = True

    checks = {
        "LSEM01_LEGACY_TRANSPORT": (
            abs(legacy["effective_transmission"] - 0.20) < 1e-12
            and abs(legacy["R_link"] - pm.link_resistance(0.20)) < 1e-12
        ),
        "LSEM02_LOW_CONTACT_REDUCES_TRANSPORT": (
            rare["effective_transmission"]
            < frequent_good["effective_transmission"]
        ),
        "LSEM03_RARE_GOOD_NOT_HIGH_FRICTION": (
            rare_safety["relational_friction"] < 0.05
            and rare_safety["combined"] < 0.22
        ),
        "LSEM04_HOSTILITY_RAISES_STRAIN": (
            hostile_safety["relational_friction"]
            > good_safety["relational_friction"] + 0.25
            and hostile_safety["combined"]
            > good_safety["combined"] + 0.10
        ),
        "LSEM05_AVAILABILITY_EVENT_IS_SEMANTIC": (
            abs(mutated["availability"] - 0.10) < 1e-12
            and abs(mutated["communication_quality"] - 0.90) < 1e-12
            and abs(mutated["hostility"] - 0.05) < 1e-12
            and mutated["effective_transmission"]
            < base_ir["links"][0]["effective_transmission"]
        ),
        "LSEM06_TARGET_LINK_REQUIRED": missing_target_rejected,
    }

    return {
        "model": "LINK-SEM1",
        "legacy": legacy,
        "rare_good": {
            "transport": rare["effective_transmission"],
            "friction": rare_safety["relational_friction"],
            "instantaneous_strain": rare_safety["combined"],
        },
        "frequent_hostile": {
            "transport": frequent_hostile["effective_transmission"],
            "friction": hostile_safety["relational_friction"],
            "instantaneous_strain": hostile_safety["combined"],
        },
        "availability_event": {
            "before": base_ir["links"][0]["effective_transmission"],
            "after": mutated["effective_transmission"],
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
