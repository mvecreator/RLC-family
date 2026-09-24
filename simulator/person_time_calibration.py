#!/usr/bin/env python3
"""PERSON-TIME-CAL: directional calibration for targeted dynamic PERSON2 networks."""

from __future__ import annotations

import copy
import json

from simulator import person_time_solver as pts


def base_two_node(quality=0.70, reserve=12000, income=5000, load=(1200, 1800, 400)):
    mortgage, base, other = load
    return {
        "название": "PERSON-TIME-CAL two-node",
        "person_model": {"gender_prior_strength": 0},
        "персонажи": [
            {"id": "a", "type": "adult", "gender": "male", "source_weight": 1},
            {"id": "b", "type": "adult", "gender": "female", "source_weight": 1},
        ],
        "связи_персонажей": [{"from": "a", "to": "b", "quality": quality}],
        "отношения": {
            "напряженность": 0.30,
            "частота_событий": 1.0,
            "накопленная_память": 0.20,
        },
        "связь": {
            "качество_проводника": 0.70,
            "усиление_эмоций": 1.0,
            "фильтр_критического_мышления": 0.70,
            "усиление_антенны": 0.30,
            "внешний_фон": 0.10,
            "сброс_через_антенну": 0.30,
            "согласование_собеседника": 0.70,
        },
        "финансы": {
            "доходы_в_месяц": [income],
            "ипотека_в_месяц": mortgage,
            "базовые_расходы_в_месяц": base,
            "прочие_расходы_в_месяц": other,
            "резерв": reserve,
            "долг_по_ипотеке": 0,
            "ставка_годовая": 0,
        },
    }


def timeline(events=None, days=2):
    return {
        "моделирование": {
            "дней": days,
            "шаг_дней": 0.005,
            "выборка_дней": 0.02,
        },
        "события": events or [],
    }


def run(scenario, tl):
    return pts.simulate_person_timeline(scenario, tl)


def suite():
    rows = []

    # PTCAL01: no event means no spontaneous voltage transient.
    calm = run(base_two_node(), timeline([], 1))
    rows.append({"id": "PTCAL01_EQUILIBRIUM", "result": calm})

    # PTCAL02: targeted event stays largest at source node.
    hit = [{
        "id": "hit-a",
        "день": 0.5,
        "длительность_дней": 0.25,
        "персонаж": "a",
        "добавить_возбуждение": 0.60,
    }]
    local = run(base_two_node(), timeline(hit, 2))
    rows.append({"id": "PTCAL02_LOCALITY", "result": local})

    # PTCAL03: better link transmits more to receiver.
    weak = run(base_two_node(0.20), timeline(hit, 2))
    strong = run(base_two_node(0.90), timeline(hit, 2))
    rows.append({"id": "PTCAL03_LINK_TRANSMISSION", "weak": weak, "strong": strong})

    # PTCAL04: targeted memory impulse is local at t=0.
    mem = run(
        base_two_node(),
        timeline([{
            "id": "mem-a",
            "день": 0,
            "персонаж": "a",
            "импульс_памяти": 0.20,
        }], 0.5),
    )
    rows.append({"id": "PTCAL04_MEMORY_LOCALITY", "result": mem})

    # PTCAL05: temporary link degradation is local and reverts.
    link_event = run(
        base_two_node(0.80),
        timeline([{
            "id": "link-drop",
            "день": 0.4,
            "длительность_дней": 0.5,
            "связь": ["a", "b"],
            "качество_связи": 0.10,
        }], 1.5),
    )
    rows.append({"id": "PTCAL05_LINK_TEMPORARY", "result": link_event})

    # PTCAL06: money impulse changes reserve exactly when finance stress is zero.
    comfy = base_two_node(reserve=20000, income=7000)
    no_bonus = run(comfy, timeline([], 1.5))
    bonus = run(
        comfy,
        timeline([{"id": "bonus", "день": 0.5, "денежный_импульс": 1000}], 1.5),
    )
    rows.append({"id": "PTCAL06_BONUS", "a": no_bonus, "b": bonus})

    # PTCAL07: financial stress acts as a global background, not a targeted event.
    healthy = base_two_node(reserve=15000, income=6000)
    stressed = base_two_node(
        reserve=800,
        income=2600,
        load=(1500, 1800, 500),
    )
    fin_a = run(healthy, timeline([], 20))
    fin_b = run(stressed, timeline([], 20))
    rows.append({"id": "PTCAL07_FINANCE_GLOBAL", "a": fin_a, "b": fin_b})

    # PTCAL08: deterministic replay.
    det_a = run(base_two_node(0.75), timeline(hit, 2))
    det_b = run(base_two_node(0.75), timeline(hit, 2))
    rows.append({"id": "PTCAL08_DETERMINISTIC", "a": det_a, "b": det_b})

    return rows


def _closest_sample(result, day):
    return min(result["samples"], key=lambda x: abs(x["day"] - day))


def _node(sample, pid):
    return next(x for x in sample["nodes"] if x["id"] == pid)


def _link(sample, a, b):
    return next(
        x for x in sample["links"]
        if {x["from"], x["to"]} == {a, b}
    )


def checks(rows):
    by = {x["id"]: x for x in rows}

    calm = by["PTCAL01_EQUILIBRIUM"]["result"]
    max_spontaneous = max(
        abs(node["voltage"])
        for sample in calm["samples"]
        for node in sample["nodes"]
    )

    local = by["PTCAL02_LOCALITY"]["result"]["summary"]["persons"]
    local_a = local["a"]["peak_voltage_abs"]
    local_b = local["b"]["peak_voltage_abs"]

    transmission = by["PTCAL03_LINK_TRANSMISSION"]
    weak_b = transmission["weak"]["summary"]["persons"]["b"]["peak_voltage_abs"]
    strong_b = transmission["strong"]["summary"]["persons"]["b"]["peak_voltage_abs"]

    mem_initial = by["PTCAL04_MEMORY_LOCALITY"]["result"]["samples"][0]
    mem_a = _node(mem_initial, "a")["memory"]
    mem_b = _node(mem_initial, "b")["memory"]

    link_result = by["PTCAL05_LINK_TEMPORARY"]["result"]
    during = _closest_sample(link_result, 0.60)
    after = _closest_sample(link_result, 1.20)
    q_during = _link(during, "a", "b")["quality"]
    q_after = _link(after, "a", "b")["quality"]

    bonus_case = by["PTCAL06_BONUS"]
    reserve_delta = (
        bonus_case["b"]["summary"]["final_reserve"]
        - bonus_case["a"]["summary"]["final_reserve"]
    )
    memory_delta = max(
        abs(
            bonus_case["b"]["summary"]["persons"][pid]["final_memory"]
            - bonus_case["a"]["summary"]["persons"][pid]["final_memory"]
        )
        for pid in ("a", "b")
    )

    finance = by["PTCAL07_FINANCE_GLOBAL"]
    stress_a = finance["a"]["summary"]["peak_financial_stress"]
    stress_b = finance["b"]["summary"]["peak_financial_stress"]
    avg_mem_a = sum(
        x["final_memory"] for x in finance["a"]["summary"]["persons"].values()
    ) / 2
    avg_mem_b = sum(
        x["final_memory"] for x in finance["b"]["summary"]["persons"].values()
    ) / 2

    deterministic = by["PTCAL08_DETERMINISTIC"]

    return {
        "PTCAL01": max_spontaneous < 1e-10,
        "PTCAL02": local_a > 2.0 * local_b,
        "PTCAL03": strong_b > 1.5 * weak_b,
        "PTCAL04": abs(mem_a - 0.40) < 1e-12 and abs(mem_b - 0.20) < 1e-12,
        "PTCAL05": abs(q_during - 0.10) < 1e-12 and abs(q_after - 0.80) < 1e-12,
        "PTCAL06": abs(reserve_delta - 1000.0) < 1e-6 and memory_delta < 1e-9,
        "PTCAL07": stress_b > stress_a and avg_mem_b > avg_mem_a,
        "PTCAL08": deterministic["a"] == deterministic["b"],
    }


def main():
    rows = suite()
    result = {"cases": rows, "checks": checks(rows)}
    result["passed"] = sum(result["checks"].values())
    result["total"] = len(result["checks"])
    result["all_pass"] = result["passed"] == result["total"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
