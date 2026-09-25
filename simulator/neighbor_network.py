#!/usr/bin/env python3
"""NEIGHBOR-NET1: observed-event network and intervention-regime analysis.

This layer models:
- a central PERSON2 node;
- several neighboring PERSON2 nodes;
- explicit neighbor-neighbor social links already present in the scenario;
- observed stimulus events applied to named source neighbors;
- one external intervention marker;
- optional explicitly declared central relief impulse;
- retrospective before/after and counterfactual comparisons.

It does not infer intent, conspiracy, harassment, or intervention causality.
Temporal alignment is a signal statistic only.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core
from simulator import thermal_recovery as therm


VERSION = "RLC-FAMILY-NEIGHBOR-NET1-0.1"


def _num(value, name, lo=None, hi=None):
    try:
        value = float(value)
    except (TypeError, ValueError) as e:
        raise core.ScenarioError(f"{name} must be number") from e
    if lo is not None and value < lo:
        raise core.ScenarioError(f"{name} must be >= {lo}")
    if hi is not None and value > hi:
        raise core.ScenarioError(f"{name} must be <= {hi}")
    return value


def compile_spec(scenario, spec):
    if not isinstance(spec, dict):
        raise core.ScenarioError("neighbor_net1 spec must be object")

    ir = pm.compile_person_network(scenario)
    node_ids = {node["id"] for node in ir["nodes"]}

    central = str(spec.get("central_person_id", "")).strip()
    if central not in node_ids:
        raise core.ScenarioError(
            f"neighbor_net1.central_person_id unknown: {central}"
        )

    raw_households = spec.get("neighbor_households")
    households = []
    member_to_household = {}

    if raw_households is not None:
        if not isinstance(raw_households, list) or not raw_households:
            raise core.ScenarioError(
                "neighbor_households must be non-empty list"
            )
        seen_groups = set()
        for idx, item in enumerate(raw_households):
            if not isinstance(item, dict):
                raise core.ScenarioError(
                    f"neighbor_households[{idx}] must be object"
                )
            gid = str(item.get("group_id", "")).strip()
            if not gid:
                raise core.ScenarioError(
                    f"neighbor_households[{idx}].group_id required"
                )
            if gid in seen_groups:
                raise core.ScenarioError(
                    f"duplicate neighbor household group_id: {gid}"
                )
            seen_groups.add(gid)

            members_raw = item.get("members", [])
            if not isinstance(members_raw, list) or not members_raw:
                raise core.ScenarioError(
                    f"{gid}.members must be non-empty list"
                )
            members = [str(x).strip() for x in members_raw]
            if len(set(members)) != len(members):
                raise core.ScenarioError(
                    f"{gid}.members must be unique"
                )
            if central in members:
                raise core.ScenarioError(
                    f"{gid}: central person cannot be household member"
                )
            unknown = [pid for pid in members if pid not in node_ids]
            if unknown:
                raise core.ScenarioError(
                    f"{gid}: unknown household members {unknown}"
                )
            overlap = [
                pid for pid in members if pid in member_to_household
            ]
            if overlap:
                raise core.ScenarioError(
                    f"neighbor household membership overlap: {overlap}"
                )
            for pid in members:
                member_to_household[pid] = gid

            households.append({
                "group_id": gid,
                "members": members,
                "household_kind": str(
                    item.get("household_kind", "unspecified")
                ),
            })
    else:
        raw_neighbors = spec.get("neighbor_ids", [])
        if not isinstance(raw_neighbors, list) or not raw_neighbors:
            raise core.ScenarioError(
                "neighbor_ids must be non-empty list when "
                "neighbor_households is absent"
            )
        neighbors = [str(x).strip() for x in raw_neighbors]
        if len(set(neighbors)) != len(neighbors):
            raise core.ScenarioError("neighbor_ids must be unique")
        if central in neighbors:
            raise core.ScenarioError(
                "central person cannot also be neighbor"
            )
        unknown = [pid for pid in neighbors if pid not in node_ids]
        if unknown:
            raise core.ScenarioError(f"unknown neighbor_ids: {unknown}")
        for pid in neighbors:
            gid = f"household:{pid}"
            households.append({
                "group_id": gid,
                "members": [pid],
                "household_kind": "solo",
            })
            member_to_household[pid] = gid

    neighbors = [
        pid
        for household in households
        for pid in household["members"]
    ]
    household_by_id = {
        household["group_id"]: household
        for household in households
    }

    intervention = spec.get("intervention")
    if not isinstance(intervention, dict):
        raise core.ScenarioError("intervention object required")
    intervention_day = _num(
        intervention.get("at_day"),
        "intervention.at_day",
        0.0,
    )
    intervention_id = str(
        intervention.get("id", "external-intervention")
    ).strip() or "external-intervention"

    window_days = _num(
        spec.get("window_days", intervention_day),
        "window_days",
        0.001,
    )
    if intervention_day < window_days:
        raise core.ScenarioError(
            "intervention.at_day must be >= window_days"
        )
    end_day = intervention_day + window_days

    sync_tolerance = _num(
        spec.get("sync_tolerance_days", 0.10),
        "sync_tolerance_days",
        0.0,
    )

    stimuli = spec.get("observed_stimuli", [])
    if not isinstance(stimuli, list):
        raise core.ScenarioError("observed_stimuli must be list")

    compiled = []
    seen_ids = set()
    for idx, item in enumerate(stimuli):
        if not isinstance(item, dict):
            raise core.ScenarioError(
                f"observed_stimuli[{idx}] must be object"
            )
        eid = str(item.get("id", f"stimulus-{idx+1}")).strip()
        if not eid:
            raise core.ScenarioError(
                f"observed_stimuli[{idx}].id required"
            )
        if eid in seen_ids:
            raise core.ScenarioError(f"duplicate stimulus id: {eid}")
        seen_ids.add(eid)

        source = item.get("source_id")
        source_group = item.get(
            "source_group_id",
            item.get("source_household_id"),
        )
        if source is not None and source_group is not None:
            raise core.ScenarioError(
                f"{eid}: use source_id or source_group_id, not both"
            )
        if source is None and source_group is None:
            raise core.ScenarioError(
                f"{eid}: source_id or source_group_id required"
            )

        source_id = None
        if source is not None:
            source_id = str(source).strip()
            if source_id not in member_to_household:
                raise core.ScenarioError(
                    f"{eid}: source_id must be a neighbor household member"
                )
            source_group_id = member_to_household[source_id]
            member_weights = {source_id: 1.0}
        else:
            source_group_id = str(source_group).strip()
            if source_group_id not in household_by_id:
                raise core.ScenarioError(
                    f"{eid}: unknown source_group_id {source_group_id}"
                )
            members = household_by_id[source_group_id]["members"]
            raw_weights = item.get("member_weights")
            if raw_weights is None:
                equal = 1.0 / len(members)
                member_weights = {pid: equal for pid in members}
            else:
                if not isinstance(raw_weights, dict):
                    raise core.ScenarioError(
                        f"{eid}.member_weights must be object"
                    )
                extra = [
                    pid for pid in raw_weights if pid not in members
                ]
                if extra:
                    raise core.ScenarioError(
                        f"{eid}.member_weights contains non-members {extra}"
                    )
                member_weights = {}
                total = 0.0
                for pid in members:
                    weight = _num(
                        raw_weights.get(pid, 0.0),
                        f"{eid}.member_weights.{pid}",
                        0.0,
                    )
                    member_weights[pid] = weight
                    total += weight
                if total <= 0:
                    raise core.ScenarioError(
                        f"{eid}.member_weights total must be > 0"
                    )
                member_weights = {
                    pid: weight / total
                    for pid, weight in member_weights.items()
                }

        at_day = _num(item.get("at_day"), f"{eid}.at_day", 0.0)
        duration = _num(
            item.get("duration_days", 0.05),
            f"{eid}.duration_days",
            0.0001,
        )
        amplitude = _num(
            item.get("amplitude"),
            f"{eid}.amplitude",
            0.0,
        )
        if at_day >= end_day:
            raise core.ScenarioError(
                f"{eid}: at_day outside analysis horizon"
            )
        compiled.append({
            "id": eid,
            "source_id": source_id,
            "source_group_id": source_group_id,
            "member_weights": member_weights,
            "kind": str(item.get("kind", "observed_event")),
            "at_day": at_day,
            "duration_days": duration,
            "amplitude": amplitude,
            "evidence": str(
                item.get("evidence", "contemporaneous_observation")
            ),
        })

    compiled.sort(key=lambda x: (x["at_day"], x["id"]))

    central_memory_relief = _num(
        intervention.get("central_memory_relief", 0.0),
        "intervention.central_memory_relief",
        0.0,
        1.0,
    )
    central_drive_relief = _num(
        intervention.get("central_drive_relief", 0.0),
        "intervention.central_drive_relief",
        0.0,
    )
    relief_duration = _num(
        intervention.get("relief_duration_days", 0.25),
        "intervention.relief_duration_days",
        0.0001,
    )


    return {
        "model_version": VERSION,
        "central_person_id": central,
        "neighbor_ids": neighbors,
        "neighbor_households": households,
        "member_to_household": member_to_household,
        "observed_stimuli": compiled,
        "intervention": {
            "id": intervention_id,
            "at_day": intervention_day,
            "central_memory_relief": central_memory_relief,
            "central_drive_relief": central_drive_relief,
            "relief_duration_days": relief_duration,
        },
        "window_days": window_days,
        "analysis_start_day": intervention_day - window_days,
        "analysis_end_day": end_day,
        "sync_tolerance_days": sync_tolerance,
    }

def timeline_from_spec(compiled, *, include_relief=True, stimuli=None):
    stimuli = (
        compiled["observed_stimuli"]
        if stimuli is None
        else stimuli
    )
    events = []
    for item in stimuli:
        weights = item.get("member_weights") or {
            item["source_id"]: 1.0
        }
        multi = len(weights) > 1
        for pid, weight in weights.items():
            if weight <= 0:
                continue
            events.append({
                "id": (
                    f"{item['id']}::{pid}"
                    if multi
                    else item["id"]
                ),
                "at_day": item["at_day"],
                "duration_days": item["duration_days"],
                "target_person": pid,
                "drive_add": item["amplitude"] * weight,
            })

    intervention = compiled["intervention"]
    if include_relief:
        if intervention["central_memory_relief"] > 0:
            events.append({
                "id": f"{intervention['id']}-memory-relief",
                "at_day": intervention["at_day"],
                "duration_days": 0.0,
                "target_person": compiled["central_person_id"],
                "memory_impulse": -intervention["central_memory_relief"],
            })
        if intervention["central_drive_relief"] > 0:
            events.append({
                "id": f"{intervention['id']}-drive-relief",
                "at_day": intervention["at_day"],
                "duration_days": intervention["relief_duration_days"],
                "target_person": compiled["central_person_id"],
                "drive_add": -intervention["central_drive_relief"],
            })

    return {
        "simulation": {
            "days": compiled["analysis_end_day"],
            "dt_days": 0.01,
            "sample_every_days": 0.05,
        },
        "events": events,
    }


def _window_events(compiled, lo, hi):
    return [
        event for event in compiled["observed_stimuli"]
        if lo <= event["at_day"] < hi
    ]


def _event_source_axis(event):
    return str(
        event.get("source_group_id")
        or event.get("source_id")
        or "unknown"
    )


def temporal_alignment_index(events, neighbor_ids, tolerance_days):
    """Fraction of events aligned with another household/source.

    This is a timing statistic. It does not infer communication or intent.
    """
    if not events:
        return 0.0
    aligned = 0
    for event in events:
        source_axis = _event_source_axis(event)
        hit = any(
            _event_source_axis(other) != source_axis
            and abs(other["at_day"] - event["at_day"]) <= tolerance_days
            for other in events
        )
        if hit:
            aligned += 1
    return aligned / len(events)


def event_metrics(events, neighbor_ids, window_days, tolerance_days):
    household_ids = sorted({
        _event_source_axis(event) for event in events
    })
    by_household = {gid: 0 for gid in household_ids}
    by_member = {pid: 0 for pid in neighbor_ids}
    amplitude_sum = 0.0
    exposure_area = 0.0
    for event in events:
        by_household[_event_source_axis(event)] += 1
        if event.get("source_id") is not None:
            by_member[event["source_id"]] = (
                by_member.get(event["source_id"], 0) + 1
            )
        amplitude_sum += event["amplitude"]
        exposure_area += (
            event["amplitude"] * event["duration_days"]
        )
    return {
        "event_count": len(events),
        "events_per_day": len(events) / window_days,
        "mean_amplitude": (
            amplitude_sum / len(events) if events else 0.0
        ),
        "exposure_area": exposure_area,
        "events_by_household": by_household,
        "events_by_explicit_member": by_member,
        "temporal_alignment_index": temporal_alignment_index(
            events,
            neighbor_ids,
            tolerance_days,
        ),
        "intent_inferred": False,
    }


def continuation_stimuli(compiled):
    """Repeat the pre-intervention window once into the post window."""
    t0 = compiled["intervention"]["at_day"]
    window = compiled["window_days"]
    pre_lo = t0 - window
    pre = _window_events(compiled, pre_lo, t0)
    post_existing = _window_events(compiled, t0, t0 + window)

    carried = []
    for event in pre:
        shifted = copy.deepcopy(event)
        shifted["id"] = f"cf-continuation-{event['id']}"
        shifted["at_day"] = event["at_day"] + window
        carried.append(shifted)

    # Keep the observed pre window, replace only the post window.
    outside_post = [
        event for event in compiled["observed_stimuli"]
        if event["at_day"] < t0
        or event["at_day"] >= t0 + window
    ]
    return sorted(
        outside_post + carried,
        key=lambda x: (x["at_day"], x["id"]),
    )


def desynchronized_pre_stimuli(compiled):
    """Preserve pre-window count/amplitude/duration but spread event times.

    This is a deterministic signal-shape counterfactual, not a claim that
    observed alignment was intentional.
    """
    t0 = compiled["intervention"]["at_day"]
    window = compiled["window_days"]
    lo = t0 - window
    pre = _window_events(compiled, lo, t0)
    if len(pre) <= 1:
        return copy.deepcopy(compiled["observed_stimuli"])

    ordered = sorted(
        pre,
        key=lambda e: (_event_source_axis(e), e["id"]),
    )
    gap = window / (len(ordered) + 1)
    remapped = []
    for idx, event in enumerate(ordered, start=1):
        item = copy.deepcopy(event)
        item["id"] = f"cf-desync-{event['id']}"
        item["at_day"] = lo + idx * gap
        remapped.append(item)

    outside = [
        event for event in compiled["observed_stimuli"]
        if not (lo <= event["at_day"] < t0)
    ]
    return sorted(
        outside + remapped,
        key=lambda x: (x["at_day"], x["id"]),
    )


def _run(scenario, compiled, *, include_relief=True, stimuli=None):
    timeline = timeline_from_spec(
        compiled,
        include_relief=include_relief,
        stimuli=stimuli,
    )
    family = family_safety.assess(scenario, timeline)
    thermal = therm.integrate_thermal(
        scenario,
        family["trajectory"],
    )
    return {
        "timeline": timeline,
        "family": family,
        "thermal": thermal,
    }


def _nearest(rows, day):
    return min(rows, key=lambda row: abs(float(row["day"]) - day))


def central_window_metrics(run, compiled, lo, hi):
    pid = compiled["central_person_id"]
    family_rows = [
        row for row in run["family"]["trajectory"]
        if lo <= float(row["day"]) <= hi
    ]
    thermal_rows = [
        row for row in run["thermal"]
        if lo <= float(row["day"]) <= hi
    ]
    if not family_rows or not thermal_rows:
        raise core.ScenarioError("analysis window has no trajectory rows")

    loads = [
        (float(row["day"]), row["persons"][pid]["accumulated_load"])
        for row in family_rows
    ]
    heats = [
        (float(row["day"]), row["persons"][pid]["heat"])
        for row in thermal_rows
    ]
    debts = [
        (
            float(row["day"]),
            row["persons"][pid]["recovery_debt_heat_days"],
        )
        for row in thermal_rows
    ]

    peak_load = max(loads, key=lambda x: x[1])
    peak_heat = max(heats, key=lambda x: x[1])
    peak_debt = max(debts, key=lambda x: x[1])

    return {
        "peak_accumulated_load": {
            "day": peak_load[0],
            "value": peak_load[1],
        },
        "final_accumulated_load": loads[-1][1],
        "peak_heat": {
            "day": peak_heat[0],
            "value": peak_heat[1],
        },
        "final_heat": heats[-1][1],
        "peak_recovery_debt": {
            "day": peak_debt[0],
            "value": peak_debt[1],
        },
        "final_recovery_debt": debts[-1][1],
    }


def _central_delta_metrics(run, baseline, compiled, lo, hi):
    pid = compiled["central_person_id"]

    family_run = {
        round(float(row["day"]), 10): row
        for row in run["family"]["trajectory"]
        if lo <= float(row["day"]) <= hi
    }
    family_base = {
        round(float(row["day"]), 10): row
        for row in baseline["family"]["trajectory"]
        if lo <= float(row["day"]) <= hi
    }
    thermal_run = {
        round(float(row["day"]), 10): row
        for row in run["thermal"]
        if lo <= float(row["day"]) <= hi
    }
    thermal_base = {
        round(float(row["day"]), 10): row
        for row in baseline["thermal"]
        if lo <= float(row["day"]) <= hi
    }

    shared_days = sorted(set(family_run) & set(family_base))
    shared_thermal_days = sorted(set(thermal_run) & set(thermal_base))
    if not shared_days or not shared_thermal_days:
        raise core.ScenarioError(
            "household probe has no aligned trajectory rows"
        )

    load_delta = [
        (
            day,
            float(family_run[day]["persons"][pid]["accumulated_load"])
            - float(family_base[day]["persons"][pid]["accumulated_load"]),
        )
        for day in shared_days
    ]
    heat_delta = [
        (
            day,
            float(thermal_run[day]["persons"][pid]["heat"])
            - float(thermal_base[day]["persons"][pid]["heat"]),
        )
        for day in shared_thermal_days
    ]

    peak_load = max(load_delta, key=lambda x: abs(x[1]))
    peak_heat = max(heat_delta, key=lambda x: abs(x[1]))

    return {
        "peak_abs_load_delta": {
            "day": peak_load[0],
            "signed_value": peak_load[1],
            "abs_value": abs(peak_load[1]),
        },
        "peak_abs_heat_delta": {
            "day": peak_heat[0],
            "signed_value": peak_heat[1],
            "abs_value": abs(peak_heat[1]),
        },
        "final_load_delta": load_delta[-1][1],
        "final_heat_delta": heat_delta[-1][1],
    }


def household_transfer_probe(scenario, compiled, probe=None):
    probe = probe or {}
    at_day = _num(
        probe.get("at_day", 1.0),
        "household_probe.at_day",
        0.0,
    )
    duration = _num(
        probe.get("duration_days", 0.20),
        "household_probe.duration_days",
        0.0001,
    )
    amplitude = _num(
        probe.get("amplitude", 0.45),
        "household_probe.amplitude",
        0.0,
    )
    measure_days = _num(
        probe.get("measure_window_days", 2.0),
        "household_probe.measure_window_days",
        0.05,
    )
    if at_day + measure_days > compiled["analysis_end_day"]:
        raise core.ScenarioError(
            "household probe window exceeds analysis horizon"
        )

    baseline = _run(
        scenario,
        compiled,
        include_relief=False,
        stimuli=[],
    )
    out = {}

    for household in compiled["neighbor_households"]:
        gid = household["group_id"]
        members = household["members"]
        equal = 1.0 / len(members)
        stimulus = {
            "id": f"household-probe::{gid}",
            "source_id": None,
            "source_group_id": gid,
            "member_weights": {
                pid: equal for pid in members
            },
            "kind": "household_transfer_probe",
            "at_day": at_day,
            "duration_days": duration,
            "amplitude": amplitude,
            "evidence": "synthetic_probe",
        }
        run = _run(
            scenario,
            compiled,
            include_relief=False,
            stimuli=[stimulus],
        )
        out[gid] = {
            "household_kind": household["household_kind"],
            "members": list(members),
            "member_count": len(members),
            "total_input_amplitude": amplitude,
            "total_input_exposure_area": amplitude * duration,
            "member_weights": stimulus["member_weights"],
            "central_response_delta": _central_delta_metrics(
                run,
                baseline,
                compiled,
                at_day,
                at_day + measure_days,
            ),
        }

    ranking = sorted(
        out,
        key=lambda gid: out[gid]["central_response_delta"][
            "peak_abs_load_delta"
        ]["abs_value"],
        reverse=True,
    )

    return {
        "probe": {
            "at_day": at_day,
            "duration_days": duration,
            "amplitude": amplitude,
            "measure_window_days": measure_days,
            "equal_total_input_across_households": True,
        },
        "households": out,
        "central_peak_load_delta_ranking": ranking,
        "ranking_is_descriptive_not_causal": True,
    }


def analyze(scenario, spec):
    compiled = compile_spec(scenario, spec)
    t0 = compiled["intervention"]["at_day"]
    window = compiled["window_days"]
    pre_lo = t0 - window
    post_hi = t0 + window

    pre_events = _window_events(compiled, pre_lo, t0)
    post_events = _window_events(compiled, t0, post_hi)

    actual = _run(scenario, compiled, include_relief=True)
    no_relief = _run(scenario, compiled, include_relief=False)
    continuation = _run(
        scenario,
        compiled,
        include_relief=True,
        stimuli=continuation_stimuli(compiled),
    )
    desync = _run(
        scenario,
        compiled,
        include_relief=True,
        stimuli=desynchronized_pre_stimuli(compiled),
    )

    actual_pre = central_window_metrics(
        actual, compiled, pre_lo, t0
    )
    actual_post = central_window_metrics(
        actual, compiled, t0, post_hi
    )
    no_relief_post = central_window_metrics(
        no_relief, compiled, t0, post_hi
    )
    continuation_post = central_window_metrics(
        continuation, compiled, t0, post_hi
    )
    actual_pre_desync = central_window_metrics(
        desync, compiled, pre_lo, t0
    )

    household_probe = household_transfer_probe(
        scenario,
        compiled,
        spec.get("household_probe"),
    )

    no_internal = copy.deepcopy(scenario)
    no_internal["связи_персонажей"] = [
        link
        for link in no_internal.get("связи_персонажей", [])
        if link.get("channel_kind") != "household_internal"
    ]
    household_probe_no_internal = household_transfer_probe(
        no_internal,
        compiled,
        spec.get("household_probe"),
    )

    topology_effect = {}
    for gid, item in household_probe["households"].items():
        coupled_peak = item["central_response_delta"][
            "peak_abs_load_delta"
        ]["abs_value"]
        uncoupled_peak = household_probe_no_internal["households"][gid][
            "central_response_delta"
        ]["peak_abs_load_delta"]["abs_value"]
        topology_effect[gid] = {
            "with_internal_links_peak_abs_load_delta": coupled_peak,
            "without_internal_links_peak_abs_load_delta": uncoupled_peak,
            "difference": coupled_peak - uncoupled_peak,
        }

    no_cross = copy.deepcopy(scenario)
    no_cross["связи_персонажей"] = [
        link
        for link in no_cross.get("связи_персонажей", [])
        if link.get("channel_kind") != "cross_household_social"
    ]
    no_cross_run = _run(
        no_cross,
        compiled,
        include_relief=True,
    )
    no_cross_pre = central_window_metrics(
        no_cross_run,
        compiled,
        pre_lo,
        t0,
    )
    cross_household_social_effect = {
        "with_cross_household_links_peak_load": actual_pre[
            "peak_accumulated_load"
        ]["value"],
        "without_cross_household_links_peak_load": no_cross_pre[
            "peak_accumulated_load"
        ]["value"],
        "difference": (
            actual_pre["peak_accumulated_load"]["value"]
            - no_cross_pre["peak_accumulated_load"]["value"]
        ),
        "direction_precommitted": False,
    }

    return {
        "model_version": VERSION,
        "central_person_id": compiled["central_person_id"],
        "neighbor_ids": compiled["neighbor_ids"],
        "neighbor_households": compiled["neighbor_households"],
        "intervention": compiled["intervention"],
        "event_windows": {
            "pre": event_metrics(
                pre_events,
                compiled["neighbor_ids"],
                window,
                compiled["sync_tolerance_days"],
            ),
            "post": event_metrics(
                post_events,
                compiled["neighbor_ids"],
                window,
                compiled["sync_tolerance_days"],
            ),
        },
        "central_response": {
            "pre_actual": actual_pre,
            "post_actual": actual_post,
            "post_no_relief_counterfactual": no_relief_post,
            "post_prepattern_continuation_counterfactual": continuation_post,
            "pre_desynchronized_counterfactual": actual_pre_desync,
        },
        "household_transfer_probe": household_probe,
        "household_transfer_probe_without_internal_links": (
            household_probe_no_internal
        ),
        "household_topology_effect": topology_effect,
        "cross_household_social_effect": cross_household_social_effect,
        "comparisons": {
            "observed_post_vs_pre_event_rate_ratio": (
                len(post_events) / len(pre_events)
                if pre_events else None
            ),
            "observed_post_vs_pre_exposure_ratio": (
                event_metrics(
                    post_events,
                    compiled["neighbor_ids"],
                    window,
                    compiled["sync_tolerance_days"],
                )["exposure_area"]
                / event_metrics(
                    pre_events,
                    compiled["neighbor_ids"],
                    window,
                    compiled["sync_tolerance_days"],
                )["exposure_area"]
                if pre_events
                and event_metrics(
                    pre_events,
                    compiled["neighbor_ids"],
                    window,
                    compiled["sync_tolerance_days"],
                )["exposure_area"] > 0
                else None
            ),
            "support_relief_association": {
                "actual_final_load": actual_post[
                    "final_accumulated_load"
                ],
                "same_stimuli_without_relief_final_load": no_relief_post[
                    "final_accumulated_load"
                ],
            },
            "post_regime_association": {
                "actual_final_load": actual_post[
                    "final_accumulated_load"
                ],
                "continued_prepattern_final_load": continuation_post[
                    "final_accumulated_load"
                ],
            },
            "timing_alignment_effect": {
                "actual_pre_peak_load": actual_pre[
                    "peak_accumulated_load"
                ]["value"],
                "desynchronized_pre_peak_load": actual_pre_desync[
                    "peak_accumulated_load"
                ]["value"],
            },
        },
        "causal_boundary": (
            "Before/after differences and counterfactual model differences "
            "do not establish intent or prove that the external intervention "
            "caused neighbors to change behavior. The model records timing, "
            "observed-event regimes, and explicitly declared relief effects."
        ),
        "intent_inferred": False,
    }


def main():
    import argparse

    p = argparse.ArgumentParser(description="Run NEIGHBOR-NET1 analysis")
    p.add_argument("scenario")
    p.add_argument("spec")
    args = p.parse_args()

    scenario = json.loads(
        Path(args.scenario).read_text(encoding="utf-8")
    )
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    print(json.dumps(analyze(scenario, spec), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
