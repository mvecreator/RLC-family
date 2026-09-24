#!/usr/bin/env python3
"""PERSON-TIME2: event-driven dynamic solver for PERSON2 networks."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

try:
    from simulator import person_model as pm
    from simulator import person_network_solver as pnet
    from simulator import rlc_family_sim as core
    from simulator import time_solver as legacy_time
except ModuleNotFoundError:
    import person_model as pm
    import person_network_solver as pnet
    import rlc_family_sim as core
    import time_solver as legacy_time

VERSION = "RLC-FAMILY-PERSON-TIME2-0.1"
DAYS_PER_MONTH = legacy_time.DAYS_PER_MONTH


def _load_json(path):
    if str(path) == "-":
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as e:
        raise core.ScenarioError(str(e)) from e
    if not isinstance(value, dict):
        raise core.ScenarioError("timeline root must be object")
    return value


def _source_weights(scenario, nodes):
    raw = {
        str(p.get("id")): p
        for p in scenario.get("персонажи", [])
        if isinstance(p, dict)
    }
    weights = []
    for node in nodes:
        item = raw.get(node["id"], {})
        weights.append(core.nonneg(item.get("source_weight", 1.0), f"{node['id']}.source_weight"))
    total = sum(weights)
    if total <= 0:
        raise core.ScenarioError("at least one PERSON2 source_weight must be > 0")
    return {node["id"]: w / total for node, w in zip(nodes, weights)}


def _compile_events(spec, node_ids, link_keys):
    raw = spec.get("события", spec.get("events", []))
    if not isinstance(raw, list):
        raise core.ScenarioError("события must be list")
    out = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise core.ScenarioError(f"event {idx}: expected object")
        start = core.nonneg(item.get("день", item.get("at_day", 0)), f"event {idx}.day")
        duration = core.nonneg(item.get("длительность_дней", item.get("duration_days", 0)), f"event {idx}.duration")
        target_person = item.get("target_person", item.get("персонаж"))
        if target_person is not None:
            target_person = str(target_person)
            if target_person not in node_ids:
                raise core.ScenarioError(f"event {idx}: unknown person {target_person}")
        target_link = item.get("target_link", item.get("связь"))
        link_tuple = None
        if target_link is not None:
            if isinstance(target_link, str):
                parts = target_link.replace("->", ":").replace("-", ":").split(":")
                parts = [x.strip() for x in parts if x.strip()]
            elif isinstance(target_link, list):
                parts = [str(x).strip() for x in target_link]
            else:
                raise core.ScenarioError(f"event {idx}: target_link must be string/list")
            if len(parts) != 2:
                raise core.ScenarioError(f"event {idx}: target_link needs two ids")
            link_tuple = tuple(sorted(parts))
            if link_tuple not in link_keys:
                raise core.ScenarioError(f"event {idx}: unknown link {parts}")
        if float(item.get("memory_impulse", item.get("импульс_памяти", 0.0))) != 0 and target_person is None:
            raise core.ScenarioError(
                f"event {idx}: memory impulse requires target_person"
            )
        out.append({
            "id": str(item.get("id", f"event-{idx+1}")),
            "label": str(item.get("описание", item.get("label", item.get("id", f"Событие {idx+1}")))),
            "start": start,
            "end": start + duration,
            "duration": duration,
            "target_person": target_person,
            "target_link": link_tuple,
            "drive_add": float(item.get("drive_add", item.get("добавить_возбуждение", 0.0))),
            "drive_set": item.get("drive_set", item.get("установить_возбуждение")),
            "memory_impulse": float(item.get("memory_impulse", item.get("импульс_памяти", 0.0))),
            "money_impulse": float(item.get("money_impulse", item.get("денежный_импульс", 0.0))),
            "link_quality_set": item.get("link_quality_set", item.get("качество_связи")),
            "link_quality_add": float(item.get("link_quality_add", item.get("изменить_качество_связи", 0.0))),
        })
    out.sort(key=lambda e: (e["start"], e["id"]))
    return out


def _active(event, t):
    return event["duration"] > 0 and event["start"] <= t < event["end"]


def _finance_state(scenario, reserve):
    ir = core.compile_scenario(scenario)
    stress, income, load = legacy_time._financial_stress(ir, reserve)
    return ir["finance"], stress, income, load


def _network_at(base_scenario, base_ir, events, t):
    nodes = copy.deepcopy(base_ir["nodes"])
    links = copy.deepcopy(base_ir["links"])
    node_by = {n["id"]: n for n in nodes}
    link_by = {tuple(sorted((x["from"], x["to"]))): x for x in links}
    person_drive = {n["id"]: 0.0 for n in nodes}

    for event in events:
        if not _active(event, t):
            continue
        pid = event["target_person"]
        if pid is not None:
            if event["drive_set"] is not None:
                person_drive[pid] = float(event["drive_set"])
            person_drive[pid] += event["drive_add"]
        key = event["target_link"]
        if key is not None:
            link = link_by[key]
            q = link["quality"]
            if event["link_quality_set"] is not None:
                q = float(event["link_quality_set"])
            q += event["link_quality_add"]
            q = pm.clip(q, 0.0, 1.0)
            link["quality"] = q
            link["R_link"] = pm.link_resistance(q)
    return nodes, links, person_drive


def _unpack(state, n):
    v = state[:n]
    il = state[n:2*n]
    mem = state[2*n:3*n]
    reserve = state[-2]
    debt = state[-1]
    return v, il, mem, reserve, debt


def _pack(v, il, mem, reserve, debt):
    return tuple(v) + tuple(il) + tuple(mem) + (reserve, debt)


def derivatives(t, state, scenario, base_ir, events, cfg, shares):
    n = len(base_ir["nodes"])
    v, il, mem, reserve, debt = _unpack(state, n)
    nodes, links, person_drive = _network_at(scenario, base_ir, events, t)
    index = {node["id"]: i for i, node in enumerate(nodes)}

    finance, fin_stress, income, load = _finance_state(scenario, reserve)
    global_ir = core.compile_scenario(scenario)
    global_drive = global_ir["analysis"]["total_drive_voltage"]
    financial_drive_gain = float(cfg.get("financial_drive_gain", 0.20))
    global_drive *= 1.0 + financial_drive_gain * fin_stress

    coupling = [0.0 for _ in range(n)]
    link_currents = []
    for link in links:
        i = index[link["from"]]
        j = index[link["to"]]
        current = (v[i] - v[j]) / link["R_link"]
        coupling[i] += current
        coupling[j] -= current
        link_currents.append((link, current))

    dv = []
    dil = []
    dmem = []
    for i, node in enumerate(nodes):
        source = global_drive * shares[node["id"]] + person_drive[node["id"]]
        dv_i = (
            source
            - v[i] / node["R"]
            - il[i]
            - coupling[i]
        ) / node["C"]
        dil_i = v[i] / node["L"]

        local_flow = 0.0
        poor_link_stress = 0.0
        for link, current in link_currents:
            if node["id"] not in (link["from"], link["to"]):
                continue
            local_flow += abs(current)
            poor_link_stress += (1.0 - link["quality"]) * abs(current)

        recovery = 0.5
        raw = next(
            (p for p in scenario.get("персонажи", []) if str(p.get("id")) == node["id"]),
            {},
        )
        role = raw.get("role") or {}
        recovery = float(raw.get("recovery_inertia", role.get("recovery_inertia", 0.5)))

        excitation_gain = float(cfg.get("person_excitation_memory_gain", 0.035))
        flow_gain = float(cfg.get("person_link_flow_memory_gain", 0.010))
        poor_gain = float(cfg.get("person_poor_link_memory_gain", 0.060))
        finance_gain = float(cfg.get("person_financial_memory_gain", 0.018))
        decay = float(cfg.get("person_memory_decay", 0.040))
        recovery_gain = float(cfg.get("person_recovery_relax", 0.025))

        dmem_i = (
            excitation_gain * abs(v[i])
            + flow_gain * local_flow
            + poor_gain * poor_link_stress
            + finance_gain * fin_stress
            - decay * mem[i]
            - recovery_gain * (1.0 - recovery) * mem[i]
        )

        dv.append(dv_i)
        dil.append(dil_i)
        dmem.append(dmem_i)

    dreserve = (income - load) / DAYS_PER_MONTH
    daily_rate = finance["annual_rate"] / 365.2425
    mortgage_daily = finance["mortgage"] / DAYS_PER_MONTH
    ddebt = daily_rate * debt - mortgage_daily if debt > 0 else 0.0
    if debt <= 0 and ddebt < 0:
        ddebt = 0.0

    return _pack(dv, dil, dmem, dreserve, ddebt)


def _rk4(t, state, dt, scenario, base_ir, events, cfg, shares):
    def add(a, b, scale):
        return tuple(x + scale*y for x, y in zip(a, b))
    k1 = derivatives(t, state, scenario, base_ir, events, cfg, shares)
    k2 = derivatives(t + dt/2, add(state, k1, dt/2), scenario, base_ir, events, cfg, shares)
    k3 = derivatives(t + dt/2, add(state, k2, dt/2), scenario, base_ir, events, cfg, shares)
    k4 = derivatives(t + dt, add(state, k3, dt), scenario, base_ir, events, cfg, shares)
    out = tuple(
        x + dt * (a + 2*b + 2*c + d) / 6
        for x, a, b, c, d in zip(state, k1, k2, k3, k4)
    )
    n = len(base_ir["nodes"])
    v, il, mem, reserve, debt = _unpack(out, n)
    mem = [pm.clip(x, 0.0, 1.0) for x in mem]
    return _pack(v, il, mem, reserve, max(0.0, debt))


def _apply_impulses(state, t0, events, node_index):
    n = len(node_index)
    v, il, mem, reserve, debt = _unpack(state, n)
    mem = list(mem)
    for event in events:
        if abs(event["start"] - t0) > 1e-9:
            continue
        reserve += event["money_impulse"]
        if event["target_person"] is not None and event["memory_impulse"]:
            i = node_index[event["target_person"]]
            mem[i] = pm.clip(mem[i] + event["memory_impulse"], 0.0, 1.0)
    return _pack(v, il, mem, reserve, debt)


def _sample(t, state, scenario, base_ir, events, cfg):
    n = len(base_ir["nodes"])
    v, il, mem, reserve, debt = _unpack(state, n)
    nodes, links, person_drive = _network_at(scenario, base_ir, events, t)
    index = {node["id"]: i for i, node in enumerate(nodes)}
    finance, fin_stress, income, load = _finance_state(scenario, reserve)

    node_rows = []
    for i, node in enumerate(nodes):
        node_rows.append({
            "id": node["id"],
            "voltage": v[i],
            "inductor_current": il[i],
            "memory": mem[i],
            "R": node["R"],
            "C": node["C"],
            "L": node["L"],
            "event_drive": person_drive[node["id"]],
        })

    link_rows = []
    for link in links:
        i = index[link["from"]]
        j = index[link["to"]]
        current = (v[i] - v[j]) / link["R_link"]
        link_rows.append({
            "from": link["from"],
            "to": link["to"],
            "quality": link["quality"],
            "R_link": link["R_link"],
            "current": current,
            "current_abs": abs(current),
        })

    return {
        "day": round(t, 8),
        "nodes": node_rows,
        "links": link_rows,
        "reserve": reserve,
        "mortgage_debt": debt,
        "financial_stress": fin_stress,
        "monthly_income_equivalent": income,
        "monthly_load_equivalent": load,
        "active_events": [e["id"] for e in events if _active(e, t)],
    }


def summarize(samples, node_ids):
    by_person = {}
    for pid in node_ids:
        series = []
        for sample in samples:
            row = next(x for x in sample["nodes"] if x["id"] == pid)
            series.append((sample["day"], row))
        peak_v = max(series, key=lambda x: abs(x[1]["voltage"]))
        peak_m = max(series, key=lambda x: x[1]["memory"])
        by_person[pid] = {
            "peak_voltage": peak_v[1]["voltage"],
            "peak_voltage_abs": abs(peak_v[1]["voltage"]),
            "peak_voltage_day": peak_v[0],
            "peak_memory": peak_m[1]["memory"],
            "peak_memory_day": peak_m[0],
            "final_memory": series[-1][1]["memory"],
            "final_voltage": series[-1][1]["voltage"],
        }

    link_series = {}
    for sample in samples:
        for link in sample["links"]:
            key = f"{link['from']}->{link['to']}"
            link_series.setdefault(key, []).append((sample["day"], link))
    by_link = {}
    for key, rows in link_series.items():
        peak = max(rows, key=lambda x: x[1]["current_abs"])
        by_link[key] = {
            "peak_current": peak[1]["current"],
            "peak_current_abs": peak[1]["current_abs"],
            "peak_day": peak[0],
            "quality_at_peak": peak[1]["quality"],
        }

    strongest = max(
        by_link.items(), key=lambda kv: kv[1]["peak_current_abs"]
    ) if by_link else (None, {"peak_current_abs": 0.0, "peak_day": 0.0})

    return {
        "persons": by_person,
        "links": by_link,
        "strongest_link": strongest[0],
        "strongest_link_peak": strongest[1]["peak_current_abs"],
        "strongest_link_peak_day": strongest[1]["peak_day"],
        "final_reserve": samples[-1]["reserve"],
        "final_mortgage_debt": samples[-1]["mortgage_debt"],
        "peak_financial_stress": max(x["financial_stress"] for x in samples),
    }


def interpret(summary):
    out = []
    if summary["persons"]:
        max_person = max(
            summary["persons"].items(),
            key=lambda kv: kv[1]["peak_voltage_abs"],
        )
        out.append(
            f"Максимальное локальное возбуждение пришлось на {max_person[0]} "
            f"(peak |v|={max_person[1]['peak_voltage_abs']:.4f})."
        )
        mem_person = max(
            summary["persons"].items(),
            key=lambda kv: kv[1]["final_memory"],
        )
        out.append(
            f"К концу окна наибольшая память у {mem_person[0]} "
            f"({mem_person[1]['final_memory']:.3f})."
        )
    if summary["strongest_link"]:
        out.append(
            f"Наибольший динамический ток связи прошёл по каналу "
            f"{summary['strongest_link']}."
        )
    return out


def simulate_person_timeline(scenario, timeline):
    base_ir = pm.compile_person_network(scenario)
    if base_ir["mode"] != "PERSON2":
        raise core.ScenarioError("PERSON-TIME2 requires персонажи")
    cfg = timeline.get("моделирование", timeline.get("simulation", {}))
    if not isinstance(cfg, dict):
        raise core.ScenarioError("моделирование must be object")
    days = core.positive(cfg.get("дней", cfg.get("days", 7)), "days")
    dt = core.positive(cfg.get("шаг_дней", cfg.get("dt_days", 0.01)), "dt_days")
    sample_every = core.positive(
        cfg.get("выборка_дней", cfg.get("sample_every_days", 0.05)),
        "sample_every_days",
    )
    if dt > 0.10:
        raise core.ScenarioError("PERSON-TIME2 dt_days must be <= 0.10")
    steps = int(math.ceil(days / dt))
    if steps > 250000:
        raise core.ScenarioError("PERSON-TIME2 timeline too large")

    node_ids = [n["id"] for n in base_ir["nodes"]]
    link_keys = {
        tuple(sorted((x["from"], x["to"])))
        for x in base_ir["links"]
    }
    events = _compile_events(timeline, set(node_ids), link_keys)
    shares = _source_weights(scenario, base_ir["nodes"])
    index = {pid: i for i, pid in enumerate(node_ids)}

    global_ir = core.compile_scenario(scenario)
    finance = global_ir["finance"]
    base_fin_stress, _, _ = legacy_time._financial_stress(
        global_ir, finance["reserve"]
    )
    financial_drive_gain = float(cfg.get("financial_drive_gain", 0.20))
    base_drive = global_ir["analysis"]["total_drive_voltage"] * (
        1.0 + financial_drive_gain * base_fin_stress
    )

    # Start from a constant-input equilibrium of the parallel PERSON2 nodes:
    # v_p = 0 and i_L,p carries the baseline injected current. This avoids
    # treating the frequency-domain PERSON-NET1 phasor as a time-domain state.
    v0 = [0.0 for _ in node_ids]
    il0 = [base_drive * shares[pid] for pid in node_ids]
    base_memory = float(
        scenario.get("отношения", {}).get("накопленная_память", 0.2)
    )
    raw_persons = {
        str(p.get("id")): p
        for p in scenario.get("персонажи", [])
        if isinstance(p, dict)
    }
    mem0 = [
        pm.clip(
            float(raw_persons.get(pid, {}).get("initial_memory", base_memory)),
            0.0,
            1.0,
        )
        for pid in node_ids
    ]
    state = _pack(v0, il0, mem0, finance["reserve"], finance["debt"])
    state = _apply_impulses(state, 0.0, events, index)

    samples = [_sample(0.0, state, scenario, base_ir, events, cfg)]
    applied_times = {0.0}
    next_sample = sample_every
    t = 0.0
    for _ in range(steps):
        step = min(dt, days - t)
        if step <= 0:
            break
        t_next = t + step
        state = _rk4(t, state, step, scenario, base_ir, events, cfg, shares)
        for event in events:
            et = event["start"]
            if et in applied_times:
                continue
            if t < et <= t_next + 1e-12:
                state = _apply_impulses(state, et, events, index)
                applied_times.add(et)
        t = t_next
        if t + 1e-12 >= next_sample or t + 1e-12 >= days:
            samples.append(_sample(t, state, scenario, base_ir, events, cfg))
            while next_sample <= t + 1e-12:
                next_sample += sample_every

    summary = summarize(samples, node_ids)
    return {
        "model_version": VERSION,
        "scenario_name": scenario.get("название", "PERSON2 family"),
        "equations": [
            "C_p dv_p/dt = u_p(t) - v_p/R_p - i_L,p - sum((v_p-v_q)/R_pq)",
            "L_p di_L,p/dt = v_p",
            "dm_p/dt = local_excitation + link_stress + financial_stress - recovery",
            "dReserve/dt = (income-load)/days_per_month + impulses",
            "dDebt/dt = annual_rate/365*Debt - mortgage/days_per_month",
        ],
        "integration": {
            "method": "RK4",
            "days": days,
            "dt_days": dt,
            "sample_every_days": sample_every,
            "steps": steps,
        },
        "events": events,
        "samples": samples,
        "summary": summary,
        "family_interpretation": interpret(summary),
    }


def report(result):
    s = result["summary"]
    lines = "\n".join("- " + x for x in result["family_interpretation"])
    person_rows = "\n".join(
        f"| {pid} | {row['peak_voltage_abs']:.5f} | {row['peak_voltage_day']:.3f} | "
        f"{row['peak_memory']:.4f} | {row['final_memory']:.4f} |"
        for pid, row in s["persons"].items()
    )
    return f"""# PERSON-TIME2 report

**Сценарий:** {result['scenario_name']}

## Интерпретация

{lines}

## Персонажи

| person | peak |v| | peak day | peak memory | final memory |
|---|---:|---:|---:|---:|
{person_rows}

## Сеть

- Strongest link: {s['strongest_link']}
- Peak link current: {s['strongest_link_peak']:.6f}
- Peak financial stress: {s['peak_financial_stress']:.4f}
- Final reserve: {s['final_reserve']:.2f}
- Final debt: {s['final_mortgage_debt']:.2f}

> PERSON-TIME2 — нормализованная сатирическая модель, а не психологический или семейный диагноз.
"""


def write_outputs(out, result):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "person_timeline_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "person_timeline_report.md").write_text(report(result), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="PERSON-TIME2 dynamic PERSON2 network solver")
    p.add_argument("scenario")
    p.add_argument("timeline", help="Timeline JSON or '-' for stdin")
    p.add_argument("--out", type=Path, default=Path("out/person-time"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    scenario = core.load(args.scenario)
    timeline = _load_json(args.timeline)
    result = simulate_person_timeline(scenario, timeline)
    write_outputs(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else report(result))


if __name__ == "__main__":
    main()
