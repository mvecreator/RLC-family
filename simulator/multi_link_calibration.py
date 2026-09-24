#!/usr/bin/env python3
"""MULTI-LINK-CAL1: calibration gates for parallel relationship channels."""

from __future__ import annotations

import json
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_network_solver as pnet
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core
from simulator import thermal_recovery as therm


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def base_scenario(links):
    return {
        "название": "MULTI-LINK-CAL1",
        "person_model": {"gender_prior_strength": 0.0},
        "персонажи": [
            {
                "id": "a",
                "type": "adult",
                "gender": "male",
                "source_weight": 0.25,
            },
            {
                "id": "b",
                "type": "adult",
                "gender": "female",
                "source_weight": 0.75,
            },
        ],
        "связи_персонажей": links,
        "отношения": {
            "напряженность": 0.25,
            "частота_событий": 1.0,
            "накопленная_память": 0.15,
        },
        "связь": {
            "качество_проводника": 0.80,
            "усиление_эмоций": 1.0,
            "фильтр_критического_мышления": 0.80,
            "усиление_антенны": 0.20,
            "внешний_фон": 0.10,
            "сброс_через_антенну": 0.30,
            "согласование_собеседника": 0.80,
        },
        "финансы": {
            "доходы_в_месяц": [1.0],
            "ипотека_в_месяц": 0.0,
            "базовые_расходы_в_месяц": 0.55,
            "прочие_расходы_в_месяц": 0.15,
            "резерв": 4.0,
            "долг_по_ипотеке": 0.0,
            "ставка_годовая": 0.0,
        },
    }


def two_parallel():
    return [
        {
            "link_id": "personal",
            "channel_kind": "personal",
            "from": "a",
            "to": "b",
            "communication_quality": 0.70,
            "contact_frequency": 0.60,
            "availability": 0.70,
            "hostility": 0.05,
            "element_type": "RESISTIVE",
        },
        {
            "link_id": "work",
            "channel_kind": "institutional_work",
            "from": "a",
            "to": "b",
            "communication_quality": 0.85,
            "contact_frequency": 0.95,
            "availability": 0.95,
            "hostility": 0.08,
            "element_type": "MOSFET",
            "gate": 0.85,
            "gate_threshold": 0.50,
            "gate_softness": 0.08,
            "off_ratio": 0.02,
            "reverse_ratio": 0.15,
        },
    ]


def safety_sample(link_count):
    links = [
        {
            "link_id": f"branch{i+1}",
            "pair_id": "a->b",
            "parallel_branch_count": link_count,
            "from": "a",
            "to": "b",
            "quality": 0.60,
            "communication_quality": 0.60,
            "contact_frequency": 1.0,
            "availability": 1.0,
            "hostility": 0.20,
            "current_abs": 0.12,
            "R_link": 1.0,
            "delta_v": 0.12,
            "power_vi_proxy": 0.0144,
        }
        for i in range(link_count)
    ]
    return {
        "financial_stress": 0.0,
        "active_events": [],
        "nodes": [
            {
                "id": "a",
                "kind": "adult",
                "age": 35,
                "voltage": 0.10,
                "memory": 0.10,
                "event_drive": 0.0,
            },
            {
                "id": "b",
                "kind": "adult",
                "age": 35,
                "voltage": -0.10,
                "memory": 0.10,
                "event_drive": 0.0,
            },
        ],
        "links": links,
    }


def suite():
    legacy = pm.compile_person_network(
        base_scenario([
            {"from": "a", "to": "b", "quality": 0.80}
        ])
    )
    parallel = pm.compile_person_network(
        base_scenario(two_parallel())
    )

    missing_id_rejected = False
    try:
        pm.compile_person_network(base_scenario([
            {"from": "a", "to": "b", "quality": 0.80},
            {
                "link_id": "work",
                "from": "a",
                "to": "b",
                "quality": 0.80,
            },
        ]))
    except core.ScenarioError:
        missing_id_rejected = True

    duplicate_id_rejected = False
    try:
        pm.compile_person_network(base_scenario([
            {
                "link_id": "same",
                "from": "a",
                "to": "b",
                "quality": 0.80,
            },
            {
                "link_id": "same",
                "from": "a",
                "to": "b",
                "quality": 0.70,
            },
        ]))
    except core.ScenarioError:
        duplicate_id_rejected = True

    ambiguous_event_rejected = False
    try:
        pts._compile_events(
            {
                "events": [{
                    "id": "ambiguous",
                    "at_day": 0,
                    "duration_days": 1,
                    "target_link": ["a", "b"],
                    "communication_quality_set": 0.50,
                }]
            },
            {"a", "b"},
            parallel["links"],
        )
    except core.ScenarioError:
        ambiguous_event_rejected = True

    targeted = pts._compile_events(
        {
            "events": [{
                "id": "target-work",
                "at_day": 0,
                "duration_days": 1,
                "target_link_id": "work",
                "gate_set": 0.15,
            }]
        },
        {"a", "b"},
        parallel["links"],
    )
    _, changed, _ = pts._network_at(
        base_scenario(two_parallel()),
        parallel,
        targeted,
        0.5,
    )
    changed_by_id = {link["link_id"]: link for link in changed}

    resistive = base_scenario([
        {
            "link_id": "r1",
            "channel_kind": "personal",
            "from": "a",
            "to": "b",
            "quality": 0.35,
            "element_type": "RESISTIVE",
        },
        {
            "link_id": "r2",
            "channel_kind": "work",
            "from": "a",
            "to": "b",
            "quality": 0.80,
            "element_type": "RESISTIVE",
        },
    ])
    linear = pnet.solve_network(resistive)
    linear_by_id = {link["link_id"]: link for link in linear["links"]}
    r1 = linear_by_id["r1"]
    r2 = linear_by_id["r2"]

    example_scenario = load_json(
        ROOT / "examples" / "multi_link1_work_personal_scenario.json"
    )
    example_timeline = load_json(
        ROOT / "examples" / "multi_link1_work_personal_timeline.json"
    )
    time = pts.simulate_person_timeline(
        example_scenario,
        example_timeline,
    )

    def nearest(day):
        return min(
            time["samples"],
            key=lambda row: abs(float(row["day"]) - float(day)),
        )

    at2 = {
        link["link_id"]: link
        for link in nearest(2.0)["links"]
    }
    at7 = {
        link["link_id"]: link
        for link in nearest(7.0)["links"]
    }

    safety = family_safety.assess(
        example_scenario,
        example_timeline,
    )
    pair = safety["summary"]["pairs"]["employee->employer"]

    thermal = therm.integrate_thermal(
        example_scenario,
        safety["trajectory"],
    )

    incident_one = family_safety._incident_link_load(
        safety_sample(1), "a"
    )
    incident_two = family_safety._incident_link_load(
        safety_sample(2), "a"
    )

    distinct = safety_sample(2)
    distinct["links"][1]["to"] = "c"
    distinct["links"][1]["pair_id"] = "a->c"
    distinct["links"][1]["current_abs"] = 0.06
    distinct_incident = family_safety._incident_link_load(
        distinct, "a"
    )
    friction = 0.65 * (1.0 - 0.60) + 0.35 * 0.20
    expected_distinct = (
        friction * (0.12 / 0.15)
        + friction * (0.06 / 0.15)
    ) / 2.0

    checks = {
        "ML01_LEGACY_SINGLE_ID_PRESERVED": (
            legacy["links"][0]["link_id"] == "a->b"
            and legacy["links"][0]["parallel_branch_count"] == 1
        ),
        "ML02_PARALLEL_BRANCHES_COMPILE": (
            {link["link_id"] for link in parallel["links"]}
            == {"personal", "work"}
            and all(
                link["parallel_branch_count"] == 2
                and link["is_parallel_branch"]
                for link in parallel["links"]
            )
        ),
        "ML03_PARALLEL_REQUIRES_EXPLICIT_IDS": missing_id_rejected,
        "ML04_LINK_IDS_UNIQUE": duplicate_id_rejected,
        "ML05_PAIR_EVENT_REJECTS_AMBIGUITY": ambiguous_event_rejected,
        "ML06_TARGETED_EVENT_MUTATES_ONE_BRANCH": (
            abs(changed_by_id["work"]["gate"] - 0.15) < 1e-12
            and changed_by_id["personal"]["element_type"] == "RESISTIVE"
            and changed_by_id["personal"].get("gate") is None
        ),
        "ML07_PARALLEL_RESISTOR_VOLTAGE_IDENTITY": (
            abs(
                abs(r1["current_re"] + 1j * r1["current_im"])
                * r1["R_link"]
                - abs(r2["current_re"] + 1j * r2["current_im"])
                * r2["R_link"]
            ) < 1e-9
            and abs(r1["current_abs"]) > 0.0
            and abs(r2["current_abs"]) > 0.0
        ),
        "ML08_MIXED_BRANCHES_RUN_IN_PERSON_TIME2": (
            set(at2) == {
                "employer-employee.personal",
                "employer-employee.work",
            }
            and abs(at2["employer-employee.work"]["gate"] - 0.95) < 1e-12
            and abs(at7["employer-employee.work"]["gate"] - 0.20) < 1e-12
            and at2["employer-employee.personal"]["element_type"]
            == "RESISTIVE"
        ),
        "ML09_FAMILY_SAFETY_PRESERVES_BRANCH_AND_PAIR_STATE": (
            set(safety["summary"]["links"]) == {
                "employer-employee.personal",
                "employer-employee.work",
            }
            and pair["branch_count"] == 2
            and set(pair["branches"]) == {
                "employer-employee.personal",
                "employer-employee.work",
            }
        ),
        "ML10_EXTRA_BRANCH_DOES_NOT_DILUTE_INCIDENT_LOAD": (
            incident_two > incident_one > 0.0
        ),
        "ML11_THERMAL_STATES_REMAIN_PER_BRANCH": (
            set(thermal[-1]["links"]) == {
                "employer-employee.personal",
                "employer-employee.work",
            }
        ),
        "ML12_DISTINCT_PAIR_AVERAGING_STAYS_LEGACY": (
            abs(distinct_incident - expected_distinct) < 1e-12
        ),
    }

    return {
        "benchmark": "MULTI-LINK-CAL1",
        "reference": {
            "legacy_link_id": legacy["links"][0]["link_id"],
            "parallel_link_ids": [
                link["link_id"] for link in parallel["links"]
            ],
            "r1_current_abs": r1["current_abs"],
            "r2_current_abs": r2["current_abs"],
            "r1_voltage_drop_abs": r1["current_abs"] * r1["R_link"],
            "r2_voltage_drop_abs": r2["current_abs"] * r2["R_link"],
            "incident_one_branch": incident_one,
            "incident_two_branches": incident_two,
            "distinct_pair_incident": distinct_incident,
            "distinct_pair_expected_legacy": expected_distinct,
            "pair_summary": pair,
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
