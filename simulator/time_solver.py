#!/usr/bin/env python3
"""SIM-TIME1: event-driven time-domain solver for RLC-family.

Compiled chat timeline -> dynamic RLCM state equations -> trajectory -> summary.
This remains a satirical systems model, not a psychological/financial predictor.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

try:
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import rlc_family_sim as core

VERSION = "RLC-FAMILY-TIME-0.1"
DAYS_PER_MONTH = 365.2425 / 12.0


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
        raise core.ScenarioError("timeline root must be an object")
    return value


def _get(obj, path, default=None):
    cur = obj
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _set(obj, path, value):
    cur = obj
    parts = path.split(".")
    for key in parts[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _compile_events(spec):
    raw = spec.get("события", spec.get("events", []))
    if not isinstance(raw, list):
        raise core.ScenarioError("события must be a list")
    events = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise core.ScenarioError(f"event {idx}: expected object")
        start = core.nonneg(item.get("день", item.get("at_day", 0)), f"event {idx}.день")
        duration = core.nonneg(item.get("длительность_дней", item.get("duration_days", 0)), f"event {idx}.длительность")
        set_values = item.get("установить", item.get("set", {}))
        add_values = item.get("добавить", item.get("add", {}))
        if not isinstance(set_values, dict) or not isinstance(add_values, dict):
            raise core.ScenarioError(f"event {idx}: set/add must be objects")
        events.append({
            "id": str(item.get("id", f"event-{idx+1}")),
            "label": str(item.get("описание", item.get("label", item.get("id", f"Событие {idx+1}")))),
            "start": start,
            "end": start + duration,
            "duration": duration,
            "set": set_values,
            "add": add_values,
            "money_impulse": float(item.get("денежный_импульс", item.get("money_impulse", 0))),
            "memory_impulse": float(item.get("импульс_памяти", item.get("memory_impulse", 0))),
        })
    events.sort(key=lambda e: (e["start"], e["id"]))
    return events


def _event_active(event, t):
    return event["duration"] > 0 and event["start"] <= t < event["end"]


def scenario_at(base, events, t, memory):
    s = copy.deepcopy(base)
    s.setdefault("отношения", {})["накопленная_память"] = max(0.0, min(1.0, memory))
    for event in events:
        if not _event_active(event, t):
            continue
        for path, value in event["set"].items():
            _set(s, path, value)
        for path, delta in event["add"].items():
            old = _get(s, path)
            if old is None:
                raise core.ScenarioError(f"event {event['id']}: cannot add to missing path {path}")
            _set(s, path, float(old) + float(delta))
    return s


def _coefficients(scenario):
    ir = core.compile_scenario(scenario)
    R = core.cv(ir, "R_CHILD") + core.cv(ir, "R_CHANNEL") + core.cv(ir, "R_RAD")
    return {
        "ir": ir,
        "R": R,
        "L": core.cv(ir, "L_WOMAN"),
        "C": core.cv(ir, "C_MAN"),
        "Rrad": core.cv(ir, "R_RAD"),
        "drive": ir["analysis"]["total_drive_voltage"],
        "amp": core.cv(ir, "GAIN"),
    }


def _photo_income(ir):
    f = ir["finance"]
    eff = f["light"] * f["coupling"] * (1 - f["loss"])
    return min(f["market"], f["market"] * eff * f["gain"])


def derivatives(t, state, base, events, cfg):
    q, current, memory, reserve, debt = state
    s = scenario_at(base, events, t, memory)
    k = _coefficients(s)
    ir = k["ir"]

    dq = current
    di = (k["drive"] - k["R"] * current - q / k["C"]) / k["L"]

    p_rad = (current * current) * k["Rrad"]
    quality = float(s.get("связь", {}).get("качество_проводника", 0.70))
    tension = float(s.get("отношения", {}).get("напряженность", 0.50))
    nonlinearity = float(s.get("отношения", {}).get("подростковая_нелинейность", 0.0))

    mem_gain = float(cfg.get("memory_gain", 0.040))
    current_gain = float(cfg.get("current_memory_gain", 0.020))
    channel_stress_gain = float(cfg.get("channel_stress_gain", 0.055))
    nonlinear_memory_gain = float(cfg.get("nonlinear_memory_gain", 0.035))
    memory_decay = float(cfg.get("memory_decay_per_day", 0.030))
    communication_relax = float(cfg.get("communication_memory_relax", 0.025))
    dump_relax = float(cfg.get("dump_memory_relax", 0.080))

    excitation = max(0.0, abs(k["drive"]) - 0.35)
    channel_stress = (1.0 - quality) * tension
    nonlinear_stress = nonlinearity * max(0.0, tension - 0.55)

    dm = (
        mem_gain * excitation
        + current_gain * abs(current)
        + channel_stress_gain * channel_stress
        + nonlinear_memory_gain * nonlinear_stress
        - memory_decay * memory
        - communication_relax * quality * memory
        - dump_relax * p_rad
    )

    f = ir["finance"]
    monthly_income = f["income"] + _photo_income(ir)
    monthly_load = f["mortgage"] + f["base"] + f["other"]
    dreserve = (monthly_income - monthly_load) / DAYS_PER_MONTH

    daily_rate = f["annual_rate"] / 365.2425
    mortgage_daily = f["mortgage"] / DAYS_PER_MONTH
    ddebt = daily_rate * debt - mortgage_daily if debt > 0 else 0.0
    if debt <= 0 and ddebt < 0:
        ddebt = 0.0

    return (dq, di, dm, dreserve, ddebt), k


def _rk4_step(t, state, dt, base, events, cfg):
    def add(a, b, scale):
        return tuple(x + scale * y for x, y in zip(a, b))

    k1, _ = derivatives(t, state, base, events, cfg)
    k2, _ = derivatives(t + dt/2, add(state, k1, dt/2), base, events, cfg)
    k3, _ = derivatives(t + dt/2, add(state, k2, dt/2), base, events, cfg)
    k4, _ = derivatives(t + dt, add(state, k3, dt), base, events, cfg)
    out = tuple(
        x + dt * (a + 2*b + 2*c + d) / 6
        for x, a, b, c, d in zip(state, k1, k2, k3, k4)
    )
    q, current, memory, reserve, debt = out
    return (q, current, max(0.0, min(1.0, memory)), reserve, max(0.0, debt))


def _event_impulses(events):
    by_time = {}
    for e in events:
        if e["money_impulse"] or e["memory_impulse"]:
            by_time.setdefault(e["start"], []).append(e)
    return by_time


def _apply_impulses(state, items):
    q, current, memory, reserve, debt = state
    for e in items:
        reserve += e["money_impulse"]
        memory = max(0.0, min(1.0, memory + e["memory_impulse"]))
    return q, current, memory, reserve, debt


def _sample(t, state, base, events):
    q, current, memory, reserve, debt = state
    s = scenario_at(base, events, t, memory)
    k = _coefficients(s)
    R, L, C = k["R"], k["L"], k["C"]
    omega = k["ir"]["analysis"]["omega_rad_s"]
    reactance = omega * L - 1 / (omega * C)
    phase = -math.degrees(math.atan2(reactance, R))
    p_rad = current * current * k["Rrad"]
    f = k["ir"]["finance"]
    monthly_income = f["income"] + _photo_income(k["ir"])
    monthly_load = f["mortgage"] + f["base"] + f["other"]
    return {
        "day": round(t, 8),
        "charge": q,
        "interaction_current": current,
        "memory": memory,
        "reserve": reserve,
        "mortgage_debt": debt,
        "drive": k["drive"],
        "R": R,
        "L": L,
        "C": C,
        "phase_deg": phase,
        "radiated_power": p_rad,
        "monthly_income_equivalent": monthly_income,
        "monthly_load_equivalent": monthly_load,
        "active_events": [e["id"] for e in events if _event_active(e, t)],
    }


def _crossing_recovery(samples, peak_index, key, fraction=0.5):
    peak = abs(samples[peak_index][key])
    target = peak * fraction
    for row in samples[peak_index+1:]:
        if abs(row[key]) <= target:
            return row["day"] - samples[peak_index]["day"]
    return None


def summarize(samples, events):
    if not samples:
        return {}
    peak_i_idx = max(range(len(samples)), key=lambda i: abs(samples[i]["interaction_current"]))
    peak_m_idx = max(range(len(samples)), key=lambda i: samples[i]["memory"])
    min_res_idx = min(range(len(samples)), key=lambda i: samples[i]["reserve"])
    final = samples[-1]
    recovery = _crossing_recovery(samples, peak_i_idx, "interaction_current")
    return {
        "peak_interaction_current": samples[peak_i_idx]["interaction_current"],
        "peak_interaction_day": samples[peak_i_idx]["day"],
        "half_recovery_days_after_peak": recovery,
        "peak_memory": samples[peak_m_idx]["memory"],
        "peak_memory_day": samples[peak_m_idx]["day"],
        "minimum_reserve": samples[min_res_idx]["reserve"],
        "minimum_reserve_day": samples[min_res_idx]["day"],
        "final_memory": final["memory"],
        "final_reserve": final["reserve"],
        "final_mortgage_debt": final["mortgage_debt"],
        "event_count": len(events),
    }


def interpret(summary):
    out = []
    peak = abs(summary["peak_interaction_current"])
    if peak < 0.05:
        out.append("Даже в пике динамический ток мал: события слабо раскачивают семейную цепь.")
    elif peak < 0.20:
        out.append("События создают заметный, но не экстремальный пик взаимодействия.")
    else:
        out.append("Есть выраженный динамический пик: в этот момент контур получает сильное возбуждение.")
    rec = summary["half_recovery_days_after_peak"]
    if rec is None:
        out.append("До конца окна ток не успевает снизиться до половины пикового значения.")
    elif rec < 1:
        out.append("После пика система быстро демпфируется — менее чем за сутки до половины амплитуды.")
    else:
        out.append(f"После пика системе требуется около {rec:.1f} суток, чтобы снизить ток до половины амплитуды.")
    if summary["peak_memory"] > 0.75:
        out.append("Память в ходе сценария входит в высокий режим: предыстория начинает заметно влиять на последующие реакции.")
    elif summary["peak_memory"] > 0.45:
        out.append("Память накапливается, но не достигает крайнего режима.")
    else:
        out.append("Накопление памяти остаётся умеренным на всём интервале.")
    if summary["minimum_reserve"] < 0:
        out.append("Финансовый резерв пересекает ноль внутри моделируемого окна.")
    return out


def simulate_timeline(base_scenario, timeline):
    if not isinstance(base_scenario, dict):
        raise core.ScenarioError("base scenario must be object")
    cfg = timeline.get("моделирование", timeline.get("simulation", {}))
    if not isinstance(cfg, dict):
        raise core.ScenarioError("timeline моделирование must be object")
    days = core.positive(cfg.get("дней", cfg.get("days", 30)), "timeline days")
    dt = core.positive(cfg.get("шаг_дней", cfg.get("dt_days", 0.05)), "dt_days")
    sample_every = core.positive(cfg.get("выборка_дней", cfg.get("sample_every_days", 0.5)), "sample_every_days")
    if dt > 0.25:
        raise core.ScenarioError("dt_days must be <= 0.25 for SIM-TIME1")
    max_steps = 200000
    steps = int(math.ceil(days / dt))
    if steps > max_steps:
        raise core.ScenarioError("timeline too large")

    events = _compile_events(timeline)
    impulse_map = _event_impulses(events)

    initial = copy.deepcopy(base_scenario)
    initial_memory = core.clamp01(_get(initial, "отношения.накопленная_память", 0.2), "initial memory")
    initial_s = scenario_at(initial, events, 0.0, initial_memory)
    k0 = _coefficients(initial_s)
    q0 = k0["C"] * k0["drive"]
    reserve0 = k0["ir"]["finance"]["reserve"]
    debt0 = k0["ir"]["finance"]["debt"]
    state = (q0, 0.0, initial_memory, reserve0, debt0)

    if 0.0 in impulse_map:
        state = _apply_impulses(state, impulse_map[0.0])

    samples = [_sample(0.0, state, initial, events)]
    event_log = []
    for e in events:
        event_log.append({
            "id": e["id"], "label": e["label"], "day": e["start"],
            "duration_days": e["duration"], "money_impulse": e["money_impulse"],
            "memory_impulse": e["memory_impulse"], "set": e["set"], "add": e["add"],
        })

    next_sample = sample_every
    applied_impulse_times = {0.0} if 0.0 in impulse_map else set()
    t = 0.0
    for _ in range(steps):
        step = min(dt, days - t)
        if step <= 0:
            break
        t_next = t + step
        state = _rk4_step(t, state, step, initial, events, cfg)
        for impulse_time in sorted(impulse_map):
            if impulse_time in applied_impulse_times:
                continue
            if t < impulse_time <= t_next + 1e-12:
                state = _apply_impulses(state, impulse_map[impulse_time])
                applied_impulse_times.add(impulse_time)
        t = t_next
        if t + 1e-12 >= next_sample or t + 1e-12 >= days:
            samples.append(_sample(t, state, initial, events))
            while next_sample <= t + 1e-12:
                next_sample += sample_every

    summary = summarize(samples, events)
    return {
        "model_version": VERSION,
        "scenario_name": str(base_scenario.get("название", "Безымянная семейная система")),
        "equations": [
            "dq/dt = i",
            "L*di/dt = V(t) - R(t)*i - q/C(t)",
            "dm/dt = a*|V| + b*|i| - lambda*m - k_rad*P_rad",
            "dReserve/dt = (income(t) - load(t))/days_per_month + impulses",
            "dDebt/dt = annual_rate/365*Debt - mortgage/days_per_month",
        ],
        "integration": {
            "method": "RK4",
            "days": days,
            "dt_days": dt,
            "sample_every_days": sample_every,
            "steps": steps,
        },
        "events": event_log,
        "samples": samples,
        "summary": summary,
        "family_interpretation": interpret(summary),
    }


def report(result):
    s = result["summary"]
    lines = "\n".join(f"- {x}" for x in result["family_interpretation"])
    return f"""# SIM-TIME1 — динамический отчёт

**Сценарий:** {result['scenario_name']}  
**Модель:** {result['model_version']}  
**Интегратор:** {result['integration']['method']}  
**Окно:** {result['integration']['days']:.2f} дней

## Итог

{lines}

## Численные показатели

| Показатель | Значение |
|---|---:|
| Пиковый ток взаимодействия | {s['peak_interaction_current']:.5f} |
| День пика | {s['peak_interaction_day']:.3f} |
| Полувосстановление после пика, дней | {s['half_recovery_days_after_peak'] if s['half_recovery_days_after_peak'] is not None else 'не достигнуто'} |
| Максимальная память | {s['peak_memory']:.5f} |
| День максимальной памяти | {s['peak_memory_day']:.3f} |
| Минимальный резерв | {s['minimum_reserve']:.2f} |
| Финальный резерв | {s['final_reserve']:.2f} |
| Финальный ипотечный долг | {s['final_mortgage_debt']:.2f} |

> Это численный результат условной RLC-family модели, а не психологический или финансовый прогноз.
"""


def write_outputs(out, result):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "timeline_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "timeline_report.md").write_text(report(result), encoding="utf-8")
    keys = ["day","interaction_current","memory","reserve","mortgage_debt","drive","phase_deg","radiated_power"]
    rows = [",".join(keys)]
    for row in result["samples"]:
        rows.append(",".join(str(row[k]) for k in keys))
    (out / "timeline.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="SIM-TIME1 event-driven RLC-family solver")
    p.add_argument("scenario", help="FamilyScenario JSON")
    p.add_argument("timeline", help="TimelineSpec JSON, or '-' for stdin")
    p.add_argument("--out", type=Path, default=Path("out/time-run"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    scenario = core.load(args.scenario)
    timeline = _load_json(args.timeline)
    result = simulate_timeline(scenario, timeline)
    write_outputs(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else report(result))


if __name__ == "__main__":
    main()
