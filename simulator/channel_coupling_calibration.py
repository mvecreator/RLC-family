#!/usr/bin/env python3
"""CHANNEL-COUPLING-CAL1 calibration gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from simulator import channel_coupling as cc
from simulator import link_semiconductor as semi
from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_network_solver as pnet
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core


ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parallel_links():
    return [
        {
            "link_id": "personal",
            "channel_kind": "personal",
            "from": "employer",
            "to": "employee",
            "communication_quality": 0.82,
            "contact_frequency": 0.35,
            "availability": 0.65,
            "hostility": 0.04,
            "element_type": "RESISTIVE",
        },
        {
            "link_id": "work",
            "channel_kind": "institutional_work",
            "from": "employer",
            "to": "employee",
            "communication_quality": 0.78,
            "contact_frequency": 0.95,
            "availability": 0.95,
            "hostility": 0.10,
            "element_type": "MOSFET",
            "gate": 0.85,
            "gate_threshold": 0.50,
            "gate_softness": 0.08,
            "off_ratio": 0.02,
            "reverse_ratio": 0.15,
        },
    ]


def coupling_rules():
    return [
        {
            "coupling_id": "work-power-degrades-personal-quality",
            "source_link_id": "work",
            "source_signal": "power",
            "source_scale": 0.020,
            "threshold": 0.20,
            "target_link_id": "personal",
            "target_field": "communication_quality",
            "gain": -0.30,
            "max_abs_effect": 0.25,
        },
        {
            "coupling_id": "personal-quality-opens-work-reverse",
            "source_link_id": "personal",
            "source_signal": "communication_quality",
            "source_scale": 1.0,
            "threshold": 0.70,
            "target_link_id": "work",
            "target_field": "reverse_ratio",
            "gain": 0.30,
            "max_abs_effect": 0.10,
        },
    ]


def base_scenario(rules=None, links=None):
    return {
        "название": "CHANNEL-COUPLING-CAL1",
        "person_model": {"gender_prior_strength": 0.0},
        "персонажи": [
            {
                "id": "employer",
                "type": "adult",
                "gender": "female",
                "source_weight": 0.30,
            },
            {
                "id": "employee",
                "type": "adult",
                "gender": "male",
                "source_weight": 0.70,
            },
        ],
        "связи_персонажей": links if links is not None else parallel_links(),
        "channel_couplings": coupling_rules() if rules is None else rules,
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


def _static_apply(scenario):
    ir = pm.compile_person_network(scenario)
    index = {
        node["id"]: idx
        for idx, node in enumerate(ir["nodes"])
    }
    voltages = [0.0 for _ in ir["nodes"]]
    voltages[index["employer"]] = 0.20
    voltages[index["employee"]] = -0.20
    out, effects = cc.apply_couplings(
        ir["links"],
        voltages,
        index,
        ir["channel_couplings"],
        semi,
        pm.refresh_link_semantics,
    )
    return ir, out, effects


def suite():
    scenario = base_scenario()
    ir, coupled, effects = _static_apply(scenario)
    before = {link["link_id"]: link for link in ir["links"]}
    after = {link["link_id"]: link for link in coupled}
    effect_by_id = {
        effect["coupling_id"]: effect for effect in effects
    }

    no_rule_ir = pm.compile_person_network(base_scenario(rules=[]))
    no_rule_index = {
        node["id"]: idx
        for idx, node in enumerate(no_rule_ir["nodes"])
    }
    no_rule_v = [0.20, -0.20]
    no_rule_links, no_rule_effects = cc.apply_couplings(
        no_rule_ir["links"],
        no_rule_v,
        no_rule_index,
        [],
        semi,
        pm.refresh_link_semantics,
    )

    reversed_scenario = base_scenario(
        rules=list(reversed(coupling_rules()))
    )
    _, reversed_links, reversed_effects = _static_apply(
        reversed_scenario
    )
    reversed_by_id = {
        link["link_id"]: link for link in reversed_links
    }
    reversed_effect_by_id = {
        effect["coupling_id"]: effect
        for effect in reversed_effects
    }

    clamp_rule = [{
        "coupling_id": "clamp-quality",
        "source_link_id": "work",
        "source_signal": "gate",
        "source_scale": 1.0,
        "threshold": 0.0,
        "target_link_id": "personal",
        "target_field": "communication_quality",
        "gain": -1.0,
        "max_abs_effect": 1.0,
    }]
    _, clamp_links, _ = _static_apply(
        base_scenario(rules=clamp_rule)
    )
    clamp_by_id = {
        link["link_id"]: link for link in clamp_links
    }

    bad_unknown = False
    try:
        pm.compile_person_network(base_scenario(rules=[{
            "coupling_id": "bad-unknown",
            "source_link_id": "missing",
            "target_link_id": "personal",
            "source_signal": "power",
            "target_field": "communication_quality",
            "gain": -0.1,
        }]))
    except core.ScenarioError:
        bad_unknown = True

    bad_self = False
    try:
        pm.compile_person_network(base_scenario(rules=[{
            "coupling_id": "bad-self",
            "source_link_id": "personal",
            "target_link_id": "personal",
            "source_signal": "power",
            "target_field": "communication_quality",
            "gain": -0.1,
        }]))
    except core.ScenarioError:
        bad_self = True

    fake_links = [
        {
            "link_id": "ab",
            "pair_id": "a->b",
            "element_type": "RESISTIVE",
        },
        {
            "link_id": "bc",
            "pair_id": "b->c",
            "element_type": "RESISTIVE",
        },
    ]
    cross_pair_rejected = False
    try:
        cc.compile_couplings({
            "channel_couplings": [{
                "coupling_id": "cross",
                "source_link_id": "ab",
                "target_link_id": "bc",
                "source_signal": "communication_quality",
                "target_field": "communication_quality",
                "gain": -0.1,
            }]
        }, fake_links)
    except ValueError:
        cross_pair_rejected = True

    cross_pair_allowed = cc.compile_couplings({
        "channel_couplings": [{
            "coupling_id": "cross",
            "source_link_id": "ab",
            "target_link_id": "bc",
            "source_signal": "communication_quality",
            "target_field": "communication_quality",
            "gain": -0.1,
            "allow_cross_pair": True,
        }]
    }, fake_links)

    bad_gate_target = False
    try:
        pm.compile_person_network(base_scenario(rules=[{
            "coupling_id": "bad-gate",
            "source_link_id": "work",
            "target_link_id": "personal",
            "source_signal": "power",
            "target_field": "gate",
            "gain": -0.1,
        }]))
    except core.ScenarioError:
        bad_gate_target = True

    linear_links = [
        {
            "link_id": "r1",
            "from": "employer",
            "to": "employee",
            "quality": 0.60,
            "element_type": "RESISTIVE",
        },
        {
            "link_id": "r2",
            "from": "employer",
            "to": "employee",
            "quality": 0.80,
            "element_type": "RESISTIVE",
        },
    ]
    linear_rules = [{
        "coupling_id": "r1-to-r2",
        "source_link_id": "r1",
        "source_signal": "communication_quality",
        "target_link_id": "r2",
        "target_field": "communication_quality",
        "gain": -0.1,
    }]
    pnet_rejected = False
    try:
        pnet.solve_network(
            base_scenario(rules=linear_rules, links=linear_links)
        )
    except core.ScenarioError as e:
        pnet_rejected = "CHANNEL-COUPLING1" in str(e)

    example_scenario = load_json(
        ROOT / "examples" / "channel_coupling1_work_personal_scenario.json"
    )
    example_timeline = load_json(
        ROOT / "examples" / "channel_coupling1_work_personal_timeline.json"
    )
    time = pts.simulate_person_timeline(
        example_scenario,
        example_timeline,
    )
    observed_ids = {
        effect["coupling_id"]
        for sample in time["samples"]
        for effect in sample["channel_coupling_effects"]
    }
    work_delta_peak = max(
        abs(effect["delta"])
        for sample in time["samples"]
        for effect in sample["channel_coupling_effects"]
        if effect["coupling_id"]
        == "work-power-degrades-personal-quality"
    )

    family = family_safety.assess(
        example_scenario,
        example_timeline,
    )
    family_couplings = family["summary"]["channel_couplings"]

    work_effect = effect_by_id[
        "work-power-degrades-personal-quality"
    ]
    personal_effect = effect_by_id[
        "personal-quality-opens-work-reverse"
    ]

    expected_reverse = 0.15 + 0.30 * (0.82 - 0.70)

    checks = {
        "CC01_EMPTY_RULESET_IS_IDENTITY": (
            no_rule_links == no_rule_ir["links"]
            and no_rule_effects == []
        ),
        "CC02_RULES_COMPILE_WITH_STABLE_IDS": (
            {
                rule["coupling_id"]
                for rule in ir["channel_couplings"]
            }
            == {
                "work-power-degrades-personal-quality",
                "personal-quality-opens-work-reverse",
            }
        ),
        "CC03_WORK_POWER_DEGRADES_PERSONAL_QUALITY": (
            after["personal"]["communication_quality"]
            < before["personal"]["communication_quality"]
            and work_effect["delta"] < 0
        ),
        "CC04_SEMANTIC_COUPLING_REFRESHES_RESISTANCE": (
            after["personal"]["R_link"]
            > before["personal"]["R_link"]
        ),
        "CC05_PERSONAL_QUALITY_OPENS_WORK_REVERSE_PATH": (
            after["work"]["reverse_ratio"]
            > before["work"]["reverse_ratio"]
            and personal_effect["delta"] > 0
        ),
        "CC06_SIMULTANEOUS_READ_USES_BASE_SOURCE": (
            abs(after["work"]["reverse_ratio"] - expected_reverse)
            < 1e-12
        ),
        "CC07_RULE_ORDER_IS_INDEPENDENT": (
            abs(
                after["personal"]["communication_quality"]
                - reversed_by_id["personal"]["communication_quality"]
            ) < 1e-12
            and abs(
                after["work"]["reverse_ratio"]
                - reversed_by_id["work"]["reverse_ratio"]
            ) < 1e-12
            and {
                cid: round(effect["delta"], 12)
                for cid, effect in effect_by_id.items()
            }
            == {
                cid: round(effect["delta"], 12)
                for cid, effect in reversed_effect_by_id.items()
            }
        ),
        "CC08_TARGET_VALUES_ARE_CLAMPED": (
            clamp_by_id["personal"]["communication_quality"] == 0.0
            and 0.0 <= clamp_by_id["personal"]["R_link"]
        ),
        "CC09_UNKNOWN_LINK_IS_REJECTED": bad_unknown,
        "CC10_SELF_COUPLING_IS_REJECTED": bad_self,
        "CC11_CROSS_PAIR_REQUIRES_EXPLICIT_OPT_IN": (
            cross_pair_rejected
            and len(cross_pair_allowed) == 1
            and cross_pair_allowed[0]["allow_cross_pair"] is True
        ),
        "CC12_GATE_TARGET_REQUIRES_MOSFET": bad_gate_target,
        "CC13_PERSON_NET1_REJECTS_DYNAMIC_COUPLING": pnet_rejected,
        "CC14_PERSON_TIME2_EXPOSES_COUPLING_PROVENANCE": (
            observed_ids == {
                "work-power-degrades-personal-quality",
                "personal-quality-opens-work-reverse",
            }
            and work_delta_peak > 0.0
        ),
        "CC15_FAMILY_SAFETY_SUMMARIZES_COUPLING_PROVENANCE": (
            set(family_couplings) == {
                "work-power-degrades-personal-quality",
                "personal-quality-opens-work-reverse",
            }
            and family_couplings[
                "work-power-degrades-personal-quality"
            ]["peak_abs_delta"]["value"] > 0.0
        ),
    }

    return {
        "benchmark": "CHANNEL-COUPLING-CAL1",
        "model_version": cc.VERSION,
        "reference": {
            "base_personal_quality": before["personal"][
                "communication_quality"
            ],
            "coupled_personal_quality": after["personal"][
                "communication_quality"
            ],
            "base_personal_R": before["personal"]["R_link"],
            "coupled_personal_R": after["personal"]["R_link"],
            "base_work_reverse_ratio": before["work"]["reverse_ratio"],
            "coupled_work_reverse_ratio": after["work"]["reverse_ratio"],
            "expected_work_reverse_ratio_from_base_read": expected_reverse,
            "static_effects": effects,
            "dynamic_work_spillover_peak_abs_delta": work_delta_peak,
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
