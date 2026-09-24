#!/usr/bin/env python3
"""PERSON2 compiler: family characters -> mixed per-person RLC network IR."""

from __future__ import annotations

import itertools
from copy import deepcopy

try:
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import rlc_family_sim as core

VERSION = "RLC-FAMILY-PERSON2-0.1"

DEFAULTS = {
    "gender_prior_strength": 0.15,
    "role_strength": 0.75,
    "temperament_strength": 0.60,
    "reactive_orientation_gain": 0.65,
    "adult_base_c": 1.50,
    "adult_base_l": 1.50,
    "adult_base_r": 0.90,
    "child_base_c": 1.00,
    "child_base_l": 1.00,
    "child_r_min": 0.35,
    "child_r_max": 2.80,
    "child_r_power": 1.35,
    "legacy_gender_profile": False,
    "child_legacy_strength": 0.55,
    "default_link_quality": 0.70,
}


def clip(value, lo, hi):
    return max(lo, min(hi, value))


def _num(value, name, lo=None, hi=None):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise core.ScenarioError(f"{name}: expected number") from e
    if lo is not None and value < lo:
        raise core.ScenarioError(f"{name}: expected >= {lo}")
    if hi is not None and value > hi:
        raise core.ScenarioError(f"{name}: expected <= {hi}")
    return value


def _config(scenario):
    raw = scenario.get("person_model", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise core.ScenarioError("person_model must be object")
    cfg = dict(DEFAULTS)
    cfg.update(raw)
    for key in (
        "gender_prior_strength", "role_strength", "temperament_strength",
        "reactive_orientation_gain", "default_link_quality",
    ):
        cfg[key] = _num(cfg[key], f"person_model.{key}", 0.0, 1.0)
    for key in (
        "adult_base_c", "adult_base_l", "adult_base_r",
        "child_base_c", "child_base_l",
        "child_r_min", "child_r_max", "child_r_power",
        "child_legacy_strength",
    ):
        cfg[key] = _num(cfg[key], f"person_model.{key}", 0.0)
    if cfg["adult_base_c"] == 0 or cfg["adult_base_l"] == 0 or cfg["adult_base_r"] == 0:
        raise core.ScenarioError("adult base R/L/C must be > 0")
    if cfg["child_base_c"] == 0 or cfg["child_base_l"] == 0:
        raise core.ScenarioError("child base C/L must be > 0")
    if cfg["child_r_min"] <= 0 or cfg["child_r_max"] <= 0:
        raise core.ScenarioError("child R limits must be > 0")
    if cfg["child_r_max"] < cfg["child_r_min"]:
        raise core.ScenarioError("child_r_max must be >= child_r_min")
    cfg["legacy_gender_profile"] = bool(cfg.get("legacy_gender_profile", False))
    return cfg


def gender_sign(label):
    label = str(label or "").strip().lower()
    if label in {"male", "man", "boy", "мужчина", "муж", "мальчик"}:
        return 1.0
    if label in {"female", "woman", "girl", "женщина", "жена", "девочка"}:
        return -1.0
    return 0.0


def _role_value(role, key, default=0.5):
    return _num(role.get(key, default), f"role.{key}", 0.0, 1.0)


def role_balance(person):
    role = person.get("role", {})
    if role is None:
        role = {}
    if not isinstance(role, dict):
        raise core.ScenarioError(f"{person.get('id','person')}.role must be object")
    work = _role_value(role, "work_provider")
    decision = _role_value(role, "decision_initiative")
    external = _role_value(role, "external_activity")
    caregiver = _role_value(role, "caregiver")
    home = _role_value(role, "domestic_load")
    value = (
        0.40 * work
        + 0.40 * decision
        + 0.20 * external
        - 0.50 * caregiver
        - 0.50 * home
    )
    return clip(value, -1.0, 1.0)


def _reactive_pair(base_c, base_l, orientation, gain):
    orientation = clip(orientation, -0.95, 0.95)
    c = base_c * (1.0 + gain * orientation)
    l = base_l * (1.0 - gain * orientation)
    if c <= 0 or l <= 0:
        raise core.ScenarioError("PERSON2 produced non-positive reactive component")
    return c, l


def compile_adult(person, cfg):
    pid = str(person.get("id", "")).strip()
    if not pid:
        raise core.ScenarioError("adult person requires id")
    role = role_balance(person)
    temperament = _num(person.get("temperament_bias", 0.0), f"{pid}.temperament_bias", -1.0, 1.0)
    recovery = _num(
        person.get("recovery_inertia", person.get("role", {}).get("recovery_inertia", 0.5)),
        f"{pid}.recovery_inertia", 0.0, 1.0,
    )
    legacy = gender_sign(person.get("gender")) * cfg["gender_prior_strength"]
    orientation = clip(
        cfg["role_strength"] * role
        + legacy
        + cfg["temperament_strength"] * temperament,
        -0.95, 0.95,
    )
    c, l = _reactive_pair(
        cfg["adult_base_c"], cfg["adult_base_l"], orientation,
        cfg["reactive_orientation_gain"],
    )
    r = cfg["adult_base_r"] * (0.65 + 0.70 * recovery)
    return {
        "id": pid,
        "kind": "adult",
        "gender_label": person.get("gender"),
        "age": person.get("age"),
        "role_balance": role,
        "legacy_orientation": legacy,
        "temperament_bias": temperament,
        "effective_orientation": orientation,
        "R": r,
        "C": c,
        "L": l,
        "c_to_l_ratio": c / l,
        "l_to_c_ratio": l / c,
    }


def child_resistance(age, cfg):
    maturity = clip(_num(age, "child.age", 0.0) / 18.0, 0.0, 1.0)
    return (
        cfg["child_r_min"]
        + (cfg["child_r_max"] - cfg["child_r_min"])
        * (1.0 - maturity) ** cfg["child_r_power"]
    )


def compile_child(person, cfg):
    pid = str(person.get("id", "")).strip()
    if not pid:
        raise core.ScenarioError("child person requires id")
    age = _num(person.get("age", 0), f"{pid}.age", 0.0)
    maturity = clip(age / 18.0, 0.0, 1.0)
    temperament = _num(person.get("temperament_bias", 0.0), f"{pid}.temperament_bias", -1.0, 1.0)
    legacy = 0.0
    if cfg["legacy_gender_profile"]:
        legacy = gender_sign(person.get("gender")) * cfg["child_legacy_strength"] * maturity
    orientation = clip(
        legacy + cfg["temperament_strength"] * temperament,
        -0.95, 0.95,
    )
    c, l = _reactive_pair(
        cfg["child_base_c"], cfg["child_base_l"], orientation,
        cfg["reactive_orientation_gain"],
    )
    r = child_resistance(age, cfg)
    return {
        "id": pid,
        "kind": "child",
        "gender_label": person.get("gender"),
        "age": age,
        "maturity": maturity,
        "legacy_orientation": legacy,
        "temperament_bias": temperament,
        "effective_orientation": orientation,
        "R": r,
        "C": c,
        "L": l,
        "c_to_l_ratio": c / l,
        "l_to_c_ratio": l / c,
    }


def compile_person(person, cfg):
    if not isinstance(person, dict):
        raise core.ScenarioError("each person must be object")
    kind = str(person.get("type", "")).strip().lower()
    if kind == "adult":
        return compile_adult(person, cfg)
    if kind == "child":
        return compile_child(person, cfg)
    raise core.ScenarioError(f"{person.get('id','person')}: type must be adult or child")


def link_resistance(quality):
    quality = _num(quality, "link quality", 0.0, 1.0)
    return 0.15 + 2.35 * (1.0 - quality)


def _compile_links(scenario, nodes, cfg):
    raw = scenario.get("связи_персонажей")
    node_ids = {n["id"] for n in nodes}
    links = []
    if raw is None:
        global_quality = scenario.get("связь", {}).get(
            "качество_проводника", cfg["default_link_quality"]
        )
        quality = _num(global_quality, "связь.качество_проводника", 0.0, 1.0)
        for a, b in itertools.combinations(sorted(node_ids), 2):
            links.append({
                "from": a, "to": b, "quality": quality,
                "R_link": link_resistance(quality), "source": "default-complete-graph",
            })
        return links
    if not isinstance(raw, list):
        raise core.ScenarioError("связи_персонажей must be list")
    seen = set()
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise core.ScenarioError(f"link {idx}: expected object")
        a = str(item.get("from", "")).strip()
        b = str(item.get("to", "")).strip()
        if a not in node_ids or b not in node_ids or a == b:
            raise core.ScenarioError(f"link {idx}: invalid endpoints")
        key = tuple(sorted((a, b)))
        if key in seen:
            raise core.ScenarioError(f"duplicate link: {a}-{b}")
        seen.add(key)
        quality = _num(item.get("quality", cfg["default_link_quality"]), f"link {a}-{b}.quality", 0.0, 1.0)
        links.append({
            "from": a, "to": b, "quality": quality,
            "R_link": link_resistance(quality), "source": "explicit",
        })
    return links


def compile_person_network(scenario):
    raw = scenario.get("персонажи")
    if raw is None:
        return {
            "model_version": VERSION,
            "mode": "legacy",
            "nodes": [],
            "links": [],
        }
    if not isinstance(raw, list) or not raw:
        raise core.ScenarioError("персонажи must be a non-empty list")
    cfg = _config(scenario)
    nodes = [compile_person(p, cfg) for p in raw]
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise core.ScenarioError("person ids must be unique")
    links = _compile_links(scenario, nodes, cfg)
    return {
        "model_version": VERSION,
        "mode": "PERSON2",
        "config": cfg,
        "nodes": nodes,
        "links": links,
    }


def attach_person_ir(scenario):
    out = deepcopy(scenario)
    out["person_ir"] = compile_person_network(scenario)
    return out
