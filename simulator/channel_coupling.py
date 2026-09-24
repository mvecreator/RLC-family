#!/usr/bin/env python3
"""CHANNEL-COUPLING1 explicit branch-to-branch modulation.

Rules are declarative and deterministic.

All source signals are measured from the uncoupled branch set at the current
PERSON-TIME2 state. Target modifications are then accumulated and applied
simultaneously. This avoids hidden algebraic iteration/cycle order dependence.
"""

from __future__ import annotations

import copy

VERSION = "RLC-FAMILY-CHANNEL-COUPLING1-0.1"

SOURCE_SIGNALS = {
    "current_abs",
    "power",
    "conductance",
    "communication_quality",
    "effective_transmission",
    "hostility",
    "gate",
}

TARGET_FIELDS = {
    "communication_quality",
    "contact_frequency",
    "availability",
    "hostility",
    "gate",
    "reverse_ratio",
}


def clip01(value):
    return max(0.0, min(1.0, float(value)))


def _positive(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be number") from e
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value


def _gain(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{name} must be number") from e
    if value < -1.0 or value > 1.0:
        raise ValueError(f"{name} must be in [-1,1]")
    return value


def compile_couplings(scenario, links):
    raw = scenario.get(
        "channel_couplings",
        scenario.get("связи_между_каналами", []),
    )
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError("channel_couplings must be list")

    by_id = {str(link["link_id"]): link for link in links}
    out = []
    seen = set()

    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"channel_couplings[{idx}] must be object")

        cid = str(
            item.get("coupling_id", item.get("id", f"coupling-{idx+1}"))
        ).strip()
        if not cid:
            raise ValueError(f"channel_couplings[{idx}].coupling_id required")
        if cid in seen:
            raise ValueError(f"duplicate coupling_id: {cid}")
        seen.add(cid)

        source = str(item.get("source_link_id", "")).strip()
        target = str(item.get("target_link_id", "")).strip()
        if source not in by_id:
            raise ValueError(f"{cid}: unknown source_link_id {source}")
        if target not in by_id:
            raise ValueError(f"{cid}: unknown target_link_id {target}")
        if source == target:
            raise ValueError(f"{cid}: source and target link must differ")

        signal = str(item.get("source_signal", "power")).strip().lower()
        if signal not in SOURCE_SIGNALS:
            raise ValueError(
                f"{cid}: source_signal must be one of "
                + ", ".join(sorted(SOURCE_SIGNALS))
            )

        field = str(item.get("target_field", "")).strip()
        if field not in TARGET_FIELDS:
            raise ValueError(
                f"{cid}: target_field must be one of "
                + ", ".join(sorted(TARGET_FIELDS))
            )

        target_link = by_id[target]
        element = target_link.get("element_type", "RESISTIVE")
        if field == "gate" and element != "MOSFET":
            raise ValueError(f"{cid}: gate target requires MOSFET")
        if field == "reverse_ratio" and element not in {
            "DIODE", "MOSFET", "BREAKDOWN_DIODE"
        }:
            raise ValueError(
                f"{cid}: reverse_ratio target requires nonlinear directed link"
            )

        default_scale = {
            "power": 0.02,
            "current_abs": 0.15,
            "conductance": 1.0,
            "communication_quality": 1.0,
            "effective_transmission": 1.0,
            "hostility": 1.0,
            "gate": 1.0,
        }[signal]
        source_scale = _positive(
            item.get("source_scale", default_scale),
            f"{cid}.source_scale",
        )
        threshold = clip01(item.get("threshold", 0.0))
        gain = _gain(item.get("gain", 0.0), f"{cid}.gain")
        max_abs_effect = clip01(item.get("max_abs_effect", 1.0))

        out.append({
            "coupling_id": cid,
            "source_link_id": source,
            "target_link_id": target,
            "source_signal": signal,
            "source_scale": source_scale,
            "threshold": threshold,
            "gain": gain,
            "max_abs_effect": max_abs_effect,
            "target_field": field,
            "same_pair": (
                by_id[source].get("pair_id")
                == by_id[target].get("pair_id")
            ),
            "description": str(item.get("description", "")),
        })

    return out


def branch_signals(links, voltages, index, semi):
    signals = {}
    for link in links:
        i = index[link["from"]]
        j = index[link["to"]]
        dv = float(voltages[i]) - float(voltages[j])
        current = semi.current(link, voltages[i], voltages[j])
        signals[str(link["link_id"])] = {
            "delta_v": dv,
            "current": current,
            "current_abs": abs(current),
            "power": abs(dv * current),
            "conductance": semi.conductance(link, dv),
            "communication_quality": float(
                link.get("communication_quality", link.get("quality", 0.0))
            ),
            "effective_transmission": float(
                link.get("effective_transmission", link.get("quality", 0.0))
            ),
            "hostility": float(link.get("hostility", 0.0)),
            "gate": float(link.get("gate", 0.0) or 0.0),
        }
    return signals


def apply_couplings(links, voltages, index, rules, semi, refresh_semantics):
    """Apply one simultaneous explicit coupling layer.

    Source signals are captured before any target is changed.
    """
    if not rules:
        return links, []

    source_signals = branch_signals(links, voltages, index, semi)
    out = copy.deepcopy(links)
    by_id = {str(link["link_id"]): link for link in out}
    deltas = {}
    effects = []

    for rule in rules:
        source = source_signals[rule["source_link_id"]]
        raw = float(source[rule["source_signal"]])
        normalized = clip01(raw / rule["source_scale"])
        excess = max(0.0, normalized - rule["threshold"])
        effect = rule["gain"] * excess
        limit = rule["max_abs_effect"]
        effect = max(-limit, min(limit, effect))

        target_id = rule["target_link_id"]
        field = rule["target_field"]
        deltas[(target_id, field)] = (
            deltas.get((target_id, field), 0.0) + effect
        )
        effects.append({
            "coupling_id": rule["coupling_id"],
            "source_link_id": rule["source_link_id"],
            "target_link_id": target_id,
            "source_signal": rule["source_signal"],
            "source_value": raw,
            "normalized_source": normalized,
            "threshold": rule["threshold"],
            "activation_excess": excess,
            "gain": rule["gain"],
            "target_field": field,
            "delta": effect,
        })

    semantic_fields = {
        "communication_quality",
        "contact_frequency",
        "availability",
        "hostility",
    }

    for (target_id, field), delta in deltas.items():
        link = by_id[target_id]
        base = float(link.get(field, 0.0))
        link[field] = clip01(base + delta)

    touched_semantic = {
        target_id
        for (target_id, field) in deltas
        if field in semantic_fields
    }
    for target_id in touched_semantic:
        refresh_semantics(by_id[target_id])

    return out, effects
